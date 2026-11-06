"""
TechStore Returns — Interfaz Streamlit.
Uso:  streamlit run app.py
"""
import streamlit as st
import sqlite3
import datetime
from pathlib import Path

# ============================================================
# Configuración de la página
# ============================================================
st.set_page_config(
    page_title="TechStore Returns",
    page_icon="📦",
    layout="wide",
)

DB_PATH = Path(__file__).resolve().parent / "techstore.db"
HOY = datetime.date(2026, 11, 6)

# ============================================================
# Conexión a SQLite
# ============================================================
@st.cache_resource
def get_conn():
    if not DB_PATH.exists():
        st.error(f"No se encontró {DB_PATH}. Ejecuta primero: "
                 "`python -m scripts.generator_datos`")
        st.stop()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


# ============================================================
# Las 7 tools (idénticas a src/tools.py)
# ============================================================
def consultar_pedido(pedido_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pedidos WHERE id=?", (pedido_id,))
    row = cur.fetchone()
    if not row:
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
    return {
        "codigo": f"RET-{pedido_id}",
        "url": f"https://mock.techstore/etiqueta/{pedido_id}",
    }


def actualizar_crm(pedido_id, estado):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE pedidos SET descripcion=? WHERE id=?",
                (f"[CRM:{estado}]", pedido_id))
    conn.commit()
    return {"ok": True, "estado": estado}


def notificar_cliente(cliente_id, mensaje):
    return {"ok": True, "cliente": cliente_id, "mensaje": mensaje}


