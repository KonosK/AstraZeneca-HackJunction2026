# OncoFlow · Regional Dashboard

Isolated Vite + React + TypeScript UI for **regional** cancer-equity analytics (not patient triage). Talks only to the OncoFlow `mlBackend` API.

## Quick start

### 1. Backend (from repo root)

```powershell
cd mlBackend
& ..\.venv\Scripts\uvicorn.exe api:app --reload --host 127.0.0.1 --port 8000
```

Confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

### 2. Dashboard

```powershell
cd regionDashboard
npm install
npm run dev
```

Default Vite URL: `http://127.0.0.1:5173` (or the next free port).

API base URL (optional):

```env
# .env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Endpoints used

| Method | Path | Role in UI |
|--------|------|------------|
| `GET` | `/health` | Sidebar API status, KPI model MAE / best_model |
| `GET` | `/regions` | Map choropleth, county list, KPI aggregates (23 counties) |
| `POST` | `/analyze/region` | Selected-county inspector: prediction, SHAP, strategies |

**Not used:** `POST /analyze/patient`.

CORS is already open (`allow_origins=["*"]`) in `mlBackend`.

## Map join key

Choropleth uses Statistics Finland wellbeing-services county boundaries (bundled locally for offline-friendly demos):

- File: `public/finland-wellbeing-counties.geojson`
- Source layer: `tilastointialueet:hyvinvointialue4500k_2024` (EPSG:4326) via StatFi WFS
- **Join key:** `feature.properties.name` ↔ `GET /regions` → `region_name` (exact English name match for all 23 areas, including Helsinki and Åland)
- Rings are rewound to RFC7946 winding on load (StatFi ships clockwise exteriors)

Rendered with `react-simple-maps` + a Mercator projection fitted to the county GeoJSON.

Predicted cancer index is **not** fetched for all 23 counties on map load. Map overlays use validated indicators from `GET /regions`. Predictions appear in the inspector after a county is selected (`POST /analyze/region`).

## Evidence labeling (demo / judges)

| UI label | Meaning |
|----------|---------|
| **Validated THL / FCR** | Observed Sotkanet / Finnish Cancer Registry indicators (`observed_*`, map overlays from `/regions`) |
| **Projection / calibrated** | Model prediction and SHAP (`predicted_*`, `calibrated_projection`) |

The inspector surfaces `confidence_and_limitations.distinction` and evidence badges so validated facts are not confused with model projections.

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Dev server |
| `npm run build` | Typecheck + production build |
| `npm run preview` | Preview production build |
