"""Genera la presentación TechStore Returns en formato .pptx."""
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pathlib import Path
import os

# ---- Paleta de colores ----
AZUL = RGBColor(0x1F, 0x38, 0x64)
GRIS = RGBColor(0x40, 0x40, 0x40)
VERDE = RGBColor(0x27, 0xAE, 0x60)
ROJO = RGBColor(0xC0, 0x39, 0x2B)
BLANCO = RGBColor(0xFF, 0xFF, 0xFF)

prs = Presentation()
prs.slide_width = Inches(13.333)   # 16:9
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

def add_slide(titulo, bullets, notas="", color_titulo=AZUL):
    slide = prs.slides.add_slide(BLANK)
    # Título
    tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.3), Inches(0.9))
    tf = tb.text_frame
    tf.text = titulo
    tf.paragraphs[0].font.size = Pt(32)
    tf.paragraphs[0].font.bold = True
    tf.paragraphs[0].font.color.rgb = color_titulo
    # Bullets
    tb2 = slide.shapes.add_textbox(Inches(0.6), Inches(1.4), Inches(12.1), Inches(5.5))
    tf2 = tb2.text_frame
    tf2.word_wrap = True
    for i, b in enumerate(bullets):
        p = tf2.paragraphs[0] if i == 0 else tf2.add_paragraph()
        p.text = b
        p.font.size = Pt(20)
        p.font.color.rgb = GRIS
        p.space_after = Pt(10)
    # Notas del orador
    if notas:
        slide.notes_slide.notes_text_frame.text = notas
    return slide

# ---------- Slide 1: Portada ----------
s = prs.slides.add_slide(BLANK)
tb = s.shapes.add_textbox(Inches(1), Inches(2.5), Inches(11), Inches(1.5))
tb.text_frame.text = "📦 TechStore Returns"
tb.text_frame.paragraphs[0].font.size = Pt(54)
tb.text_frame.paragraphs[0].font.bold = True
tb.text_frame.paragraphs[0].font.color.rgb = AZUL
tb.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER

tb2 = s.shapes.add_textbox(Inches(1), Inches(4), Inches(11), Inches(2))
tf2 = tb2.text_frame
tf2.text = "Automatización de devoluciones con IA"
tf2.paragraphs[0].font.size = Pt(28)
tf2.paragraphs[0].font.color.rgb = GRIS
tf2.paragraphs[0].alignment = PP_ALIGN.CENTER
for linea in ["", "Evaluación Parcial N°2 · ISY0101 Ingeniería de Soluciones con IA",
              "Lorena Ledezma Sánchez · [Integrante 2]", "6 de noviembre de 2026"]:
    p = tf2.add_paragraph(); p.text = linea; p.font.size = Pt(18); p.font.color.rgb = GRIS; p.alignment = PP_ALIGN.CENTER
s.notes_slide.notes_text_frame.text = "Buenos días. Somos Lorena y [Integrante 2], presentamos TechStore Returns, un agente que automatiza devoluciones."

# ---------- Slide 2 ----------
add_slide("El problema", [
    "🔴 Hoy: devoluciones revisadas manualmente", "🔴 Política aplicada de forma inconsistente",
    "🔴 Sin memoria del historial del cliente", "", "✅ Requerimiento:",
    "   • Resolver casos estándar sin intervención", "   • Aplicar la política de 30 días uniformemente",
    "   • Derivar a humano: fuera de plazo, monto alto, fraude", "",
    "Alcance: sin pagos reales · sin couriers · sin reclamos legales · datos ficticios"
], notas="El problema de fondo es triple: lentitud, inconsistencia y ceguera sobre el historial.")

# ---------- Slide 3: Arquitectura ----------
s3 = add_slide("Arquitectura híbrida", [
    "Usuario (Streamlit) → procesar_solicitud → tools → Planner → ramas", "",
    "3 ramas de decisión:", "   🟢 Aprobar (reembolso → etiqueta → CRM → notificación)",
    "   🔴 Escalar / solicitar aprobación (CRM → notificación)", "   🟡 Solicitar información (notificación)",
    "", "Determinista en el flujo principal · LLM solo para preguntas abiertas",
    "", "⬇️ [Insertar diagrama PNG aquí]"
], notas="La arquitectura es híbrida: tools en secuencia fija + planner con reglas.")

