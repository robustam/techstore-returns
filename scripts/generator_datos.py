"""
Generador de datos sintéticos para TechStore Returns.
Crea techstore.db con 40 pedidos y 15 clientes usando semilla fija.
Uso:  python -m scripts.generator_datos
"""
import sqlite3
import random
import datetime
from pathlib import Path

# ---- Semilla fija para reproducibilidad (requisito del informe) ----
SEED = 42
random.seed(SEED)

DB_PATH = Path(__file__).resolve().parent.parent / "techstore.db"
HOY = datetime.date(2026, 11, 6)  # fecha de la evaluación


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
        # 1 de cada 3 es recurrente
        recurrente = 1 if i % 3 == 0 else 0
        cur.execute(
            "INSERT INTO clientes VALUES (?,?,?)",
            (f"C-{i:03d}", nombre, recurrente),
        )


def generar_pedidos(cur):
    """40 pedidos con fechas que cubren todos los escenarios del planner."""
    montos = [25000, 30000, 48000, 60000, 90000, 120000, 150000, 250000]
    descripciones = [
        "Producto defectuoso",
        "No me gustó",
        "Talla incorrecta",
        "Llegó dañado en transporte",
        "No funciona",
        "",
    ]
    # Días de antigüedad: mezcla de dentro y fuera de plazo
    dias_opciones = [3, 7, 12, 20, 28, 35, 45, 60]

    for i in range(1, 41):
        cliente_id = f"C-{random.randint(1, 15):03d}"
        monto = random.choice(montos)
        dias_atras = random.choice(dias_opciones)
        fecha = (HOY - datetime.timedelta(days=dias_atras)).isoformat()
        comprobante = random.choice([1, 1, 1, 0])  # 75% con comprobante
        descripcion = random.choice(descripciones)
        cur.execute(
            "INSERT INTO pedidos VALUES (?,?,?,?,?,?)",
            (f"PED-{i:03d}", cliente_id, monto, fecha, comprobante, descripcion),
        )


def generar_historial(cur):
    """Historial precargado para los escenarios de memoria y fraude."""
    historial = [
        # C-004: cliente recurrente (memoria)
        ("C-004", "PED-004", "aprobar_estandar", "2026-09-01", 25000),
        # C-005: 4 devoluciones en 90 días → fraude
        ("C-005", "PED-005", "aprobar_estandar", "2026-06-01", 25000),
        ("C-005", "PED-010", "aprobar_estandar", "2026-07-01", 25000),
        ("C-005", "PED-011", "aprobar_estandar", "2026-08-01", 25000),
        ("C-005", "PED-012", "aprobar_estandar", "2026-09-01", 25000),
    ]
    cur.executemany(
        "INSERT INTO historical_cliente(cliente_id,pedido_id,decision,fecha,monto) "
        "VALUES (?,?,?,?,?)",
        historial,
    )


def forzar_escenarios(cur):
    """Ajusta pedidos concretos para que los 6 escenarios de evidencia
    produzcan exactamente la decisión esperada."""
    cur.executemany(
        "UPDATE pedidos SET cliente_id=?, monto=?, fecha=?, comprobante=?, descripcion=? "
        "WHERE id=?",
        [
            # Escenario 1: estándar (dentro de plazo, monto bajo, con comprobante)
            ("C-001", 25000, "2026-10-20", 1, "Producto defectuoso", "PED-001"),
            # Escenario 2: fuera de plazo (47 días)
            ("C-002", 25000, "2026-09-20", 1, "No funciona", "PED-015"),
            # Escenario 3: alto valor ($250.000)
            ("C-003", 250000, "2026-10-25", 1, "Producto caro", "PED-022"),
            # Escenario 4: cliente recurrente (C-004 ya tiene historial)
            ("C-004", 30000, "2026-10-28", 1, "Cambio de opinión", "PED-024"),
            # Escenario 5: posible fraude (C-005 tiene 4 devoluciones)
            ("C-005", 20000, "2026-10-29", 1, "No sirve", "PED-005"),
            # Escenario 6: falta comprobante
            ("C-006", 30000, "2026-10-30", 0, "Sin descripción", "PED-030"),
        ],
    )


def generar_politicas(cur):
    """Fragmentos de política para la colección de Chroma (RAG)."""
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


def main():
    print(f"Generando datos en: {DB_PATH}")
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    crear_tablas(cur)
    generar_clientes(cur)
    generar_pedidos(cur)
    generar_historial(cur)
    forzar_escenarios(cur)
    generar_politicas(cur)
    conn.commit()

    # Resumen
    n_clientes = cur.execute("SELECT COUNT(*) FROM clientes").fetchone()[0]
    n_pedidos = cur.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    n_hist = cur.execute("SELECT COUNT(*) FROM historical_cliente").fetchone()[0]
    n_pol = cur.execute("SELECT COUNT(*) FROM politicas").fetchone()[0]
    conn.close()

    print(f"  OK {n_clientes} clientes")
    print(f"  OK {n_pedidos} pedidos")
    print(f"  OK {n_hist} registros de historial")
    print(f"  OK {n_pol} políticas (para Chroma)")
    print("Listo. Puedes correr:  streamlit run app.py")


if __name__ == "__main__":
    main()