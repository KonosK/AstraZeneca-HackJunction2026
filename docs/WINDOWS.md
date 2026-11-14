# Probar y configurar la demo en Windows (PowerShell, sin WSL)

## Arranque

El entorno Python debe estar en una ruta corta: algunos archivos del SDK de ElevenLabs exceden el límite de rutas de Windows cuando `.venv` está dentro de una carpeta larga en Descargas.

Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv "$env:USERPROFILE\tcenv"
& "$env:USERPROFILE\tcenv\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:USERPROFILE\tcenv\Scripts\python.exe" -m uvicorn server.app:app --host 127.0.0.1 --port 8001
```

Espera `Application startup complete`. En otra ventana de PowerShell, desde la misma carpeta del proyecto:

```powershell
cd regionDashboard
npm.cmd ci --include=dev
npm.cmd run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Abre la aplicación local del puerto 5173. Mantén ambas ventanas abiertas.

## ElevenLabs en tu ordenador

La configuración de secretos de Codex Cloud no se transfiere al ordenador local. Este servidor tampoco carga `.env` automáticamente.

1. En tu cuenta de ElevenLabs, crea o copia el **valor secreto completo** de una API key. El identificador de la clave es distinto del secreto; el proveedor rechazó el valor anterior con `api_key_id_used_as_api_key`.
2. Comprueba que la clave tiene permisos para Speech-to-Text y Text-to-Speech y que la cuenta dispone de créditos. Nunca pegues claves en el chat, en archivos del frontend ni en una variable `VITE_`.
3. En la ventana donde corre Python, pulsa Ctrl+C. Desde la carpeta raíz del proyecto ejecuta:

```powershell
$env:ELEVENLABS_API_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Clave secreta de ElevenLabs" -AsSecureString)).Password
& "$env:USERPROFILE\tcenv\Scripts\python.exe" -m uvicorn server.app:app --host 127.0.0.1 --port 8001
```

La entrada no muestra la clave ni incorpora su valor al historial del comando. Se proporciona al proceso Python mediante su entorno y dura en esa ventana; ciérrala para terminar la sesión. No hace falta activar `.venv`.

4. En Patient abre **Optional voice · ElevenLabs** y pulsa **Check voice setup**. Indica únicamente si el servidor detecta una clave. No valida permisos, saldo ni éxito del proveedor, y no realiza una llamada de pago.
5. Marca el consentimiento para audio sintético. Prueba **Listen to SILTA** o graba una frase corta con **Record voice answer**. Permite el micrófono, detén la grabación y revisa la transcripción. Una petición real al proveedor puede consumir créditos. La narración de este prototipo es en inglés.

Si falla, conserva el mensaje de error sin incluir secretos: clave ausente → volver a configurar/reiniciar Python; identificador rechazado → usar el secreto completo; autorización → revisar permisos; créditos/cuota → revisar cuenta; micrófono denegado → permitirlo en el navegador o usar texto.

## Recorrido rápido sin voz

En Patient pulsa **Fill demo check-in**, revisa la respuesta y el resumen, y pulsa **Confirm & send check-in** una sola vez. Los datos adicionales permanecen en grupos cerrados. La simulación se reanuda con **Continue simulation**, se detiene en la revisión médica y continúa sola después de **Accept selected & continue**. El médico marca las propuestas que quiere aceptar; no se solicita otra confirmación.

## Actualización de la interfaz

Detén ambos servicios con Ctrl+C. El ZIP `Thriver-Care-actualizacion.zip` contiene rutas relativas a la raíz del proyecto: extrae su contenido **dentro de tu carpeta `Thriver-Care`** y reemplaza los archivos de la aplicación. No contiene claves ni entornos Python. Esta actualización mantiene las mismas dependencias; reinicia Python y Vite con los comandos anteriores y recarga la página.