# ---------- Slide 4 ----------
add_slide("Las 7 tools", [
    "📋 Consultas:", "   • consultar_pedido · validar_politica · buscar_casos_similares", "",
    "🧮 Cálculos:", "   • calcular_reembolso", "", "✍️ Escrituras:",
    "   • generar_etiqueta · actualizar_crm · notificar_cliente", "",
    "buscar_casos_similares usa Chroma + all-MiniLM-L6-v2 (búsqueda por significado)"
])

# ---------- Slide 5 ----------
add_slide("Memoria en 3 niveles", [
    "🕐 Corto plazo: ConversationBufferMemory (sesión)", "   Mantiene el hilo de la conversación", "",
    "💾 Largo plazo: tabla historical_cliente en SQLite", "   Reconoce clientes entre sesiones", "",
    "🧠 Semántica: Chroma + all-MiniLM-L6-v2", "   Recupera políticas y casos por significado", "",
    "⚡ La memoria de largo plazo habilita la regla de fraude (3+ devoluciones en 90 días)"
])

# ---------- Slide 6 ----------
add_slide("Planner: 6 reglas priorizadas", [
    "1. 🔴 Fuera de plazo (30 días)          → escalar",
    "2. 🔴 Monto > $100.000                  → solicitar_aprobacion",
    "3. 🔴 ≥ 3 devoluciones en 90 días       → escalar_fraude",
    "4. 🟢 Recurrente + monto < $50.000      → aprobar_preferente",
    "5. 🟡 Falta comprobante o descripción   → solicitar_info",
    "6. 🟢 Caso estándar                     → aprobar_estandar", "",
    "⚠️ Riesgo primero, trato amable después.",
    "Si la regla 6 fuera la primera, ningún caso se validaría."
])

# ---------- Slide 7: Evidencias ----------
s7 = add_slide("Evidencias: 6/6 escenarios + 16 tests", [
    "✅ PED-001 → aprobar_estandar",
    "✅ PED-015 → escalar (fuera de plazo, 47 días)",
    "✅ PED-022 → solicitar_aprobacion ($250.000)",
    "✅ PED-024 → aprobar_preferente (cliente recurrente)",
    "✅ PED-005 → escalar_fraude (4 devoluciones)",
    "✅ PED-030 → solicitar_info (sin comprobante)", "",
    "📊 16/16 tests pasando", "⬇️ [Insertar capturas aquí]"
])

# ---------- Slide 8 ----------
add_slide("¿Por qué estos componentes?", [
    "LangChain      → patrón agente + tools + memoria sin router manual",
    "Gemini Flash   → capa gratuita · baja latencia · buen tool-calling",
    "SQLite         → volumen pequeño · .db versionable en repo",
    "Chroma + local → búsqueda por significado · sin costo por consulta",
    "Planner det.   → reproducible · auditable · explicable",
    "Streamlit      → traza visible con muy poco código", "",
    "🎯 Separar lo determinista de lo generativo = trazabilidad + confianza"
])

# ---------- Slide 9 ----------
add_slide("Limitaciones y trabajo futuro", [
    "⚠️ Limitaciones:",
    "   • No procesa pagos reales ni couriers", "   • No maneja reclamos legales",
    "   • Sin métricas de acierto en producción", "", "🔮 Trabajo futuro:",
    "   • Extraer módulo de decisión puro", "   • Logging estructurado desde el inicio",
    "   • Migrar a PostgreSQL si escala", "   • Panel de métricas"
])

# ---------- Slide 10 ----------
add_slide("Conclusiones", [
    "💡 Un agente útil delimita bien dónde decide el LLM y dónde no", "",
    "💡 La trazabilidad es un requisito de negocio, no un lujo técnico", "",
    "💡 Separar lo determinista de lo generativo =",
    "   decisiones reproducibles, auditables y explicables", "", "",
    "🎬 Demo: streamlit run app.py", "🔗 github.com/robustam/techstore-returns", "",
    "¡Gracias! — ¿Preguntas?"
])

# Guardar
prs.save("TechStore_Returns_Presentacion.pptx")
print("✅ Presentación generada: TechStore_Returns_Presentacion.pptx")