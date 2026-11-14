# Vercel — preparado, pendiente de publicar

La entrega incorpora `app.py`, `vercel.json`, `.python-version`, `pyproject.toml` y `uv.lock` para servir FastAPI y el frontend desde el mismo proyecto. Se conserva el modelo original. El constructor de Python puede optimizar dependencias grandes mediante el lock; el build y el arranque reales deben verificarse en la cuenta Vercel.

El usuario ha pedido terminar primero el push/ZIP y dejar el despliegue para el siguiente paso. No hay una URL publicada confirmada.

Al continuar: conecta el repositorio y la rama **codex/thriver-demo-delivery**, con raíz del proyecto **./** y framework **FastAPI**. Conserva el comando de build de `vercel.json`; deja la instalación Python gestionada por Vercel/uv. Configura **DEMO_ACCESS_TOKEN** como contraseña privada de la demo (usuario `demo`). La clave de ElevenLabs es opcional y solo se introduce como secreto del servidor. No introduzcas secretos en GitHub, frontend ni chat.

El entorno reconoce los dominios automáticos de Vercel para las peticiones de voz del mismo origen. Para un dominio propio, configura APP_ORIGINS con su origen HTTPS exacto. La clave y los créditos deben comprobarse con una llamada sintética real antes de afirmar que la voz funciona.

Después de publicar, verifica las cuatro rutas, el mapa, las dos llamadas de análisis, el flujo completo, la contraseña de acceso, la versión móvil y los errores de voz. Una prueba local o un push a GitHub no equivalen a una publicación externa.
