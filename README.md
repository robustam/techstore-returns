
---

## 1️⃣6️⃣ `README.md`

````markdown
# TechStore Returns 🤖📦

Agente de IA que automatiza el proceso de devoluciones de una tienda de tecnología simulada.
Recibe un ID de pedido, valida la política de 30 días, consulta el historial del cliente,
decide con 6 reglas priorizadas y ejecuta acciones (reembolso, etiqueta, CRM, notificación)
o escala el caso con justificación trazable.

> **Evaluación Parcial N°2 · ISY0101 Ingeniería de Soluciones con IA**
> Integrantes: Lorena Ledezma Sánchez · [Integrante 2]
> Docente: [nombre] · Fecha: 6 de noviembre de 2026

---

## 📋 Tabla de contenidos

1. [Características](#-características)
2. [Arquitectura](#-arquitectura)
3. [Stack tecnológico](#-stack-tecnológico)
4. [Instalación paso a paso](#-instalación-paso-a-paso)
5. [Uso](#-uso)
6. [Estructura del proyecto](#-estructura-del-proyecto)
7. [Las 6 reglas del planner](#-las-6-reglas-del-planner)
8. [Pruebas y evidencias](#-pruebas-y-evidencias)
9. [Limitaciones](#-limitaciones)
10. [Referencias](#-referencias)

---

## ✨ Características

- ✅ **Validación automática** de la política de devolución (30 días).
- ✅ **Memoria de 3 niveles**: corto plazo (sesión), largo plazo (SQLite) y semántica (Chroma).
- ✅ **Planner determinista** con 6 reglas priorizadas → decisiones reproducibles y auditables.
- ✅ **7 tools** expuestas al agente vía LangChain.
- ✅ **Rama LLM abierta** con `AgentExecutor` + Gemini Flash para preguntas no estructuradas.
- ✅ **Traza visible** en la interfaz Streamlit (tool → salida paso a paso).
- ✅ **Suite de pruebas** con `pytest` y generador de evidencias.

---

## 🏗️ Arquitectura

Flujo híbrido: tools fijas en secuencia + planner determinista + LLM para razonamiento abierto.
