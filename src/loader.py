"""
loader.py — Capa de ingesta de datos (la "R" de RAG: Retrieval).

Responsabilidad única: convertir el PDF de la base de conocimiento de
DevShield en un índice vectorial FAISS consultable por similitud semántica.

Flujo:
    PDF -> PyPDFLoader -> RecursiveCharacterTextSplitter -> Embeddings
    (HuggingFace, local y gratuito) -> índice FAISS en memoria.

Este módulo es deliberadamente independiente de Streamlit: no importa `st`
ni conoce la interfaz. Así puede reutilizarse desde un script, una API o
un test unitario. El cacheo de resultados es responsabilidad de `app.py`.
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Configuración por defecto
# --------------------------------------------------------------------------

# Modelo de embeddings local: 22 M de parámetros, 384 dimensiones.
# Se ejecuta en CPU y NO consume cuota de ninguna API de pago.
MODELO_EMBEDDINGS = "sentence-transformers/all-MiniLM-L6-v2"

# Tamaño de fragmento en caracteres. 1000 es un buen equilibrio para un
# documento normativo: suficiente contexto para que un párrafo (p. ej. una
# fila de la tabla de precios) quede completo, sin diluir la señal semántica.
TAMANO_FRAGMENTO = 1000

# Solapamiento entre fragmentos: evita cortar una idea a la mitad y perderla.
SOLAPAMIENTO = 150


class ErrorDeCarga(Exception):
    """Se lanza cuando el documento base no puede leerse o está vacío."""


# --------------------------------------------------------------------------
# 1. Carga del documento
# --------------------------------------------------------------------------
def cargar_pdf(ruta_pdf: str | Path) -> list[Document]:
    """Lee el PDF y devuelve una lista de documentos (uno por página).

    Args:
        ruta_pdf: Ruta al archivo PDF de la base de conocimiento.

    Returns:
        Lista de objetos ``Document``, cada uno con el texto de una página
        y metadatos (``source`` y ``page``).

    Raises:
        ErrorDeCarga: Si el archivo no existe o no contiene texto extraíble
            (por ejemplo, si el PDF es una imagen escaneada sin OCR).
    """
    ruta = Path(ruta_pdf)

    if not ruta.exists():
        raise ErrorDeCarga(
            f"No se encontró el documento base en '{ruta}'. "
            "Verifica que el PDF esté versionado en la carpeta 'data/'."
        )

    logger.info("Cargando PDF desde %s", ruta)
    paginas = PyPDFLoader(str(ruta)).load()

    # Un PDF escaneado carga páginas, pero todas sin texto: lo detectamos aquí
    # en lugar de dejar que el RAG responda vacío más adelante.
    if not any(pagina.page_content.strip() for pagina in paginas):
        raise ErrorDeCarga(
            f"El PDF '{ruta.name}' no contiene texto extraíble. "
            "Si es un documento escaneado, necesita pasar antes por un OCR."
        )

    logger.info("PDF cargado: %d páginas", len(paginas))
    return paginas


# --------------------------------------------------------------------------
# 2. Fragmentación (chunking)
# --------------------------------------------------------------------------
def dividir_en_fragmentos(
    documentos: list[Document],
    tamano: int = TAMANO_FRAGMENTO,
    solapamiento: int = SOLAPAMIENTO,
) -> list[Document]:
    """Divide los documentos en fragmentos manejables para el modelo.

    Usa ``RecursiveCharacterTextSplitter``, que intenta cortar primero por
    separadores "naturales" (párrafo -> línea -> frase -> palabra), de modo que
    los fragmentos conserven unidades de significado completas.

    Args:
        documentos: Páginas devueltas por :func:`cargar_pdf`.
        tamano: Longitud máxima de cada fragmento, en caracteres.
        solapamiento: Caracteres compartidos entre fragmentos consecutivos.

    Returns:
        Lista de fragmentos listos para vectorizar.
    """
    divisor = RecursiveCharacterTextSplitter(
        chunk_size=tamano,
        chunk_overlap=solapamiento,
        separators=["\n\n", "\n", ". ", " ", ""],
        length_function=len,
    )

    fragmentos = divisor.split_documents(documentos)
    logger.info("Documento dividido en %d fragmentos", len(fragmentos))
    return fragmentos


# --------------------------------------------------------------------------
# 3. Vectorización e indexado
# --------------------------------------------------------------------------
def crear_indice_vectorial(fragmentos: list[Document]) -> FAISS:
    """Convierte los fragmentos en vectores y los indexa con FAISS.

    Los embeddings se calculan **localmente** con `all-MiniLM-L6-v2`, así que
    esta operación no consume cuota de la API de Gemini. El índice vive en
    memoria RAM: es instantáneo de consultar y no requiere base de datos
    externa, a costa de reconstruirse cuando el proceso se reinicia.

    Args:
        fragmentos: Fragmentos devueltos por :func:`dividir_en_fragmentos`.

    Returns:
        Índice ``FAISS`` listo para usarse como *retriever*.
    """
    logger.info("Generando embeddings con %s", MODELO_EMBEDDINGS)

    embeddings = HuggingFaceEmbeddings(
        model_name=MODELO_EMBEDDINGS,
        model_kwargs={"device": "cpu"},
        # Vectores normalizados: la similitud coseno se vuelve un simple
        # producto punto, que es lo que FAISS optimiza.
        encode_kwargs={"normalize_embeddings": True},
    )

    indice = FAISS.from_documents(documents=fragmentos, embedding=embeddings)
    logger.info("Índice FAISS creado con %d vectores", len(fragmentos))
    return indice


# --------------------------------------------------------------------------
# 4. Función orquestadora (punto de entrada del módulo)
# --------------------------------------------------------------------------
def construir_base_conocimiento(ruta_pdf: str | Path) -> FAISS:
    """Ejecuta el pipeline completo de ingesta: PDF -> índice FAISS.

    Es la única función que `app.py` necesita invocar de este módulo.

    Args:
        ruta_pdf: Ruta al PDF de la base de conocimiento de DevShield.

    Returns:
        Índice ``FAISS`` poblado y listo para responder consultas.

    Raises:
        ErrorDeCarga: Si el PDF no existe o no tiene texto extraíble.
    """
    paginas = cargar_pdf(ruta_pdf)
    fragmentos = dividir_en_fragmentos(paginas)
    return crear_indice_vectorial(fragmentos)
