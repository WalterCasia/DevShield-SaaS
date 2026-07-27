"""
Script auxiliar: genera el documento base `data/devshield_docs.pdf` (3 páginas)
con la base de conocimiento de DevShield SaaS.

Uso:
    python scripts/generar_pdf.py

Solo requiere reportlab (no forma parte de las dependencias de la app,
el PDF generado se versiona junto al repositorio).
"""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

RUTA_SALIDA = Path(__file__).resolve().parent.parent / "data" / "devshield_docs.pdf"

AZUL = colors.HexColor("#1a3c6e")
GRIS = colors.HexColor("#f2f4f8")

estilos = getSampleStyleSheet()
h1 = ParagraphStyle("H1", parent=estilos["Heading1"], textColor=AZUL, spaceAfter=8)
h2 = ParagraphStyle("H2", parent=estilos["Heading2"], textColor=AZUL, spaceBefore=10, spaceAfter=4)
cuerpo = ParagraphStyle(
    "Cuerpo", parent=estilos["Normal"], fontSize=9.5, leading=13, alignment=TA_JUSTIFY, spaceAfter=5
)
vineta = ParagraphStyle("Vineta", parent=cuerpo, leftIndent=14, bulletIndent=4)
celda = ParagraphStyle("Celda", parent=estilos["Normal"], fontSize=8.5, leading=11)
celda_titulo = ParagraphStyle("CeldaTitulo", parent=celda, textColor=colors.white, fontName="Helvetica-Bold")


def p(texto: str, estilo=cuerpo) -> Paragraph:
    return Paragraph(texto, estilo)


def b(texto: str) -> Paragraph:
    return Paragraph(texto, vineta, bulletText="•")


