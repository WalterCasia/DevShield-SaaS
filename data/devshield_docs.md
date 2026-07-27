# DevShield SaaS — Base de Conocimiento Oficial

**Versión del documento:** 2.4 | **Última actualización:** Julio de 2026
**Clasificación:** Pública — Documentación técnica, comercial y legal

---

## PÁGINA 1 — ARQUITECTURA GENERAL Y BACK-END

### 1.1 ¿Qué es DevShield SaaS?

DevShield SaaS es una plataforma digital en la nube para la **detección automatizada de
vulnerabilidades web**. Permite a equipos de desarrollo y seguridad analizar sus aplicaciones
y repositorios de código en busca de fallos críticos, entre ellos:

- **Inyección SQL (SQLi):** detección de consultas dinámicas sin parametrizar mediante análisis
  estático (SAST) y pruebas dinámicas (DAST) sobre los endpoints expuestos.
- **Cross-Site Scripting (XSS):** identificación de XSS reflejado, almacenado y basado en DOM.
- **Escaneo de repositorios:** análisis de repositorios Git (GitHub, GitLab y Bitbucket) para
  detectar secretos expuestos (API keys, tokens, credenciales), dependencias vulnerables (CVE)
  y configuraciones inseguras.

### 1.2 Arquitectura técnica

DevShield está construido sobre una **arquitectura de microservicios** desplegada en Kubernetes:

- **API Gateway y orquestación (Python 3.12 + FastAPI):** recibe las solicitudes de escaneo,
  gestiona la autenticación mediante tokens JWT con expiración de 24 horas y encola los trabajos
  en **RabbitMQ**.
- **Motor de escaneo (Java 21 + Spring Boot):** núcleo de análisis que ejecuta las reglas de
  detección. Cada escaneo se ejecuta dentro de un **contenedor Docker aislado y efímero**
  (sandbox) sin acceso a la red interna, que se destruye al finalizar el análisis. Este
  aislamiento garantiza que el código de un cliente jamás comparta entorno de ejecución con
  el de otro cliente.
- **Base de datos (PostgreSQL 16):** almacena resultados de escaneos, usuarios y facturación.
  Los reportes se cifran en reposo con **AES-256**.
- **Caché y colas (Redis):** sesiones y resultados intermedios con TTL de 15 minutos.
- **Panel web (React + TypeScript):** dashboard con reportes descargables en PDF y JSON.

Toda la comunicación entre servicios viaja cifrada con **TLS 1.3**. Las regiones de despliegue
disponibles son: `us-east`, `eu-west` y `sa-east` (São Paulo).

### 1.3 Ciclo de vida de un escaneo

1. El usuario registra la URL o conecta su repositorio mediante OAuth.
2. El API Gateway valida la propiedad del dominio/repositorio (archivo de verificación o DNS TXT).
3. El trabajo entra a la cola y un contenedor Docker aislado ejecuta el análisis.
4. El motor Java genera el reporte con severidades **Crítica, Alta, Media, Baja e Informativa**,
   usando el estándar de puntuación **CVSS 3.1**.
5. El contenedor se destruye y el reporte cifrado queda disponible en el dashboard.

La duración promedio de un escaneo completo es de **8 a 12 minutos** para aplicaciones medianas
(hasta 200 endpoints) y de **3 a 5 minutos** para repositorios de hasta 500 MB.

---

## PÁGINA 2 — PLANES, PRECIOS, FAQ Y SLA

### 2.1 Planes de suscripción

| Característica | **Free** | **Pro** | **Enterprise** |
|---|---|---|---|
| Precio mensual | US$ 0 | US$ 49 / mes | US$ 299 / mes |
| Escaneos web por mes | 5 | 100 | Ilimitados |
| Repositorios conectados | 1 | 10 | Ilimitados |
| Tamaño máximo por repositorio | 100 MB | 500 MB | 5 GB |
| Escaneos simultáneos | 1 | 3 | 10 |
| Detección SQLi y XSS | ✔ | ✔ | ✔ |
| Detección de secretos en código | ✖ | ✔ | ✔ |
| Reportes PDF/JSON | Solo PDF | PDF y JSON | PDF, JSON y API |
| Retención de reportes | 30 días | 12 meses | 24 meses |
| Usuarios por cuenta | 1 | 5 | Ilimitados |
| Soporte | Comunidad (foro) | Correo (24 h hábiles) | Prioritario 24/7 + gerente de cuenta |
| API de integración CI/CD | ✖ | ✔ (1.000 llamadas/mes) | ✔ (ilimitada) |

- El plan **Pro anual** tiene un descuento del **20 %** (US$ 470/año).
- El plan **Enterprise** incluye despliegue opcional en región dedicada y firma de **DPA**
  (Acuerdo de Procesamiento de Datos) personalizado.
- Los escaneos no utilizados **no se acumulan** para el mes siguiente.

### 2.2 Preguntas Frecuentes (FAQ)

**¿Puedo cambiar de plan en cualquier momento?**
Sí. Las mejoras (upgrade) se aplican de inmediato con cobro prorrateado. Las bajas (downgrade)
se aplican al inicio del siguiente ciclo de facturación.

