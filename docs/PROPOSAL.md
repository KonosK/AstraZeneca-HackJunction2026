# Thriver Care / SILTA — propuesta de entrega

**Conectar el contexto regional, la voz del paciente y una acción que un profesional pueda revisar.**

Las barreras prácticas pueden quedar fuera de una derivación: una respuesta pendiente, un desplazamiento difícil o información fragmentada. Nuestra propuesta organiza ese contexto sin convertir un índice de incidencia regional en un diagnóstico individual.

La demo mantiene cuatro perspectivas. En **Simulación** se compara el mismo caso ficticio sin SILTA y con SILTA; cada evento se detiene para explicar la siguiente acción. En **Paciente**, una extensión dentro de un portal reconstruido recoge un check-in por texto o voz opcional, permite corregirlo y exige confirmación. En **Médico**, el profesional recibe datos con su procedencia, información desconocida y una propuesta real de OncoFlow; puede aceptar, editar la nota, rechazar o pedir contexto. En **Dashboard**, el mismo condado conecta indicadores observados con una intervención, un responsable y una métrica de seguimiento.

El flujo por texto está implementado y probado de extremo a extremo. El backend, su modelo y el dataset originales se conservan. No se envían derivaciones ni se escribe en Maisa, Apotti o Kanta. El paciente recibe únicamente el estado local de la revisión y una fecha de check-in ilustrativa.

Para Lapland, el dataset suministrado informa un 39,5% de esperas de atención primaria superiores a siete días en 2024. Es una posible barrera de acceso que merece investigar; no prueba una desigualdad en resultados oncológicos. Las recomendaciones regionales y sus responsables proceden de la respuesta real de OncoFlow. La evolución futura se podría evaluar con completitud del traspaso de información, tiempo hasta revisión y seguimiento completado, siempre mediante un piloto autorizado y datos adecuados.

El recorrido ficticio de 78 frente a 32 días ayuda a mostrar la coordinación. No representa un beneficio medido, una predicción del modelo ni un tratamiento que se haya adelantado realmente. El R² de validación regional es negativo y las estimaciones de días son heurísticas. La correspondencia exacta con el indicador oficial del Objetivo 3 requiere verificación de dominio: el acceso al documento nacional está bloqueado en este entorno.

ElevenLabs está integrado mediante su SDK oficial y el circuito de grabación y confirmación está probado con audio sintético y respuestas de prueba. La credencial actual es rechazada por el proveedor como identificador de clave; una prueba STT/TTS real satisfactoria queda pendiente de sustituirla de forma segura. La demostración por texto no depende de ello.

**Siguiente paso propuesto:** validar la selección del indicador y las reglas con responsables clínicos y regionales, completar la trazabilidad de las fuentes y ensayar un piloto de coordinación con métricas de proceso. No se afirma eficacia clínica ni despliegue público.
