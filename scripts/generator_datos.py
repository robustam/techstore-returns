"""
Generador de datos sintéticos para TechStore Returns.
Crea techstore.db con 40 pedidos y 15 clientes usando semilla fija.
IDEMPOTENTE: ejecutarlo N veces deja la BD en el mismo estado.

Uso:  python -m scripts.generator_datos
"""
import sqlite3
import random
import datetime
from pathlib import Path

# ---- Semilla fija para reproducibilidad ----
SEED = 42
random.seed(SEED)

DB_PATH = Path(__file__).resolve().parent.parent / "techstore.db"
HOY = datetime.date(2026, 11, 6)


def crear_tablas(cur):
    cur.executescript("""
    DROP TABLE IF EXISTS pedidos;
    DROP TABLE IF EXISTS clientes;
    DROP TABLE IF EXISTS historical_cliente;
    DROP TABLE IF EXISTS politicas;

    CREATE TABLE clientes (
        id          TEXT PRIMARY KEY,
        nombre      TEXT NOT NULL,
        recurrente  INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE pedidos (
        id           TEXT PRIMARY KEY,
        cliente_id   TEXT NOT NULL,
        monto        REAL NOT NULL,
        fecha        TEXT NOT NULL,
        comprobante  INTEGER NOT NULL,
        descripcion  TEXT,
        FOREIGN KEY (cliente_id) REFERENCES clientes(id)
    );

    CREATE TABLE historical_cliente (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id  TEXT NOT NULL,
        pedido_id   TEXT NOT NULL,
        decision    TEXT NOT NULL,
        fecha       TEXT NOT NULL,
        monto       REAL NOT NULL
    );

    CREATE TABLE politicas (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        seccion   TEXT NOT NULL,
        contenido TEXT NOT NULL
    );
    """)


def generar_clientes(cur):
    nombres = [
        "Ana Pérez", "Bruno Díaz", "Carla Soto", "Diego Rojas", "Elena Muñoz",
        "Felipe Vera", "Gabriela Lagos", "Hugo Castro", "Isabel Fuentes",
        "Javier Pinto", "Karen Silva", "Luis Herrera", "María Torres",
        "Nicolás Reyes", "Olga Vargas",
    ]
    for i, nombre in enumerate(nombres, start=1):
        recurrente = 1 if i % 3 == 0 else 0
        cur.execute(
            "INSERT INTO clientes VALUES (?,?,?)",
            (f"C-{i:03d}", nombre, recurrente),
        )


def generar_pedidos(cur):
    """40 pedidos base. Los 6 de escenario se sobreescriben después."""
    montos = [25000, 30000, 48000, 60000, 90000, 120000, 150000, 250000]
    descripciones = [
        "Producto defectuoso", "No me gustó", "Talla incorrecta",
        "Llegó dañado en transporte", "No funciona", "",
    ]
    dias_opciones = [3, 7, 12, 20, 28, 35, 45, 60]

    for i in range(1, 41):
        cliente_id = f"C-{random.randint(1, 15):03d}"
        monto = random.choice(montos)
        dias_atras = random.choice(dias_opciones)
        fecha = (HOY - datetime.timedelta(days=dias_atras)).isoformat()
        comprobante = random.choice([1, 1, 1, 0])
        descripcion = random.choice(descripciones)
        cur.execute(
            "INSERT INTO pedidos VALUES (?,?,?,?,?,?)",
            (f"PED-{i:03d}", cliente_id, monto, fecha, comprobante, descripcion),
        )


