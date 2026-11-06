"""Tools del agente TechStore Returns (versión modular)."""
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "techstore.db"
HOY = datetime.date(2026, 11, 6)


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
    cur.execute("SELECT decision, fecha FROM historical_cliente WHERE cliente_id=?",
                (pedido["cliente_id"],))
    pedido["historical"] = [{"decision": d, "fecha": f} for d, f in cur.fetchall()]
    conn.close()
    return pedido


def validar_politica(pedido_id):
    p = consultar_pedido(pedido_id)
    if "error" in p:
        return p
    dias = (HOY - datetime.date.fromisoformat(p["fecha"])).days
    return {"elegible": dias <= 30, "dias": dias,
            "razon": "dentro de plazo" if dias <= 30 else "fuera de plazo (30 días)"}


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
    """Stub: en producción consulta Chroma. Aquí devuelve 2 casos del historial."""
    conn = _conn(); cur = conn.cursor()
    cur.execute("SELECT pedido_id, decision FROM historical_cliente LIMIT 2")
    out = [{"pedido_id": p, "decision": d} for p, d in cur.fetchall()]
    conn.close()
    return out


def guardar_decision(pedido_id, cliente_id, decision, monto):
    conn = _conn(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
        "VALUES (?,?,?,?,?)",
        (cliente_id, pedido_id, decision, HOY.isoformat(), monto))
    conn.commit(); conn.close()
    return {"ok": True}