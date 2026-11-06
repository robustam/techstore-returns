"""
Generador de evidencias para TechStore Returns.
Ejecuta los escenarios del informe y guarda:
  - evidence/resultados.json
  - evidence/reporte_evidencias.md
  - evidence/resumen_consola.txt

Uso:  python -m scripts.generator_evidencias
"""
import json
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "techstore.db"
EVIDENCE_DIR = Path(__file__).resolve().parent.parent / "evidence"
EVIDENCE_DIR.mkdir(exist_ok=True)
HOY = datetime.date(2026, 11, 6)

# Escenarios oficiales del informe (sección 6)
ESCENARIOS = [
    {
        "nombre": "Estándar",
        "pedido": "PED-001",
        "esperado": "aprobar_estandar",
        "descripcion": "Dentro de plazo, monto bajo, con comprobante.",
    },
    {
        "nombre": "Fuera de plazo (45 días)",
        "pedido": "PED-015",
        "esperado": "escalar",
        "descripcion": "Pedido con 47 días de antigüedad.",
    },
    {
        "nombre": "Alto valor ($250.000)",
        "pedido": "PED-022",
        "esperado": "solicitar_aprobacion",
        "descripcion": "Monto superior a $100.000.",
    },
    {
        "nombre": "Cliente recurrente (memoria)",
        "pedido": "PED-024",
        "esperado": "aprobar_preferente",
        "descripcion": "C-004 tiene historial previo y monto < $50.000.",
    },
    {
        "nombre": "Posible fraude",
        "pedido": "PED-005",
        "esperado": "escalar_fraude",
        "descripcion": "C-005 registra 4 devoluciones en 90 días.",
    },
    {
        "nombre": "Falta información",
        "pedido": "PED-030",
        "esperado": "solicitar_info",
        "descripcion": "Sin comprobante o sin descripción.",
    },
]


