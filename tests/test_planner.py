"""Pruebas de las 6 reglas del planner."""
import datetime

from scripts import generator_evidencias as ev


def _pedido_base(**overrides):
    """Pedido sintético dentro de plazo, monto bajo, con comprobante."""
    base = {
        "id": "PED-TEST",
        "cliente_id": "C-001",
        "monto": 25000,
        "fecha": (ev.HOY - datetime.timedelta(days=10)).isoformat(),
        "comprobante": 1,
        "descripcion": "Producto defectuoso",
        "historical": [],
    }
    base.update(overrides)
    return base


def test_estandar_aprueba():
    """Regla 6: caso estándar sin riesgo."""
    assert ev.decidir_accion(_pedido_base()) == "aprobar_estandar"


def test_fuera_de_plazo_escala():
    """Regla 1: pedido de 47 días -> escalar."""
    p = _pedido_base(
        fecha=(ev.HOY - datetime.timedelta(days=47)).isoformat()
    )
    assert ev.decidir_accion(p) == "escalar"


def test_alto_valor_requiere_aprobacion():
    """Regla 2: monto > $100.000 -> solicitar_aprobacion."""
    assert ev.decidir_accion(_pedido_base(monto=250000)) == "solicitar_aprobacion"


def test_fraude_escala_con_3_devoluciones():
    """Regla 3: >= 3 devoluciones en 90 días -> escalar_fraude."""
    hace_10 = (ev.HOY - datetime.timedelta(days=10)).isoformat()
    hace_20 = (ev.HOY - datetime.timedelta(days=20)).isoformat()
    hace_30 = (ev.HOY - datetime.timedelta(days=30)).isoformat()
    p = _pedido_base(
        historical=[
            {"decision": "aprobar_estandar", "fecha": hace_10},
            {"decision": "aprobar_estandar", "fecha": hace_20},
            {"decision": "aprobar_estandar", "fecha": hace_30},
        ]
    )
    assert ev.decidir_accion(p) == "escalar_fraude"


def test_cliente_recurrente_preferente():
    """Regla 4: cliente recurrente + monto < $50.000 -> aprobar_preferente."""
    p = _pedido_base(cliente_id="C-004", monto=30000)
    assert ev.decidir_accion(p) == "aprobar_preferente"


def test_falta_comprobante_pide_info():
    """Regla 5: sin comprobante -> solicitar_info."""
    assert ev.decidir_accion(_pedido_base(comprobante=0)) == "solicitar_info"