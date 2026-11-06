"""Pruebas de las 7 tools."""
from scripts import generator_evidencias as ev


def test_consultar_pedido_existente():
    p = ev.consultar_pedido("PED-001")
    assert "error" not in p
    assert p["id"] == "PED-001"
    assert "historical" in p


def test_consultar_pedido_inexistente():
    p = ev.consultar_pedido("PED-999")
    assert "error" in p


def test_validar_politica_dentro_plazo():
    v = ev.validar_politica("PED-001")
    assert v["elegible"] is True
    assert v["dias"] <= 30


def test_validar_politica_fuera_plazo():
    v = ev.validar_politica("PED-015")
    assert v["elegible"] is False
    assert v["dias"] > 30


def test_calcular_reembolso():
    r = ev.calcular_reembolso("PED-001")
    assert r["monto"] == 25000
    assert r["moneda"] == "CLP"


def test_generar_etiqueta_formato():
    e = ev.generar_etiqueta("PED-001")
    assert e["codigo"] == "RET-PED-001"
    assert e["url"].startswith("https://")


def test_buscar_casos_similares_devuelve_lista():
    casos = ev.buscar_casos_similares("no me gustó")
    assert isinstance(casos, list)
    assert len(casos) >= 1