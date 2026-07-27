"""
app.py — Interfaz web del Agente Inteligente de DevShield SaaS.

Aplicación Streamlit que expone un chat conversacional sobre la base de
conocimiento técnica y legal de DevShield, resuelta mediante RAG
(LangChain + Google Gemini + FAISS).

Ejecución local:
    streamlit run app.py
"""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage

from src.agent import crear_cadena_qa, preguntar
from src.loader import ErrorDeCarga, construir_base_conocimiento

# --------------------------------------------------------------------------
# Configuración general
# --------------------------------------------------------------------------
load_dotenv()

RUTA_PDF = Path(os.getenv("RUTA_PDF", "data/devshield_docs.pdf"))
MODELOS_DISPONIBLES = ["gemini-2.5-flash", "gemini-2.5-pro"]

PREGUNTAS_SUGERIDAS = [
    "¿Cuántos escaneos incluye el plan Free?",
    "¿Puedo escanear la web de otra empresa?",
    "¿Qué pasa si el servicio cae por debajo del SLA?",
    "¿DevShield guarda una copia de mi código fuente?",
]

st.set_page_config(
    page_title="DevShield · Agente IA",
    layout="centered",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------
# Gestión de la API Key
# --------------------------------------------------------------------------
def obtener_api_key() -> str | None:
    """Resuelve la clave de Gemini por orden de prioridad.

    1. ``st.secrets`` — usado en el despliegue de Streamlit Community Cloud.
    2. Variable de entorno ``GOOGLE_API_KEY`` — usada en desarrollo local (.env).
    3. Clave introducida manualmente en el panel lateral.

    Returns:
        La clave encontrada, o ``None`` si ninguna fuente la proporciona.
    """
    try:
        if "GOOGLE_API_KEY" in st.secrets:
            return st.secrets["GOOGLE_API_KEY"]
    except FileNotFoundError:
        # En local no existe .streamlit/secrets.toml; no es un error.
        pass

    return os.getenv("GOOGLE_API_KEY") or st.session_state.get("api_key_manual")


# --------------------------------------------------------------------------
# Recursos cacheados
# --------------------------------------------------------------------------
@st.cache_resource(show_spinner="Indexando la base de conocimiento…")
def cargar_base_conocimiento(ruta: str):
    """Construye el índice FAISS una sola vez por sesión del servidor.

    ``st.cache_resource`` evita recalcular los embeddings en cada
    interacción: sin él, cada mensaje del chat volvería a leer el PDF y a
    vectorizarlo, con un coste de varios segundos por pregunta.
    """
    return construir_base_conocimiento(ruta)


@st.cache_resource(show_spinner="Conectando con Gemini…")
def cargar_cadena(_vectorstore, api_key: str, modelo: str, temperatura: float):
    """Construye la cadena de QA.

    El guion bajo en ``_vectorstore`` le indica a Streamlit que no intente
    calcular el hash de ese objeto (no es serializable); la caché se
    invalida correctamente con los demás parámetros.
    """
    return crear_cadena_qa(_vectorstore, api_key, modelo, temperatura)


# --------------------------------------------------------------------------
# Estado de la sesión
# --------------------------------------------------------------------------
def inicializar_estado() -> None:
    """Crea las claves de ``session_state`` en el primer arranque."""
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []
    if "api_key_manual" not in st.session_state:
        st.session_state.api_key_manual = ""
    if "pregunta_pendiente" not in st.session_state:
        st.session_state.pregunta_pendiente = None


def construir_historial() -> list:
    """Convierte el historial del chat al formato de mensajes de LangChain.

    Se excluye el último turno porque la pregunta actual viaja por separado
    en la clave ``input`` de la cadena.
    """
    historial = []
    for mensaje in st.session_state.mensajes[:-1]:
        if mensaje["rol"] == "user":
            historial.append(HumanMessage(content=mensaje["contenido"]))
        else:
            historial.append(AIMessage(content=mensaje["contenido"]))
    return historial


# --------------------------------------------------------------------------
# Panel lateral
# --------------------------------------------------------------------------
def render_sidebar() -> tuple[str | None, str, float]:
    """Dibuja el panel lateral y devuelve (api_key, modelo, temperatura)."""
    with st.sidebar:
        st.title("DevShield")
        st.caption("Agente Inteligente RAG")
        st.divider()

        # --- Configuración de la API Key ---
        st.subheader("Configuración")
        api_key = obtener_api_key()

        if api_key:
            origen = "secrets/entorno" if not st.session_state.api_key_manual else "manual"
            st.success(f"API Key activa ({origen})")
        else:
            st.warning("Falta la API Key de Gemini")
            st.text_input(
                "Pega tu clave de Google Gemini",
                type="password",
                key="api_key_manual",
                placeholder="AIzaSy…",
                help="La clave solo vive en tu sesión del navegador; no se almacena.",
            )
            st.link_button(
                "Obtener clave gratuita",
                "https://aistudio.google.com/app/apikey",
                use_container_width=True,
            )
            api_key = st.session_state.api_key_manual or None

        # --- Parámetros del modelo ---
        st.subheader("Modelo")
        modelo = st.selectbox("Modelo de Gemini", MODELOS_DISPONIBLES, index=0)
        temperatura = st.slider(
            "Temperatura",
            min_value=0.0,
            max_value=1.0,
            value=0.2,
            step=0.1,
            help="Valores bajos = respuestas más literales y fieles al documento.",
        )

        st.divider()

        # --- Estado de la base de conocimiento ---
        st.subheader("Base de conocimiento")
        if RUTA_PDF.exists():
            tamano_kb = RUTA_PDF.stat().st_size / 1024
            st.caption(f"`{RUTA_PDF.name}` · {tamano_kb:.0f} KB")
            st.caption("Embeddings: `all-MiniLM-L6-v2` (local)")
            st.caption("Vectores: `FAISS` (en memoria)")
        else:
            st.error(f"No se encuentra `{RUTA_PDF}`")

        if st.button("Limpiar conversación", use_container_width=True):
            st.session_state.mensajes = []
            st.rerun()

        st.divider()

        # --- Créditos ---
        st.subheader("Créditos")
        st.markdown(
            """
**Proyecto:** Agente Inteligente RAG
**Autor:** *Tu Nombre Aquí*
**Stack:** Python · Streamlit · LangChain
**LLM:** Google Gemini 2.5 Flash
**Vectores:** FAISS + HuggingFace

[![GitHub](https://img.shields.io/badge/Código-GitHub-181717?logo=github)](https://github.com/tu-usuario/devshield-rag-agent)
            """
        )
        st.caption("DevShield SaaS es una empresa ficticia creada con fines educativos.")

    return api_key, modelo, temperatura


# --------------------------------------------------------------------------
# Área principal
# --------------------------------------------------------------------------
def render_cabecera() -> None:
    """Dibuja el encabezado de la aplicación."""
    st.title("Agente Inteligente DevShield")
    st.markdown(
        "Pregunta lo que quieras sobre la **documentación técnica, comercial y legal** "
        "de DevShield SaaS. Las respuestas se generan únicamente a partir del "
        "documento oficial mediante *Retrieval-Augmented Generation*."
    )


def render_sugerencias() -> None:
    """Muestra botones de preguntas de ejemplo cuando el chat está vacío."""
    st.info("Empieza con una de estas preguntas o escribe la tuya abajo.")
    columnas = st.columns(2)
    for indice, sugerencia in enumerate(PREGUNTAS_SUGERIDAS):
        with columnas[indice % 2]:
            if st.button(sugerencia, key=f"sug_{indice}", use_container_width=True):
                st.session_state.pregunta_pendiente = sugerencia
                st.rerun()


def render_historial() -> None:
    """Repinta todos los mensajes previos del chat."""
    for mensaje in st.session_state.mensajes:
        with st.chat_message(mensaje["rol"]):
            st.markdown(mensaje["contenido"])
            if mensaje.get("fuentes"):
                render_fuentes(mensaje["fuentes"])


def render_fuentes(fuentes: list[dict]) -> None:
    """Muestra los fragmentos del PDF que fundamentan una respuesta."""
    with st.expander(f"Fuentes consultadas ({len(fuentes)})"):
        for fuente in fuentes:
            st.caption(f"**Página {fuente['pagina']}**")
            st.markdown(f"> {fuente['extracto']}")


def procesar_pregunta(cadena, pregunta: str) -> None:
    """Ejecuta la cadena RAG y añade la respuesta al historial."""
    st.session_state.mensajes.append({"rol": "user", "contenido": pregunta})

    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando la documentación…"):
            try:
                resultado = preguntar(cadena, pregunta, construir_historial())
            except Exception as error:  # noqa: BLE001 — se muestra al usuario
                st.error(
                    "No se pudo generar la respuesta. Revisa que la API Key sea "
                    f"válida y que tengas cuota disponible.\n\n**Detalle:** `{error}`"
                )
                # Se descarta la pregunta para no dejar el historial descuadrado.
                st.session_state.mensajes.pop()
                return

        st.markdown(resultado["respuesta"])

        # Se guarda solo un extracto de cada fuente: el historial de Streamlit
        # debe ser ligero y serializable.
        fuentes = [
            {
                "pagina": documento.metadata.get("page", 0) + 1,
                "extracto": documento.page_content[:280].replace("\n", " ") + "…",
            }
            for documento in resultado["fuentes"]
        ]
        if fuentes:
            render_fuentes(fuentes)

    st.session_state.mensajes.append(
        {"rol": "assistant", "contenido": resultado["respuesta"], "fuentes": fuentes}
    )


# --------------------------------------------------------------------------
# Punto de entrada
# --------------------------------------------------------------------------
def main() -> None:
    """Orquesta el renderizado completo de la aplicación."""
    inicializar_estado()
    api_key, modelo, temperatura = render_sidebar()
    render_cabecera()

    # Sin clave no se puede continuar: se avisa y se detiene el flujo.
    if not api_key:
        st.warning(
            "Configura tu **API Key de Google Gemini** en el panel lateral "
            "para activar el agente."
        )
        st.stop()

    # Carga de la base de conocimiento.
    try:
        vectorstore = cargar_base_conocimiento(str(RUTA_PDF))
    except ErrorDeCarga as error:
        st.error(f"**Error al cargar la base de conocimiento:** {error}")
        st.stop()

    cadena = cargar_cadena(vectorstore, api_key, modelo, temperatura)

    if not st.session_state.mensajes:
        render_sugerencias()

    render_historial()

    # Una sugerencia pulsada se procesa igual que un mensaje escrito.
    pregunta = st.chat_input("Escribe tu pregunta sobre DevShield…")
    if st.session_state.pregunta_pendiente:
        pregunta = st.session_state.pregunta_pendiente
        st.session_state.pregunta_pendiente = None

    if pregunta:
        procesar_pregunta(cadena, pregunta)
        st.rerun()


if __name__ == "__main__":
    main()
