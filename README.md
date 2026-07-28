<div align="center">

# DevShield RAG Agent

### Agente Inteligente de documentación basado en Retrieval-Augmented Generation

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![LangChain](https://img.shields.io/badge/LangChain-1.3-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://python.langchain.com/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-2.5_Flash-4285F4?style=for-the-badge&logo=googlegemini&logoColor=white)](https://ai.google.dev/)
[![FAISS](https://img.shields.io/badge/FAISS-Vector_DB-0467DF?style=for-the-badge&logo=meta&logoColor=white)](https://faiss.ai/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

</div>

---

## Descripción

**DevShield RAG Agent** es un asistente conversacional que responde preguntas
sobre la base de conocimiento técnica, comercial y legal de **DevShield SaaS**
—una plataforma ficticia de detección de vulnerabilidades web (Inyección SQL,
XSS y escaneo de repositorios)—.

El problema que resuelve es concreto: un LLM genérico **no conoce** los precios,
los límites de escaneos ni las cláusulas legales de una empresa privada, y si se
le pregunta, los inventa. Este proyecto aplica **RAG (Retrieval-Augmented
Generation)** para anclar cada respuesta a un documento oficial, de modo que el
modelo cite datos reales en lugar de alucinarlos, y admita explícitamente cuando
una información no está en la documentación.

> DevShield SaaS es una empresa ficticia; todo el contenido del documento base
> (precios, SLAs, cláusulas legales) fue creado con fines exclusivamente
> educativos y no representa a ninguna compañía real.

### Características

| | |
|---|---|
| **Chat conversacional** | Historial con memoria: entiende preguntas de seguimiento como *"¿y en el plan Pro?"* |
| **Trazabilidad** | Cada respuesta muestra los fragmentos exactos del PDF que la fundamentan, con número de página |
| **Anti-alucinación** | Si el dato no está en el documento, el agente lo dice en lugar de inventarlo |
| **Coste cero** | Embeddings locales + capa gratuita de Gemini: sin base de datos ni facturación |
| **API Key flexible** | Se lee de `secrets`, de `.env` o se introduce en caliente desde la interfaz |
| **Arranque rápido** | Índice vectorial en memoria cacheado con `st.cache_resource` |

---

## Arquitectura técnica

El sistema se divide en dos fases: una de **indexación** (se ejecuta una sola vez
al arrancar) y otra de **consulta** (se ejecuta en cada pregunta).

```mermaid
graph TD
    subgraph FASE_1["FASE 1 · Indexación (una vez por sesión)"]
        A["devshield_docs.pdf<br/>3 páginas"] --> B["PyPDFLoader<br/>extrae texto por página"]
        B --> C["RecursiveCharacterTextSplitter<br/>chunk=1000 · overlap=150"]
        C --> D["HuggingFace all-MiniLM-L6-v2<br/>384 dimensiones · CPU · gratis"]
        D --> E[("Índice FAISS<br/>en memoria")]
    end

    subgraph FASE_2["FASE 2 · Consulta (por cada pregunta)"]
        F["Pregunta del usuario"] --> G["History-Aware Retriever<br/>reformula usando el historial"]
        G --> H["Búsqueda por similitud<br/>top-k = 4"]
        E -.-> H
        H --> I["Prompt aumentado<br/>contexto + reglas + pregunta"]
        I --> J["Gemini 2.5 Flash<br/>temperatura 0.2"]
        J --> K["Respuesta + fuentes citadas"]
    end

    style E fill:#0467DF,color:#fff
    style J fill:#4285F4,color:#fff
    style K fill:#0f9d58,color:#fff
```
