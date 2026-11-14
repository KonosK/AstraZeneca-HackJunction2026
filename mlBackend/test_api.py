"""Quick TestClient verification for OncoFlow API endpoints.

Run from repo root:
    python -m mlBackend.test_api
Or from mlBackend/:
    python test_api.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

try:
    from mlBackend.api import FIVE_BLOCK_KEYS, app
except ModuleNotFoundError:
    # Allow `python test_api.py` when cwd is mlBackend/
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from api import FIVE_BLOCK_KEYS, app


def _assert_five_blocks(payload: dict, label: str) -> None:
    missing = [k for k in FIVE_BLOCK_KEYS if k not in payload]
    assert not missing, f"{label} missing blocks: {missing}"


def main() -> int:
    client = TestClient(app)
    failures: list[str] = []

    # GET /regions
    r = client.get("/regions")
    if r.status_code != 200:
        failures.append(f"GET /regions -> {r.status_code}: {r.text}")
    else:
        try:
            data = r.json()
            json.dumps(data, allow_nan=False)
            assert data.get("count") == 23, f"expected 23 regions, got {data.get('count')}"
            assert len(data.get("regions", [])) == 23
            print("OK  GET /regions  count=23  JSON allow_nan=False")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"GET /regions JSON/assert: {exc}")

    # POST /analyze/region (Lapland)
    region_body = {"region_name": "Lapland"}
    r = client.post("/analyze/region", json=region_body)
    if r.status_code != 200:
        failures.append(f"POST /analyze/region -> {r.status_code}: {r.text}")
    else:
        try:
            data = r.json()
            json.dumps(data, allow_nan=False)
            _assert_five_blocks(data, "analyze/region")
            name = data["predictions_and_gaps"].get("region_name", "")
            assert "Lapland" in name, name
            assert "what_if" not in data["predictions_and_gaps"]
            assert "shap_drivers_what_if" not in data["contributing_factors"]
            print(
                f"OK  POST /analyze/region  region={name!r}  "
                f"pred={data['predictions_and_gaps'].get('predicted_cancer_index_age_std')}"
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"POST /analyze/region JSON/assert: {exc}")

    # POST /analyze/patient — full Tier A + Tier B (Lapland-style)
    patient_body = {
        "patient_id": "demo-001",
        "region_name": "Lapland",
        "age": 78,
        "public_care_track": True,
        "symptom_severity_score": 7,
        "g8_frailty_score": 12,
        "missing_staging_fields": ["T", "N", "M"],
        "sex": "male",
        "symptom_onset_days": 60,
        "primary_symptom_cluster": "respiratory",
        "smoking_status": "former",
        "lives_alone": True,
        "travel_time_to_care_minutes": 95,
        "needs_interpreter": False,
        "education_band": "low",
        "already_referred_to_specialist": False,
        "care_phase": "primary_care",
        "language": "fi",
        "comorbidity_flags": ["copd"],
        "agent_confidence": 0.82,
    }
    r = client.post("/analyze/patient", json=patient_body)
    if r.status_code != 200:
        failures.append(f"POST /analyze/patient -> {r.status_code}: {r.text}")
    else:
        try:
            data = r.json()
            json.dumps(data, allow_nan=False)
            _assert_five_blocks(data, "analyze/patient")
            assert data["predictions_and_gaps"].get("patient_id") == "demo-001"
            assert "pathway_days_estimate" in data["predictions_and_gaps"]
            intake = data["predictions_and_gaps"].get("intake") or {}
            assert intake.get("sex") == "male"
            assert intake.get("primary_symptom_cluster") == "respiratory"
            assert intake.get("smoking_status") == "former"
            assert intake.get("education_band") == "low"
            assert intake.get("travel_time_to_care_minutes") == 95
            assert "blind_spots" in data["predictions_and_gaps"]
            assert isinstance(data["predictions_and_gaps"]["blind_spots"], list)
            assert "blind_spots" in data["contributing_factors"]
            flags = data["contributing_factors"].get("intake_risk_flags") or {}
            assert flags.get("lives_alone") is True
            assert flags.get("smoking_risk") is True
            assert flags.get("high_travel") is True
            # Male intake should not surface cervical screening macro tips.
            macros = data["recommended_interventions"].get("department_macro") or []
            for macro in macros:
                feature = str(macro.get("driver_feature") or "")
                assert "cervical" not in feature.casefold(), feature
            print(
                "OK  POST /analyze/patient  "
                f"pathway_total="
                f"{data['predictions_and_gaps']['pathway_days_estimate'].get('total_days')}  "
                f"blind_spots={data['predictions_and_gaps']['blind_spots']}"
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"POST /analyze/patient JSON/assert: {exc}")

    # Backward compatibility: minimal Tier A-only payload still returns 200
    minimal_body = {
        "patient_id": "demo-minimal",
        "region_name": "Lapland",
        "age": 65,
        "symptom_severity_score": 5,
    }
    r = client.post("/analyze/patient", json=minimal_body)
    if r.status_code != 200:
        failures.append(f"POST /analyze/patient (Tier A only) -> {r.status_code}: {r.text}")
    else:
        try:
            data = r.json()
            json.dumps(data, allow_nan=False)
            _assert_five_blocks(data, "analyze/patient minimal")
            intake = data["predictions_and_gaps"].get("intake") or {}
            assert intake.get("sex") == "unknown"
            assert intake.get("care_phase") == "primary_care"
            assert "blind_spots" in data["predictions_and_gaps"]
            print("OK  POST /analyze/patient (Tier A only)  status=200")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"POST /analyze/patient minimal JSON/assert: {exc}")

    # Health smoke
    r = client.get("/health")
    if r.status_code != 200:
        failures.append(f"GET /health -> {r.status_code}")
    else:
        json.dumps(r.json(), allow_nan=False)
        print("OK  GET /health")

    if failures:
        print("\nFAILED:")
        for item in failures:
            print(" -", item)
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