**¿Qué pasa si supero mi límite de escaneos?**
El escaneo adicional queda bloqueado y se ofrece la compra de paquetes extra: 10 escaneos
adicionales por US$ 9 (solo planes Pro y Enterprise).

**¿DevShield modifica mi código o mi aplicación?**
No. Todos los análisis son de solo lectura. Las pruebas dinámicas (DAST) usan cargas útiles
seguras que no alteran datos de producción.

**¿Cómo restablezco mi contraseña?**
Desde la pantalla de inicio de sesión, opción "Olvidé mi contraseña". El enlace de
restablecimiento expira en **30 minutos**.

**¿Ofrecen periodo de prueba del plan Pro?**
Sí, **14 días de prueba gratuita** sin tarjeta de crédito. Al finalizar, la cuenta pasa
automáticamente al plan Free si no se ingresa un método de pago.

### 2.3 Acuerdos de Nivel de Servicio (SLA)

- **Disponibilidad garantizada:** 99,5 % mensual (Free y Pro) y **99,9 % mensual (Enterprise)**.
- **Compensación por incumplimiento (solo planes de pago):** si la disponibilidad mensual cae
  por debajo de lo garantizado, el cliente recibe créditos de servicio:
  - Entre 99,0 % y el objetivo: **10 %** de crédito sobre la factura mensual.
  - Entre 95,0 % y 98,99 %: **25 %** de crédito.
  - Menor a 95,0 %: **50 %** de crédito.
- Los créditos deben solicitarse dentro de los **30 días** posteriores al incidente escribiendo
  a `sla@devshield.io`.
- **Tiempos de primera respuesta de soporte:** Free: sin garantía (foro comunitario).
  Pro: 24 horas hábiles. Enterprise: **1 hora** para incidentes críticos (P1), 4 horas para P2.
- El mantenimiento programado se anuncia con **72 horas** de antelación y no computa como downtime.

---

## PÁGINA 3 — TÉRMINOS DE USO Y POLÍTICA DE PRIVACIDAD

### 3.1 Términos de uso (resumen vinculante)

1. **Autorización obligatoria:** el usuario solo puede escanear aplicaciones, dominios y
   repositorios **de su propiedad o sobre los que posea autorización expresa y por escrito**.
   Queda **estrictamente prohibido** utilizar DevShield para escanear activos de terceros sin
   consentimiento. La verificación de propiedad (DNS TXT o archivo en el servidor) es un
   requisito técnico previo a todo escaneo web.
2. **Sanciones por uso indebido:** el primer intento de escaneo no autorizado genera la
   **suspensión inmediata de la cuenta por 30 días**; la reincidencia implica el **cierre
   definitivo de la cuenta sin reembolso** y, cuando la ley lo exija, la notificación a las
   autoridades competentes.
3. **Uso aceptable:** está prohibido revender el servicio, realizar ingeniería inversa de la
   plataforma, o usar los reportes para atacar sistemas de terceros.
4. **Responsabilidad:** DevShield es una herramienta de apoyo; no garantiza la detección del
   100 % de las vulnerabilidades existentes. La responsabilidad total de DevShield se limita
   al monto pagado por el cliente en los **12 meses** anteriores al reclamo.
5. **Cancelación:** el usuario puede cancelar en cualquier momento desde el panel. No se
   emiten reembolsos por periodos parciales, salvo lo dispuesto en el SLA.

### 3.2 Política de privacidad y manejo del código fuente

- **Propiedad del código:** el código fuente del cliente es y seguirá siendo **propiedad
  exclusiva del cliente**. DevShield no adquiere ningún derecho sobre él.
- **Procesamiento efímero:** el código clonado para un escaneo vive únicamente dentro del
  contenedor Docker aislado y **se elimina de forma irreversible al terminar el análisis**
  (máximo 60 minutos después). DevShield **nunca almacena copias permanentes** del código
  fuente; solo persisten los reportes de hallazgos.
- **Confidencialidad:** los empleados de DevShield no acceden al código del cliente, salvo
  solicitud expresa de soporte autorizada por escrito por el propio cliente, y siempre bajo
  acuerdo de confidencialidad (NDA).
- **Datos personales:** se recopilan únicamente nombre, correo electrónico y datos de
  facturación. Nunca se venden datos a terceros. El procesamiento cumple con **GDPR** (UE)
  y **LGPD** (Brasil). Los datos de facturación son procesados por un proveedor de pagos
  certificado **PCI-DSS**; DevShield no almacena números de tarjeta.
- **Derechos del usuario:** acceso, rectificación y supresión escribiendo a
  `privacy@devshield.io`. Las solicitudes se resuelven en un máximo de **15 días hábiles**.
- **Eliminación de cuenta:** al eliminar la cuenta, todos los reportes y datos personales se
  borran definitivamente en un plazo de **30 días**, salvo obligación legal de retención de
  datos de facturación (5 años).

---

*© 2026 DevShield Inc. — Documento ficticio creado con fines educativos para el proyecto
de Agente Inteligente RAG.*
