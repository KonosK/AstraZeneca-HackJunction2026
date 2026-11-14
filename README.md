# Iniciar el proyecto

Windows · PowerShell. Instala **Python 3.12** y **Node.js 24**. Desde la carpeta del proyecto:

```powershell
py -3.12 -m venv "$env:USERPROFILE\tcenv"
& "$env:USERPROFILE\tcenv\Scripts\python.exe" -m pip install -r requirements.txt
npm.cmd --prefix regionDashboard ci --include=dev
npm.cmd --prefix regionDashboard run build
& "$env:USERPROFILE\tcenv\Scripts\python.exe" -m uvicorn server.app:app --host 127.0.0.1 --port 8001
```

Abre **http://127.0.0.1:8001**. Mantén PowerShell abierto; **Ctrl+C** para detenerlo.
