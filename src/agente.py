"""
AgentExecutor con Gemini Flash para preguntas abiertas.
Requiere GEMINI_API_KEY en .env o variable de entorno.
"""
import os
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import PromptTemplate

load_dotenv()


def _tool_consultar(pedido_id: str) -> str:
    from src.tools import consultar_pedido
    return str(consultar_pedido(pedido_id.strip()))


def _tool_validar(pedido_id: str) -> str:
    from src.tools import validar_politica
    return str(validar_politica(pedido_id.strip()))


def _tool_reembolso(pedido_id: str) -> str:
    from src.tools import calcular_reembolso
    return str(calcular_reembolso(pedido_id.strip()))


def _tool_similares(texto: str) -> str:
    from src.tools import buscar_casos_similares
    return str(buscar_casos_similares(texto))


TOOLS = [
    Tool(name="consultar_pedido",
         func=_tool_consultar,
         description="Consulta los datos de un pedido por su ID (ej. PED-001)."),
    Tool(name="validar_politica",
         func=_tool_validar,
         description="Valida si un pedido cumple la política de 30 días."),
    Tool(name="calcular_reembolso",
         func=_tool_reembolso,
         description="Calcula el monto de reembolso de un pedido."),
    Tool(name="buscar_casos_similares",
         func=_tool_similares,
         description="Busca casos previos similares por significado."),
]


PROMPT = PromptTemplate.from_template("""
Eres el agente de devoluciones de TechStore. Responde en español, con claridad
y sin inventar datos. Usa las tools disponibles cuando necesites información real.

Tools disponibles:
{tools}

Usa el formato:
Question: la pregunta del usuario
Thought: qué necesitas hacer
Action: una de [{tool_names}]
Action Input: el input de la action
Observation: el resultado
... (repite Thought/Action/Action Input/Observation si hace falta)
Thought: ya tengo la respuesta
Final Answer: la respuesta al usuario

Question: {input}
{agent_scratchpad}
""")


def crear_agente():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en .env o variables de entorno.")

    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        google_api_key=api_key,
    )
    agente = create_react_agent(llm, TOOLS, PROMPT)
    return AgentExecutor(
        agent=agente,
        tools=TOOLS,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=6,
    )