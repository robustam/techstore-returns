"""Fixtures compartidos para toda la suite de pruebas."""
import sys
import sqlite3
from pathlib import Path

import pytest

# Permite importar scripts.generator_evidencias desde los tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import generator_evidencias as ev  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def preparar_bd(tmp_path_factory):
    """Genera una BD limpia en techstore.db antes de correr los tests."""
    from scripts import generator_datos
    # Reapuntamos a una BD temporal
    tmp_db = tmp_path_factory.mktemp("db") / "techstore.db"
    generator_datos.DB_PATH = tmp_db
    ev.DB_PATH = tmp_db
    generator_datos.main()
    yield tmp_db


@pytest.fixture
def conn(preparar_bd):
    conn = sqlite3.connect(preparar_bd)
    yield conn
    conn.close()