def generar_politicas(cur):
    politicas = [
        ("plazo", "El cliente puede solicitar devolución dentro de los 30 días "
                  "corridos desde la fecha de compra."),
        ("comprobante", "Toda devolución requiere boleta o comprobante de pago "
                        "y una descripción del motivo."),
        ("reembolso", "El reembolso se realiza por el monto total del pedido en "
                      "la misma moneda de la compra."),
        ("alto_valor", "Las devoluciones superiores a $100.000 requieren "
                       "aprobación de un supervisor."),
        ("fraude", "Si un cliente registra 3 o más devoluciones en 90 días, el "
                   "caso se escala a revisión antifraude."),
        ("recurrente", "Los clientes recurrentes con devoluciones menores a "
                       "$50.000 acceden a aprobación preferente."),
        ("etiqueta", "La etiqueta de devolución se genera automáticamente y se "
                     "envía al correo del cliente."),
        ("escalamiento", "Los casos fuera de política se derivan a un agente "
                         "humano con justificación registrada en el CRM."),
    ]
    cur.executemany(
        "INSERT INTO politicas(seccion, contenido) VALUES (?,?)", politicas
    )


def forzar_escenarios(cur):
    """Fuerza los 6 escenarios. LIMPIA el historial de los clientes de
    escenario antes de insertar, para garantizar idempotencia."""
    # 1. Limpiar historial de los 6 clientes de escenario
    cur.execute(
        "DELETE FROM historical_cliente WHERE cliente_id IN "
        "('C-001','C-002','C-003','C-004','C-005','C-006')"
    )

    # 2. Forzar flags de recurrente
    cur.execute("UPDATE clientes SET recurrente=1 WHERE id='C-004'")
    cur.execute(
        "UPDATE clientes SET recurrente=0 "
        "WHERE id IN ('C-001','C-002','C-003','C-005','C-006')"
    )

    # 3. Historial: C-004 = 1 devolución (recurrente, sin fraude)
    cur.execute(
        "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
        "VALUES (?,?,?,?,?)",
        ("C-004", "PED-004", "aprobar_estandar", "2026-09-01", 25000),
    )

    # 4. Historial: C-005 = 4 devoluciones (fraude)
        # 4. Historial: C-005 = 4 devoluciones en los últimos 90 días (fraude)
    for i, fecha in enumerate(
        ["2026-08-15", "2026-09-01", "2026-10-01", "2026-10-20"], start=1
    ):
        cur.execute(
            "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
            "VALUES (?,?,?,?,?)",
            ("C-005", f"PED-00{i}", "aprobar_estandar", fecha, 25000),
        )

    # 5. Forzar los 6 pedidos de escenario
    escenarios = [
        ("PED-001", "C-001", 25000,  "2026-10-20", 1, "Producto defectuoso"),
        ("PED-015", "C-002", 25000,  "2026-09-20", 1, "No funciona"),
        ("PED-022", "C-003", 250000, "2026-10-25", 1, "Producto caro"),
        ("PED-024", "C-004", 30000,  "2026-10-28", 1, "Cambio de opinión"),
        ("PED-005", "C-005", 20000,  "2026-10-29", 1, "No sirve"),
        ("PED-030", "C-006", 30000,  "2026-10-30", 0, ""),
    ]
    for pedido_id, cliente_id, monto, fecha, comprobante, descripcion in escenarios:
        cur.execute(
            "UPDATE pedidos SET cliente_id=?, monto=?, fecha=?, comprobante=?, descripcion=? "
            "WHERE id=?",
            (cliente_id, monto, fecha, comprobante, descripcion, pedido_id),
        )


def main():
    print(f"Generando datos en: {DB_PATH}")
    if DB_PATH.exists():
        DB_PATH.unlink()  # Borra el archivo completo

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    crear_tablas(cur)
    generar_clientes(cur)
    generar_pedidos(cur)
    generar_politicas(cur)
    forzar_escenarios(cur)
    conn.commit()

    # Resumen
    n_clientes = cur.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    n_pedidos = cur.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    n_hist = cur.execute("SELECT COUNT(*) FROM historical_cliente").fetchone()[0]
    n_pol = cur.execute("SELECT COUNT(*) FROM politicas").fetchone()[0]
    conn.close()

    print(f"  OK {n_clientes} clientes")
    print(f"  OK {n_pedidos} pedidos")
    print(f"  OK {n_hist} registros de historial (debe ser 5)")
    print(f"  OK {n_pol} políticas")
    print("Listo.")


if __name__ == "__main__":
    main()