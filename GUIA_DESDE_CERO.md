# De cero hasta pulsar Enviar en Codex — Thriver Care

**No publiques este paquete como repo nuevo.** Es una superposición de archivos para el REPOSITORIO ORIGINAL DE TU COMPAÑERO.

## 0. Qué necesitas
- Cuenta GitHub y acceso **Write** al repositorio original. Tu compañero puede invitarte en GitHub > repo > Settings > Collaborators (o Manage access) > Add people. Abre y acepta la invitación.
- Instala GitHub Desktop desde https://desktop.github.com/ e inicia sesión con la misma cuenta de GitHub.
- Archivos: este paquete; logo PNG/SVG original; captura de la burbuja; código de dashboard exportado por tu compañero (si realmente existe). **No necesitas Gemini ni ElevenLabs, API keys, tarjetas, hosting ni terminal para preparar Codex.**

## 1. Descargar el repo correcto (NO usar ZIP viejo)
1. Abre el repositorio original de tu compañero en GitHub, iniciado sesión. Verifica que ves `mlBackend/` con `api.py` y `API_CONTRACT.md`.
2. Abre GitHub Desktop > `File` > `Clone repository…` > pestaña GitHub.com. Selecciona el repositorio de tu compañero > `Clone`. Si no aparece: acepta invitación, y comprueba que Desktop usa la misma cuenta. Alternativa: pestaña URL, pega URL HTTPS del repo.
3. En GitHub Desktop, menú `Branch` > `New branch…` > escribe `codex/thriver-final` > `Create branch`. Base desde la rama estable de tu compañero (habitualmente main). **No modifiques main**.
4. `Repository` > `Show in Explorer` para abrir carpeta REAL del repo en Windows.

## 2. Copiar documentación y assets
1. Descarga y extrae `THRIVER_PARA_REPO_COMPANERO.zip` en Descargas.
2. Abre la carpeta extraída y selecciona `AGENTS.md`, `docs/`, `assets/`, `.env.example`, `.gitignore`, `PROMPT_UNICO_CODEX.txt`, `DASHBOARD_CODIGO_AQUI.txt`. Copia y pega TODO directamente dentro de la carpeta del repositorio abierto en el Explorador (junto a `mlBackend`, **NO dentro de mlBackend**).
3. Si Windows pregunta sobre combinar `docs`/`assets`, permite combinar. Si algún archivo existente tiene el mismo nombre, **no sobrescribas sin revisar**, especialmente `.gitignore` y `AGENTS.md`: fusiona el contenido o pide ayuda para evitar borrar reglas previas.
4. Logo: localiza el PNG original (si lo tienes en Telegram/WhatsApp/Figma, usa el archivo original o expórtalo a PNG transparente), renómbralo `thriver-logo.png` y cópialo en `assets/brand/`. Si es SVG original, usa `thriver-logo.svg`. **No copies una imagen generada si no es el logo final.**
5. Burbuja: guarda la captura de la referencia flotante como `floating-bubble-reference.png` dentro de `assets/references/`. Opcional: capturas reales de Maisa, no collages IA, también en esa carpeta.
6. Dashboard: si te pasan un ZIP con el código, clic derecho > Extraer todo; busca el directorio donde están `package.json`, `src` o `app`, `public`. Crea en la raíz del repo una carpeta `dashboard-source` y pega ahí esos archivos. No incluyas `node_modules`, `.next`, `dist`, `.env`, otras claves o `.git`. Si el dashboard ya forma parte del repositorio, no lo dupliques.
7. Comprueba en la carpeta del repo que ves `mlBackend`, `docs`, `AGENTS.md`, `PROMPT_UNICO_CODEX.txt`; si has conseguido recursos, también `assets/brand/thriver-logo.png` y `assets/references/floating-bubble-reference.png`, y `dashboard-source`.