def construir_documento() -> list:
    """Arma la lista de elementos (story) de las 3 páginas del PDF."""
    story = []

    # ------------------------- PÁGINA 1 -------------------------
    story += [
        p("DevShield SaaS - Base de Conocimiento Oficial", h1),
        p("<b>Versión 2.4 - Julio de 2026.</b> Documentación técnica, comercial y legal. "
          "Documento ficticio con fines educativos."),
        p("1. Arquitectura general y back-end", h2),
        p("<b>DevShield SaaS</b> es una plataforma en la nube para la <b>detección automatizada de "
          "vulnerabilidades web</b>: Inyección SQL (SQLi) mediante análisis estático (SAST) y dinámico "
          "(DAST), Cross-Site Scripting (XSS) reflejado, almacenado y basado en DOM, y escaneo de "
          "repositorios Git (GitHub, GitLab y Bitbucket) para detectar secretos expuestos, dependencias "
          "vulnerables (CVE) y configuraciones inseguras."),
        p("La plataforma usa una <b>arquitectura de microservicios</b> sobre Kubernetes:"),
        b("<b>API Gateway (Python 3.12 + FastAPI):</b> recibe solicitudes, autentica con JWT "
          "(expiración de 24 horas) y encola trabajos en RabbitMQ."),
        b("<b>Motor de escaneo (Java 21 + Spring Boot):</b> ejecuta cada análisis dentro de un "
          "<b>contenedor Docker aislado y efímero</b> (sandbox) sin acceso a la red interna, que se "
          "destruye al finalizar. El código de un cliente jamás comparte entorno con el de otro."),
        b("<b>PostgreSQL 16:</b> resultados, usuarios y facturación; reportes cifrados en reposo con AES-256."),
        b("<b>Redis:</b> sesiones y resultados intermedios con TTL de 15 minutos."),
        b("<b>Panel web (React + TypeScript):</b> dashboard con reportes descargables en PDF y JSON."),
        p("Toda la comunicación entre servicios viaja cifrada con <b>TLS 1.3</b>. Regiones disponibles: "
          "us-east, eu-west y sa-east (São Paulo)."),
        p("1.1 Ciclo de vida de un escaneo", h2),
        b("El usuario registra la URL o conecta su repositorio mediante OAuth."),
        b("El API Gateway valida la propiedad del dominio o repositorio (archivo de verificación o registro DNS TXT)."),
        b("El trabajo entra a la cola y un contenedor Docker aislado ejecuta el análisis."),
        b("El motor Java genera el reporte con severidades Crítica, Alta, Media, Baja e Informativa, "
          "según el estándar CVSS 3.1."),
        b("El contenedor se destruye y el reporte cifrado queda disponible en el dashboard."),
        p("Duración promedio: <b>8 a 12 minutos</b> para aplicaciones medianas (hasta 200 endpoints) y "
          "<b>3 a 5 minutos</b> para repositorios de hasta 500 MB."),
        PageBreak(),
    ]

    # ------------------------- PÁGINA 2 -------------------------
    filas = [
        ["Característica", "Free", "Pro", "Enterprise"],
        ["Precio mensual", "US$ 0", "US$ 49", "US$ 299"],
        ["Escaneos web por mes", "5", "100", "Ilimitados"],
        ["Repositorios conectados", "1", "10", "Ilimitados"],
        ["Tamaño máx. por repositorio", "100 MB", "500 MB", "5 GB"],
        ["Escaneos simultáneos", "1", "3", "10"],
        ["Detección SQLi y XSS", "Sí", "Sí", "Sí"],
        ["Detección de secretos en código", "No", "Sí", "Sí"],
        ["Reportes", "Solo PDF", "PDF y JSON", "PDF, JSON y API"],
        ["Retención de reportes", "30 días", "12 meses", "24 meses"],
        ["Usuarios por cuenta", "1", "5", "Ilimitados"],
        ["Soporte", "Foro comunidad", "Correo (24 h hábiles)", "Prioritario 24/7"],
        ["API CI/CD", "No", "1.000 llamadas/mes", "Ilimitada"],
    ]
    tabla = Table(
        [[Paragraph(c, celda_titulo if i == 0 else celda) for c in fila] for i, fila in enumerate(filas)],
        colWidths=[5.4 * cm, 3.2 * cm, 4.0 * cm, 4.0 * cm],
    )
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c8cdd6")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))

    story += [
        p("2. Planes de suscripción y precios", h2),
        tabla,
        Spacer(1, 6),
        b("El plan <b>Pro anual</b> tiene 20 % de descuento (US$ 470/año). Los escaneos no utilizados "
          "<b>no se acumulan</b> para el mes siguiente."),
        b("El plan <b>Enterprise</b> incluye región dedicada opcional y firma de DPA personalizado."),
        p("2.1 Preguntas frecuentes (FAQ)", h2),
        b("<b>¿Puedo cambiar de plan?</b> Sí: los upgrades se aplican de inmediato con cobro prorrateado; "
          "los downgrades, al inicio del siguiente ciclo de facturación."),
        b("<b>¿Qué pasa si supero mi límite de escaneos?</b> El escaneo se bloquea; en Pro y Enterprise "
          "se pueden comprar 10 escaneos adicionales por US$ 9."),
        b("<b>¿DevShield modifica mi código o mi aplicación?</b> No: todos los análisis son de solo "
          "lectura y las pruebas DAST usan cargas útiles seguras."),
        b("<b>¿Cómo restablezco mi contraseña?</b> Con la opción 'Olvidé mi contraseña'; el enlace "
          "expira en 30 minutos."),
        b("<b>¿Hay prueba gratuita del plan Pro?</b> Sí, 14 días sin tarjeta de crédito; al terminar, "
          "la cuenta pasa automáticamente al plan Free."),
        p("2.2 Acuerdos de Nivel de Servicio (SLA)", h2),
        b("<b>Disponibilidad garantizada:</b> 99,5 % mensual (Free y Pro) y <b>99,9 % (Enterprise)</b>."),
        b("<b>Créditos por incumplimiento</b> (solo planes de pago): entre 99,0 % y el objetivo: 10 % "
          "de crédito; entre 95,0 % y 98,99 %: 25 %; menor a 95,0 %: 50 %. Deben solicitarse dentro de "
          "los 30 días posteriores al incidente escribiendo a sla@devshield.io."),
        b("<b>Primera respuesta de soporte:</b> Free: sin garantía (foro). Pro: 24 horas hábiles. "
          "Enterprise: 1 hora para incidentes críticos (P1) y 4 horas para P2."),
        b("El mantenimiento programado se anuncia con 72 horas de antelación y no computa como downtime."),
        PageBreak(),
    ]

    # ------------------------- PÁGINA 3 -------------------------
    story += [
        p("3. Términos de uso", h2),
        b("<b>Autorización obligatoria:</b> solo se pueden escanear aplicaciones, dominios y repositorios "
          "<b>propios o con autorización expresa y por escrito</b> del titular. Queda <b>estrictamente "
          "prohibido</b> escanear activos de terceros sin consentimiento. La verificación de propiedad "
          "(DNS TXT o archivo en el servidor) es requisito previo a todo escaneo web."),
        b("<b>Sanciones:</b> el primer intento de escaneo no autorizado suspende la cuenta por 30 días; "
          "la reincidencia implica el cierre definitivo sin reembolso y, cuando la ley lo exija, la "
          "notificación a las autoridades competentes."),
        b("<b>Uso aceptable:</b> prohibido revender el servicio, hacer ingeniería inversa de la "
          "plataforma o usar los reportes para atacar sistemas de terceros."),
        b("<b>Responsabilidad:</b> DevShield no garantiza detectar el 100 % de las vulnerabilidades. "
          "Su responsabilidad total se limita al monto pagado por el cliente en los 12 meses anteriores "
          "al reclamo."),
        b("<b>Cancelación:</b> disponible en cualquier momento desde el panel; no hay reembolsos por "
          "periodos parciales, salvo lo dispuesto en el SLA."),
        p("3.1 Política de privacidad y manejo del código fuente", h2),
        b("<b>Propiedad del código:</b> el código fuente es y seguirá siendo <b>propiedad exclusiva del "
          "cliente</b>; DevShield no adquiere ningún derecho sobre él."),
        b("<b>Procesamiento efímero:</b> el código clonado vive solo dentro del contenedor Docker "
          "aislado y <b>se elimina de forma irreversible al terminar el análisis</b> (máximo 60 minutos "
          "después). Nunca se almacenan copias permanentes del código; solo persisten los reportes."),
        b("<b>Confidencialidad:</b> los empleados de DevShield no acceden al código del cliente, salvo "
          "solicitud de soporte autorizada por escrito por el cliente y siempre bajo NDA."),
        b("<b>Datos personales:</b> solo se recopilan nombre, correo electrónico y datos de facturación. "
          "Nunca se venden datos a terceros. Cumplimiento de GDPR (UE) y LGPD (Brasil). Los pagos los "
          "procesa un proveedor certificado PCI-DSS; DevShield no almacena números de tarjeta."),
        b("<b>Derechos del usuario:</b> acceso, rectificación y supresión escribiendo a "
          "privacy@devshield.io; respuesta en máximo 15 días hábiles."),
        b("<b>Eliminación de cuenta:</b> reportes y datos personales se borran definitivamente en 30 "
          "días, salvo la obligación legal de retener datos de facturación durante 5 años."),
        Spacer(1, 12),
        p("<i>(c) 2026 DevShield Inc. - Documento ficticio creado con fines educativos para el "
          "proyecto de Agente Inteligente RAG.</i>"),
    ]
    return story


def main() -> None:
    RUTA_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(RUTA_SALIDA),
        pagesize=letter,
        title="DevShield SaaS - Base de Conocimiento",
        author="DevShield Inc.",
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    doc.build(construir_documento())
    print(f"PDF generado correctamente en: {RUTA_SALIDA}")


if __name__ == "__main__":
    main()
