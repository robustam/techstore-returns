"""Pruebas del flujo completo (orquestador + planner + tools)."""
from scripts import generator_evidencias as ev


def test_flujo_estandar_completo():
    r = ev.procesar_solicitud("PED-001")
    assert r["decision"] == "aprobar_estandar"
    tools = [t for t, _ in r["traza"]]
    assert "calcular_reembolso" in tools
    assert "generar_etiqueta" in tools
    assert "notificar_cliente" in tools


def test_flujo_fuera_plazo_no_reembolsa():
    r = ev.procesar_solicitud("PED-015")
    assert r["decision"] == "escalar"
    tools = [t for t, _ in r["traza"]]
    assert "calcular_reembolso" not in tools
    assert "generar_etiqueta" not in tools


def test_flujo_pedido_inexistente():
    r = ev.procesar_solicitud("PED-999")
    assert r["decision"] == "error"