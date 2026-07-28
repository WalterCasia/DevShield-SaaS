"""
agent.py — Capa de razonamiento (la "G" de RAG: Generation).

Responsabilidad única: construir la cadena conversacional que conecta el
retriever de FAISS con el modelo Gemini.

La cadena se arma con la API moderna de LangChain (LCEL) en dos etapas:

1. **Retriever consciente del historial**
   (``create_history_aware_retriever``): reformula la pregunta del usuario
   en una consulta autocontenida antes de buscar. Sin esto, un seguimiento
   como "¿y cuántos en el plan Pro?" no recuperaría nada útil, porque le
   falta el sujeto de la conversación anterior.

2. **Cadena de respuesta** (``create_stuff_documents_chain`` +
   ``create_retrieval_chain``): inserta ("stuff") los fragmentos recuperados
   en el prompt y pide a Gemini una respuesta fundamentada solo en ellos.

Al igual que `loader.py`, este módulo no depende de Streamlit.
"""

from __future__ import annotations

import logging

from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable
from langchain_core.vectorstores import VectorStore
from langchain_google_genai import ChatGoogleGenerativeAI

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuración por defecto
# --------------------------------------------------------------------------

# gemini-2.5-flash: rápido, con ventana de contexto amplia y una capa
# gratuita generosa, ideal para un asistente de documentación.
# (gemini-1.5-flash/pro fueron retirados por Google; gemini-2.5-flash/pro
# tienen retiro anunciado para el 16-oct-2026 — si esta app se usa después
# de esa fecha, migrar a gemini-3.5-flash, que no tiene fecha de baja anunciada).
MODELO_LLM = "gemini-2.5-flash"

# Temperatura baja: en un agente sobre documentación normativa queremos
# fidelidad al texto, no creatividad.
TEMPERATURA = 0.2

# Número de fragmentos a recuperar por consulta. Con 4 hay contexto
# suficiente para respuestas cruzadas (p. ej. comparar dos planes) sin
# saturar el prompt con ruido.
FRAGMENTOS_RECUPERADOS = 4


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------

# Prompt 1: reformula la pregunta usando el historial de la conversación.
PROMPT_REFORMULACION = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Dado el historial de la conversación y la última pregunta del usuario, "
            "reformúlala como una pregunta independiente y autocontenida que se "
            "entienda sin leer el historial. "
            "NO la respondas: devuelve únicamente la pregunta reformulada. "
            "Si la pregunta ya es autocontenida, devuélvela tal cual.",
        ),
        MessagesPlaceholder("historial"),
        ("human", "{input}"),
    ]
)

# Prompt 2: genera la respuesta final anclada al contexto recuperado.
PROMPT_RESPUESTA = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres el Asistente Virtual oficial de **DevShield SaaS**, una plataforma "
            "de detección de vulnerabilidades web. Respondes preguntas de clientes y "
            "del equipo técnico basándote EXCLUSIVAMENTE en la documentación oficial.\n\n"
            "REGLAS DE RESPUESTA:\n"
            "1. Responde únicamente con información presente en el CONTEXTO. "
            "Nunca inventes datos, precios, límites ni plazos.\n"
            "2. Si el contexto no contiene la respuesta, dilo con franqueza: "
            "'No encuentro esa información en la documentación oficial de DevShield.' "
            "y sugiere contactar a soporte. No especules.\n"
            "3. Sé preciso con las cifras (precios, límites de escaneos, porcentajes "
            "de SLA, plazos): cítalas exactamente como aparecen.\n"
            "4. Responde siempre en español, con tono profesional y cercano.\n"
            "5. Usa viñetas o tablas cuando compares planes o enumeres condiciones; "
            "para preguntas simples, responde en dos o tres frases.\n"
            "6. En temas legales o de privacidad, sé literal y no relativices las "
            "prohibiciones.\n\n"
            "CONTEXTO:\n{context}",
        ),
        MessagesPlaceholder("historial"),
        ("human", "{input}"),
    ]
)


# --------------------------------------------------------------------------
# Construcción de la cadena
# --------------------------------------------------------------------------
def crear_llm(
    api_key: str,
    modelo: str = MODELO_LLM,
    temperatura: float = TEMPERATURA,
) -> ChatGoogleGenerativeAI:
    """Instancia el cliente de Gemini.

    Args:
        api_key: Clave de la API de Google AI Studio.
        modelo: Identificador del modelo Gemini.
        temperatura: Aleatoriedad de la generación (0 = determinista).

    Returns:
        Cliente ``ChatGoogleGenerativeAI`` configurado.
    """
    return ChatGoogleGenerativeAI(
        model=modelo,
        google_api_key=api_key,
        temperature=temperatura,
        # Evita que la cadena se cuelgue indefinidamente si la API no responde.
        timeout=60,
        max_retries=2,
    )


def crear_cadena_qa(
    vectorstore: VectorStore,
    api_key: str,
    modelo: str = MODELO_LLM,
    temperatura: float = TEMPERATURA,
    k: int = FRAGMENTOS_RECUPERADOS,
) -> Runnable:
    """Construye la cadena conversacional de preguntas y respuestas.

    Args:
        vectorstore: Índice FAISS creado por ``loader.construir_base_conocimiento``.
        api_key: Clave de la API de Google Gemini.
        modelo: Modelo de Gemini a utilizar.
        temperatura: Aleatoriedad de la generación.
        k: Número de fragmentos a recuperar por consulta.

    Returns:
        Cadena invocable con ``{"input": str, "historial": list}`` que
        devuelve un diccionario con las claves ``answer`` (la respuesta) y
        ``context`` (los fragmentos que la fundamentan).
    """
    llm = crear_llm(api_key, modelo, temperatura)

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

    # Etapa 1: el retriever entiende preguntas de seguimiento.
    retriever_con_historial = create_history_aware_retriever(
        llm=llm,
        retriever=retriever,
        prompt=PROMPT_REFORMULACION,
    )

    # Etapa 2: los fragmentos recuperados se insertan en el prompt final.
    cadena_documentos = create_stuff_documents_chain(
        llm=llm,
        prompt=PROMPT_RESPUESTA,
    )

    logger.info("Cadena QA construida con el modelo %s (k=%d)", modelo, k)
    return create_retrieval_chain(retriever_con_historial, cadena_documentos)


def preguntar(cadena: Runnable, pregunta: str, historial: list | None = None) -> dict:
    """Envía una pregunta a la cadena y normaliza la respuesta.

    Args:
        cadena: Cadena devuelta por :func:`crear_cadena_qa`.
        pregunta: Texto de la pregunta del usuario.
        historial: Mensajes previos como objetos ``HumanMessage`` / ``AIMessage``.

    Returns:
        Diccionario con ``respuesta`` (str) y ``fuentes`` (list[Document]).
    """
    resultado = cadena.invoke({"input": pregunta, "historial": historial or []})
    return {
        "respuesta": resultado.get("answer", ""),
        "fuentes": resultado.get("context", []),
    }