## 3. Subir lo preparado, sin terminal
1. Vuelve a GitHub Desktop > `Changes`. Revisa la lista: documentos y assets sí; **ningún `.env` con claves, `node_modules` o miles de ficheros construidos**.
2. Abajo a la izquierda, escribe resumen `Add Thriver specs, original assets and dashboard source`.
3. Pulsa `Commit to codex/thriver-final`.
4. Pulsa `Publish branch` o `Push origin` arriba (dependiendo de lo que aparezca).
5. Abre GitHub en el navegador, cambia a rama `codex/thriver-final` y verifica que están `docs/01_DESIGN.md`, `docs/02_INTEGRATION.md` y tu dashboard. Si el ZIP del dashboard no te llegó, te conviene conseguirlo ANTES de lanzar Codex para que no tenga que rehacerlo.

## 4. Configurar Codex Cloud UNA SOLA VEZ
1. Abre https://chatgpt.com/codex e inicia sesión con tu cuenta de ChatGPT.
2. Si pregunta por GitHub, conecta la misma cuenta que tiene acceso al repo del compañero; autoriza específicamente ese repositorio si la autorización permite elegir repos.
3. Selecciona `Cloud` / `Work in Cloud`; crea un entorno (`Create environment`) y selecciona **el repositorio original de tu compañero**, no el ZIP ni un repo nuevo. **Elige la rama `codex/thriver-final`** como base de trabajo, cuando se te permita. Si la interfaz no permite elegirla en el entorno, selecciónala al iniciar la tarea.
4. Durante el setup, deja las opciones por defecto primero; el prompt pide a Codex detectar dependencias. **No añadas secretos** porque no tienes claves Google ni ElevenLabs. Habilita acceso a Internet solo a las fuentes legítimas necesarias para instalar dependencias y consultar documentación, si el entorno ofrece ese ajuste; usa el mínimo necesario.
5. Publica el entorno (`Publish`). Eso publica la *configuración del entorno Codex*, no tu web en Internet.
6. Comprueba que la tarea nueva está sobre `codex/thriver-final` y el repositorio correcto. Abre `PROMPT_UNICO_CODEX.txt`, copia TODO su contenido (Ctrl+A, Ctrl+C) y pégalo en Codex. **Una sola tarea; un solo mensaje inicial.** Pulsa Enviar.

## 5. Cuando Codex acabe
1. Lee `docs/FINAL_REPORT.md` y `docs/DEMO_RUNBOOK.md` del resultado, y comprueba si dice que Python API, frontend build y cuatro rutas han pasado pruebas de verdad. No des por terminado algo marcado como `unverified`.
2. Revisa los cambios/diff. Si Codex ofrece `Create PR` o `Push`, envíalos a la rama o abre un Pull Request hacia la rama acordada. **No merges a main sin hablarlo con tu compañero.**
3. Para ver la web localmente, sigue exactamente los comandos generados en su README/DEMO_RUNBOOK; los comandos dependen del frontend real y de si el backend es accesible. Si Codex ofrece vista previa funcional, pruébala.
4. **Despliegue público no es automático.** Para obtener una URL, necesitarás una cuenta de hosting y autorizar el despliegue. El backend Python con `.joblib` requiere hosting adecuado; solo frontend en Vercel no garantiza backend operativo. Sigue el procedimiento concreto escrito por Codex y verifica URL pública en incógnito.
5. Haz el recorrido completo de dos minutos: región y dato con fuente; caso FHIR sintético; preguntas/corrección; análisis real OncoFlow; aprobación humana simulada; recomendación local y métrica. Prueba también la alternativa de demo sin backend si existe, claramente marcada como fixture.

## Si no tienes logo o burbuja
Puedes mandar el prompt sin ellos, pero no obtendrás exactitud visual. Preferible añadir los dos archivos ANTES de pulsar Enviar. No necesitas cambiar el prompt.

## Si tienes problemas
- No aparece el repo en Desktop: confirma invitación, cuenta y permisos.
- No aparece en Codex: autoriza la app de Codex para acceder a ese repo; comprueba cuenta y workspace.
- No ves la rama: pulsa `Push origin` desde Desktop, recarga Codex.
- Falla la instalación: deja que la única tarea Codex lo diagnostique; no inventes versiones de bibliotecas.
- Solicita claves Gemini/ElevenLabs: indícale que el prompt explícitamente exige funcionar sin ellas; la arquitectura opcional puede esperar.
