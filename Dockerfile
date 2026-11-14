FROM node:24-bookworm-slim AS frontend
WORKDIR /app/regionDashboard
COPY regionDashboard/package.json regionDashboard/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY regionDashboard/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_ENV=production COOKIE_SECURE=true
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY mlBackend/ ./mlBackend/
COPY server/ ./server/
COPY --from=frontend /app/regionDashboard/dist ./regionDashboard/dist
RUN useradd --create-home --uid 10001 demo && chmod -R a+rX /app
USER demo
EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s CMD python -c "import urllib.request,os; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8001')+'/healthz',timeout=8)"
CMD ["sh", "-c", "exec python -m uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-8001}"]