def buscar_casos_similares(texto):
    """Stub: en producción consulta Chroma. Aquí devuelve 2 casos del historial."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pedido_id, decision FROM historical_cliente LIMIT 2")
    return [{"pedido_id": p, "decision": d} for p, d in cur.fetchall()]


def guardar_decision(pedido_id, cliente_id, decision, monto):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
        "VALUES (?,?,?,?,?)",
        (cliente_id, pedido_id, decision, HOY.isoformat(), monto),
    )
    conn.commit()
    return {"ok": True}


# ============================================================
# Planner — 6 reglas priorizadas
# ============================================================
def decidir_accion(p):
    # Regla 1: fuera de plazo
    v = validar_politica(p["id"])
    if not v["elegible"]:
        return "escalar"
    # Regla 2: monto alto
    if p["monto"] > 100000:
        return "solicitar_aprobacion"
    # Regla 3: posible fraude
    devol_90d = sum(
        1 for h in p["historical"]
        if (HOY - datetime.date.fromisoformat(h["fecha"])).days <= 90
    )
    if devol_90d >= 3:
        return "escalar_fraude"
    # Regla 4: cliente recurrente
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT recurrente FROM clientes WHERE id=?", (p["cliente_id"],))
    row = cur.fetchone()
    if row and row[0] and p["monto"] < 50000:
        return "aprobar_preferente"
    # Regla 5: falta info
    if not p["comprobante"] or not (p["descripcion"] or "").strip():
        return "solicitar_info"
    # Regla 6: estándar
    return "aprobar_estandar"


# ============================================================
# Orquestador — devuelve traza paso a paso
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
        r = calcular_reembolso(pedido_id)
        traza.append(("calcular_reembolso", r))
        e = generar_etiqueta(pedido_id)
        traza.append(("generar_etiqueta", e))
        actualizar_crm(pedido_id, decision)
        traza.append(("actualizar_crm", {"ok": True}))
        notificar_cliente(p["cliente_id"], f"Devolución aprobada ({decision})")
        traza.append(("notificar_cliente", {"ok": True}))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    elif decision in ("escalar", "escalar_fraude", "solicitar_aprobacion"):
        actualizar_crm(pedido_id, decision)
        traza.append(("actualizar_crm", {"ok": True}))
        notificar_cliente(
            p["cliente_id"],
            f"Tu caso fue derivado ({decision}). Un agente lo revisará.",
        )
        traza.append(("notificar_cliente", {"ok": True}))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    elif decision == "solicitar_info":
        notificar_cliente(
            p["cliente_id"],
            "Falta comprobante o descripción. Por favor completa los datos.",
        )
        traza.append(("notificar_cliente", {"ok": True}))
        guardar_decision(pedido_id, p["cliente_id"], decision, p["monto"])

    return {"pedido": pedido_id, "decision": decision, "traza": traza}


# ============================================================
# UI
# ============================================================
BADGES = {
    "aprobar_estandar":   ("🟢", "Aprobado (estándar)"),
    "aprobar_preferente": ("🟢", "Aprobado (preferente)"),
    "escalar":            ("🔴", "Escalado (fuera de plazo)"),
    "escalar_fraude":     ("🔴", "Escalado (posible fraude)"),
    "solicitar_aprobacion": ("🟠", "Requiere aprobación (monto alto)"),
    "solicitar_info":     ("🟡", "Falta información"),
    "error":              ("⚫", "Error"),
}

st.title("📦 TechStore Returns")
st.caption(
    "Agente de devoluciones · ISY0101 Ingeniería de Soluciones con IA · "
    "Evaluación Parcial N°2"
)

tab1, tab2, tab3 = st.tabs(
    ["🔄 Flujo principal", "💬 Preguntas abiertas", "📊 Estado del sistema"]
)

# ---------- TAB 1: Flujo principal ----------
with tab1:
    st.subheader("Procesar una devolución")

    col1, col2 = st.columns([2, 1])
    with col1:
        pedido_id = st.text_input(
            "ID de pedido", value="PED-001",
            help="Ejemplos: PED-001, PED-015, PED-022, PED-024, PED-005",
        )
    with col2:
        st.write("")
        st.write("")
        ejecutar = st.button("▶️ Ejecutar agente", type="primary",
                             use_container_width=True)

    st.markdown("**Escenarios de prueba rápida:**")
    cols = st.columns(6)
    ejemplos = [
        ("PED-001", "Estándar"),
        ("PED-015", "Fuera de plazo"),
        ("PED-022", "Alto valor"),
        ("PED-024", "Recurrente"),
        ("PED-005", "Fraude"),
        ("PED-030", "Falta info"),
    ]
    for c, (pid, label) in zip(cols, ejemplos):
        if c.button(f"{pid}\n{label}", use_container_width=True):
            pedido_id = pid
            ejecutar = True

    if ejecutar:
        with st.spinner("Ejecutando agente..."):
            resultado = procesar_solicitud(pedido_id)

        icono, texto = BADGES.get(resultado["decision"], ("⚪", resultado["decision"]))
        st.markdown(f"### {icono} Decisión: **{texto}**")
        st.code(f"decision = {resultado['decision']}", language="python")

        st.subheader("🧭 Traza de ejecución")
        for i, (tool, salida) in enumerate(resultado["traza"], start=1):
            with st.expander(f"Paso {i} · `{tool}`", expanded=(i <= 3)):
                st.json(salida)

        st.success("Traza completa. La decisión quedó registrada en memoria de largo plazo.")

# ---------- TAB 2: Preguntas abiertas ----------
with tab2:
    st.subheader("Preguntas abiertas al agente (LLM)")
    st.caption(
        "Esta rama usa AgentExecutor + Gemini Flash. Si no configuraste "
        "`GEMINI_API_KEY`, verás un aviso."
    )

    pregunta = st.text_area(
        "Escribe tu pregunta",
        value="¿Puedo devolver un pedido comprado hace 20 días?",
    )

    if st.button("💬 Preguntar al agente"):
        try:
            from src.agente import crear_agente  # import perezoso
            agente = crear_agente()
            with st.spinner("Razonando..."):
                respuesta = agente.invoke({"input": pregunta})
            st.markdown("**Respuesta:**")
            st.write(respuesta.get("output", respuesta))
        except ImportError:
            st.warning(
                "⚠️ Módulo `src/agente.py` no disponible. "
                "Configura `GEMINI_API_KEY` y `langchain-google-genai`."
            )
        except Exception as e:
            st.error(f"Error al invocar el agente: {e}")

# ---------- TAB 3: Estado del sistema ----------
with tab3:
    st.subheader("Estado del sistema")

    conn = get_conn()
    cur = conn.cursor()

    n_clientes = cur.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    n_pedidos = cur.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    n_hist = cur.execute("SELECT COUNT(*) FROM historical_cliente").fetchone()[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("Clientes", n_clientes)
    c2.metric("Pedidos", n_pedidos)
    c3.metric("Decisiones guardadas", n_hist)

    st.markdown("#### Últimos 10 pedidos")
    cur.execute("SELECT id, cliente_id, monto, fecha FROM pedidos LIMIT 10")
    filas = cur.fetchall()
    st.dataframe(
        [{"Pedido": p, "Cliente": c, "Monto": m, "Fecha": f} for p, c, m, f in filas],
        use_container_width=True,
    )

    st.markdown("#### Distribución de decisiones")
    cur.execute("SELECT decision, COUNT(*) FROM historical_cliente GROUP BY decision")
    dist = cur.fetchall()
    if dist:
        st.bar_chart({d: n for d, n in dist})
    else:
        st.info("Aún no hay decisiones guardadas. Ejecuta un caso en la pestaña 1.")