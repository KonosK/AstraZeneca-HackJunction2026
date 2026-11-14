# Demo de dos minutos

## Arranque

Sigue el README desde la raíz. En Windows usa el entorno Python corto (`%USERPROFILE%\tcenv`). Para el servidor compilado abre el puerto 8001; para desarrollo con Vite usa los comandos de `docs/WINDOWS.md`.

## Recorrido

**0–20 s · Simulation.** Selecciona Lapland y pulsa Start simulation en Without SILTA. La historia avanza sola al día 78; Pause detiene realmente el contador. Los días son ilustrativos. Selecciona With SILTA y Start simulation: se detiene en el día 3 para la interacción del paciente.

**20–50 s · Patient.** Pulsa Open Patient questionnaire y Fill demo check-in. Muestra la respuesta editable; el historial y las opciones permanecen cerrados. Puedes grabar una respuesta corta si ElevenLabs está configurado y autorizado, o usar el texto sintético. Pulsa **Confirm & send check-in** una sola vez: aprueba el registro, ejecuta el análisis real y envía la propuesta al inbox local simulado. No se envía nada a una historia clínica real.

**50–85 s · Doctor.** Pulsa Continue simulation: el reloj llega al día 7 y se detiene. Abre Doctor. Primero muestra el índice **regional** del modelo y sus contribuyentes, sin llamarlos riesgo del paciente ni causas. Marca una o dos propuestas revisables. Cada propuesta permite consultar acción, responsable, justificación y métrica. Pulsa **Accept selected & continue**: registra la selección local y vuelve a la simulación sin otra confirmación.

**85–100 s · Simulation.** El recorrido continúa solo hasta el día 32, pasando por planificación del trabajo diagnóstico, seguimiento del equipo y siguiente cita en el escenario. No se ha reservado ni ejecutado ninguna cita real; los 46 días de diferencia no son un beneficio medido o una predicción del modelo.

**100–120 s · Dashboard.** Abre Dashboard: conserva Lapland. Señala el indicador observado de espera en atención primaria, su año y las limitaciones de procedencia. La evidencia y la acción regional están junto al mapa. Destaca responsable y métrica de una propuesta real del motor. Termina con cómo un piloto autorizado mediría si mejora la coordinación, sin afirmar eficacia clínica.

## Pruebas alternativas

- Rechazar o pedir más información mantiene la vía con SILTA detenida. El paciente ve el estado y puede editar su check-in.
- Cambiar un dato invalida análisis, envío y aprobación anteriores. Un conflicto requiere elegir explícitamente la respuesta nueva o la registrada.
- Verify provider access comprueba acceso a la cuenta sin producir audio. Un key ID no es la secret key. El estado de la clave de cloud no confirma la configuración del ordenador del usuario.
- Si falla el backend, el error es visible. El replay grabado requiere elección explícita y mantiene DEMO FIXTURE — NOT LIVE MODEL RESPONSE en pantalla. Solo admite el preset exacto de Lapland.
- Reset borra el caso, el resultado, la selección y la revisión locales. La navegación conserva el estado; recargar lo reinicia.

## Evidencia y alcance

El motor original OncoFlow se conserva y es el que produce el análisis; SILTA es la experiencia de coordinación. El coordinador usa reglas deterministas, no un LLM autónomo que interprete documentos arbitrarios. No existe una regla clínicamente validada para decidir que una persona puede evitar atención médica. Los límites completos están en About this demo, los desplegables de evidencia y `docs/clinical-limitations.md`.