# ============================================================
# Tools (misma lógica que src/tools.py, autocontenidas aquí)
# ============================================================
def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def consultar_pedido(pedido_id):
    conn = _conn(); cur = conn.cursor()
    cur.execute("SELECT * FROM pedidos WHERE id=?", (pedido_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return {"error": f"Pedido {pedido_id} no existe"}
    cols = ["id", "cliente_id", "monto", "fecha", "comprobante", "descripcion"]
    pedido = dict(zip(cols, row))
    cur.execute(
        "SELECT decision, fecha FROM historical_cliente WHERE cliente_id=?",
        (pedido["cliente_id"],),
    )
    pedido["historical"] = [
        {"decision": d, "fecha": f} for d, f in cur.fetchall()
    ]
    conn.close()
    return pedido


def validar_politica(pedido_id):
    p = consultar_pedido(pedido_id)
    if "error" in p:
        return p
    dias = (HOY - datetime.date.fromisoformat(p["fecha"])).days
    return {
        "elegible": dias <= 30,
        "dias": dias,
        "razon": "dentro de plazo" if dias <= 30 else "fuera de plazo (30 días)",
    }


def calcular_reembolso(pedido_id, tipo="total"):
    p = consultar_pedido(pedido_id)
    if "error" in p:
        return p
    return {"monto": p["monto"], "moneda": "CLP", "tipo": tipo}


def generar_etiqueta(pedido_id):
    return {"codigo": f"RET-{pedido_id}",
            "url": f"https://mock.techstore/etiqueta/{pedido_id}"}


def actualizar_crm(pedido_id, estado):
    conn = _conn(); cur = conn.cursor()
    cur.execute("UPDATE pedidos SET descripcion=? WHERE id=?",
                (f"[CRM:{estado}]", pedido_id))
    conn.commit(); conn.close()
    return {"ok": True, "estado": estado}


def notificar_cliente(cliente_id, mensaje):
    return {"ok": True, "cliente": cliente_id, "mensaje": mensaje}


def buscar_casos_similares(texto):
    conn = _conn(); cur = conn.cursor()
    cur.execute("SELECT pedido_id, decision FROM historical_cliente LIMIT 2")
    out = [{"pedido_id": p, "decision": d} for p, d in cur.fetchall()]
    conn.close()
    return out


def guardar_decision(pedido_id, cliente_id, decision, monto):
    """Guarda la decisión SOLO si no existe ya para ese pedido.
    Así el generador de evidencias es idempotente."""
    conn = _conn(); cur = conn.cursor()
    cur.execute(
        "SELECT id FROM historical_cliente WHERE pedido_id=? AND cliente_id=?",
        (pedido_id, cliente_id),
    )
    if cur.fetchone() is not None:
        conn.close()
        return {"ok": True, "skipped": True}
    cur.execute(
        "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
        "VALUES (?,?,?,?,?)",
        (cliente_id, pedido_id, decision, HOY.isoformat(), monto),
    )
    conn.commit(); conn.close()
    return {"ok": True, "skipped": False}


# ============================================================
# Planner — 6 reglas
# ============================================================
def decidir_accion(p):
    v = validar_politica(p["id"])
    if not v["elegible"]:
        return "escalar"
    if p["monto"] > 100000:
        return "solicitar_aprobacion"
    devol_90d = sum(
        1 for h in p["historical"]
        if (HOY - datetime.date.fromisoformat(h["fecha"])).days <= 90
    )
    if devol_90d >= 3:
        return "escalar_fraude"
    conn = _conn(); cur = conn.cursor()
    cur.execute("SELECT recurrente FROM clientes WHERE id=?", (p["cliente_id"],))
    row = cur.fetchone(); conn.close()
    if row and row[0] and p["monto"] < 50000:
        return "aprobar_preferente"
    if not p["comprobante"] or not (p["descripcion"] or "").strip():
        return "solicitar_info"
    return "aprobar_estandar"


# ============================================================
# Orquestador con traza
# ============================================================
def procesar_solicitud(pedido_id):
    traza = []
    p = consultar_pedido(pedido_id)
    traza.append(("consultar_pedido", p))
    if "error" in p:
        return {"pedido": pedido_id, "decision": "error", "traza": traza}

    v = validar_politica(pedido_id)
    traza.append(("validar_politica", v))

    decision = decidir_accion(p)
    traza.append(("decidir_accion", {"decision": decision}))

    if decision in ("aprobar_estandar", "aprobar_preferente"):
        traza.append(("calcular_reembolso", calcular_reembolso(pedido_id)))
        traza.append(("generar_etiqueta", generar_etiqueta(pedido_id)))
        traza.append(("actualizar_crm", actualizar_crm(pedido_id, decision)))
        traza.append(("notificar_cliente", notificar_cliente(
            p["cliente_id"], f"Devolución aprobada ({decision})")))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    elif decision in ("escalar", "escalar_fraude", "solicitar_aprobacion"):
        traza.append(("actualizar_crm", actualizar_crm(pedido_id, decision)))
        traza.append(("notificar_cliente", notificar_cliente(
            p["cliente_id"], f"Tu caso fue derivado ({decision}).")))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    elif decision == "solicitar_info":
        traza.append(("notificar_cliente", notificar_cliente(
            p["cliente_id"], "Falta comprobante o descripción.")))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    return {"pedido": pedido_id, "decision": decision, "traza": traza}


# ============================================================
# Salidas
# ============================================================
def _json_default(o):
    if isinstance(o, datetime.date):
        return o.isoformat()
    return str(o)


def escribir_markdown(resultados):
    lines = []
    lines.append("# Evidencias — TechStore Returns")
    lines.append("")
    lines.append(f"Fecha de ejecución: {HOY.isoformat()}")
    lines.append(f"Semilla de datos: 42 · Pedidos: 40 · Clientes: 15")
    lines.append("")
    lines.append("## Resumen de escenarios")
    lines.append("")
    lines.append("| # | Escenario | Pedido | Esperado | Obtenido | OK | Tools |")
    lines.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(resultados, start=1):
        ok = "SI" if r["esperado"] == r["decision"] else "NO"
        n_tools = len(r["traza"])
        lines.append(
            f"| {i} | {r['nombre']} | `{r['pedido']}` | "
            f"`{r['esperado']}` | `{r['decision']}` | {ok} | {n_tools} |"
        )
    lines.append("")
    lines.append("## Detalle por escenario")
    lines.append("")

    for r in resultados:
        lines.append(f"### {r['nombre']} — `{r['pedido']}`")
        lines.append("")
        lines.append(f"**Descripción:** {r['descripcion']}")
        lines.append("")
        lines.append(f"**Decisión esperada:** `{r['esperado']}`  ")
        lines.append(f"**Decisión obtenida:** `{r['decision']}`")
        lines.append("")
        lines.append("**Traza de ejecución:**")
        lines.append("")
        lines.append("| Paso | Tool | Salida (resumen) |")
        lines.append("|---|---|---|")
        for j, (tool, salida) in enumerate(r["traza"], start=1):
            resumen = json.dumps(salida, ensure_ascii=False, default=_json_default)
            if len(resumen) > 120:
                resumen = resumen[:117] + "..."
            lines.append(f"| {j} | `{tool}` | `{resumen}` |")
        lines.append("")

    lines.append("## Cómo reproducir")
    lines.append("")
    lines.append("```bash")
    lines.append("python -m scripts.generator_datos")
    lines.append("python -m scripts.generator_evidencias")
    lines.append("pytest tests/ -v")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)


def escribir_consola(resultados):
    lines = []
    lines.append("=" * 66)
    lines.append(" TechStore Returns — Evidencias de ejecución")
    lines.append(f" Fecha: {HOY.isoformat()} · Semilla: 42")
    lines.append("=" * 66)
    exitos = 0
    for r in resultados:
        ok = "OK  " if r["esperado"] == r["decision"] else "FAIL"
        if ok == "OK  ":
            exitos += 1
        lines.append("")
        lines.append(f"[{ok}] {r['nombre']:<30} {r['pedido']:<8} -> {r['decision']}")
        for tool, _ in r["traza"]:
            lines.append(f"         - {tool}")
    lines.append("")
    lines.append("-" * 66)
    lines.append(f" Resultado: {exitos}/{len(resultados)} escenarios exitosos")
    lines.append("-" * 66)
    return "\n".join(lines)


# ============================================================
# Main
# ============================================================
def main():
    if not DB_PATH.exists():
        raise SystemExit(
            f"No existe {DB_PATH}. Ejecuta primero:\n"
            "  python -m scripts.generator_datos"
        )

    resultados = []
    for esc in ESCENARIOS:
        r = procesar_solicitud(esc["pedido"])
        r.update({
            "nombre": esc["nombre"],
            "esperado": esc["esperado"],
            "descripcion": esc["descripcion"],
        })
        resultados.append(r)

    # 1. JSON
    with open(EVIDENCE_DIR / "resultados.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2,
                  default=_json_default)

    # 2. Markdown
    md = escribir_markdown(resultados)
    with open(EVIDENCE_DIR / "reporte_evidencias.md", "w", encoding="utf-8") as f:
        f.write(md)

    # 3. Consola
    consola = escribir_consola(resultados)
    with open(EVIDENCE_DIR / "resumen_consola.txt", "w", encoding="utf-8") as f:
        f.write(consola)
    print(consola)

    # Aviso final
    exitos = sum(1 for r in resultados if r["esperado"] == r["decision"])
    print(f"\nArchivos generados en {EVIDENCE_DIR}/")
    print("  - resultados.json")
    print("  - reporte_evidencias.md")
    print("  - resumen_consola.txt")
    if exitos != len(resultados):
        raise SystemExit(f"ATENCION: {len(resultados) - exitos} escenario(s) no coinciden.")


if __name__ == "__main__":
    main()