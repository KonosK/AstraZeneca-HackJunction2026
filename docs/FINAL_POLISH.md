# Cambios finales de la demo

Aplicados a partir de la grabación del usuario del 14 de noviembre de 2026:

- Reproducción continua y contador de días fluido. Sin SILTA llega al día 78 sin clics intermedios. Con SILTA se pausa en el cuestionario del paciente (día 3) y la revisión médica (día 7); tras aceptar continúa hasta el día 32. Son días de un escenario, no un beneficio clínico medido.
- Un único control de reproducción/pausa, más Reset. En los puntos de espera se muestra la acción que corresponde a paciente o médico, sin un botón de avance deshabilitado redundante.
- Interfaz más compacta: títulos reducidos, encabezados de marketing eliminados, aclaraciones repetidas agrupadas en un desplegable About this demo y estado técnico inferior solo accesible para lector de pantalla.
- Paciente: Fill demo check-in, respuesta editable y un solo Confirm & send check-in. Esa acción confirma los campos, valida conflictos, llama al motor y crea la entrada local de revisión. No hay confirmaciones de preview, payload, análisis, borrador y envío por separado. El contexto adicional sigue disponible en grupos cerrados.
- Médico: índice regional generado por el modelo y contribuyentes SHAP primero, claramente identificados como datos regionales, no riesgo individual ni causas. Propuestas del motor con casillas, detalles de acción/responsable/métrica, y un solo Accept selected & continue. Se conservan rechazar, pedir información y editar la nota.
- Las propuestas aceptadas quedan registradas en la auditoría local. Cambiar el intake invalida el resultado anterior y la aprobación. No se crean órdenes ni derivaciones externas.
- Stop narration aparece solo mientras hay audio reproduciéndose. Los controles de voz tienen estados de espera/error y mantienen texto y preset como alternativa.
- Verify provider access hace una comprobación de cuenta sin generar audio. Detecta un key ID rechazado, muestra cómo reemplazarlo por una secret key y no devuelve ni almacena la clave. La credencial disponible sigue rechazada: no se afirma STT/TTS real satisfactorio.
- El proyecto conserva un coordinador determinista: extracción FHIR limitada, procedencia, conflictos, preguntas pendientes, validación y reglas de revisión. No es un agente autónomo con LLM. La decisión clínica y la selección de propuestas pertenecen al profesional.
- Se prepara Vercel con un entry point FastAPI, build del frontend, Python 3.12, lock de dependencias y configuración del mismo origen. Publicar una web requiere autorización de la cuenta Vercel; subir a GitHub por sí solo no publica la aplicación.
