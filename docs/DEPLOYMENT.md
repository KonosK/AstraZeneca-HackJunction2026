# Private HTTPS demo deployment

No external service was deployed, charged, pushed or published. The repository provides a single container serving the built frontend, the original Python model API and optional server-side voice. Use a private, synthetic-data demonstration, not a patient production service.

## Normal Docker host

```bash
docker build -t thriver-care:demo .
# Create a private env file or equivalent hosting secret bindings first:
docker run --rm --env-file /secure/path/thriver-demo.env \
  -p 127.0.0.1:8001:8001 thriver-care:demo
```

Required production settings:

- `DEMO_ACCESS_TOKEN`: strong secret password. Browser username is `demo`. The production gate rejects access if this is missing. Enter the password through secure host settings, never a committed file.
- `APP_ORIGINS=https://your-actual-demo-host`: exact browser origin, no trailing slash. `COOKIE_SECURE=true` is the image default. HTTPS is required for microphone access outside loopback.
- Optional `ELEVENLABS_API_KEY`: actual secret API key; optional `ELEVENLABS_VOICE_ID`. No key enables the full text workflow.

Choose an owner-authorized container host with at least 1 GiB memory initially; verify actual memory use under your load. Use one Uvicorn process for the demo and avoid loading one model per worker unnecessarily. Configure TLS on that host or a reverse proxy, route all paths to container port 8001 and preserve same-origin `/api` routing. Do not add a public standalone frontend pointing at an unprotected model service.

After deployment, authenticate in a fresh browser, open each deep link and verify the county list, a real Lapland regional analysis, the synthetic patient analysis, local review and reset. Test the microphone through HTTPS and confirm that no key appears in network responses or frontend assets. Check provider credits and privacy controls before optional voice calls.

This gate and per-process rate limiter suit a private demo. A real service needs reviewed identity/access control, persistent audit design, distributed quota controls, data processing approvals and clinical validation. No real patient data is authorized here.

## Managed-cloud Docker trust

The unmodified Docker build initially failed because inner containers did not trust the session proxy CA. Verification succeeded using a temporary Dockerfile with BuildKit CA secrets, keeping TLS and npm integrity checks enabled and keeping the CA out of image layers:

```python
# From repository root, create a temporary build file, not a source modification.
from pathlib import Path
s = Path('Dockerfile').read_text()
s = s.replace('RUN npm ci --no-audit --no-fund',
 'RUN --mount=type=secret,id=proxy_ca,required=true NODE_EXTRA_CA_CERTS=/run/secrets/proxy_ca npm ci --strict-ssl=true --no-audit --no-fund')
s = s.replace('RUN pip install --no-cache-dir -r requirements.txt',
 'RUN --mount=type=secret,id=proxy_ca,required=true PIP_CERT=/run/secrets/proxy_ca pip install --no-cache-dir -r requirements.txt')
Path('/tmp/thriver-Dockerfile.cloud').write_text(s)
```

```bash
docker build -f /tmp/thriver-Dockerfile.cloud \
 --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt \
 -t thriver-care:demo .
```

Use the managed Docker socket and proxy configuration already supplied by the environment. Do not disable certificate verification. Runtime provider calls inside a proxy-controlled container may also require a read-only CA mount with `SSL_CERT_FILE` pointing at the mounted combined trust bundle; do not bake a session CA or credentials into the image.
