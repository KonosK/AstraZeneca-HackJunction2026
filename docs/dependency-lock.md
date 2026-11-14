# Tested dependency environment

Onboarding restored Python 3.12.14, Node 24.22.1, npm 11.9.0. `requirements.txt` records exact Python versions tested during implementation; the npm lockfile preserves existing dependency versions with only the self-hosted Archivo font added. Docker uses Python 3.12 bookworm and Node 24 bookworm; its resolved image checksums were preserved by the local build engine.

| Runtime dependency | Tested version |
| --- | --- |
| scikit-learn | 1.9.1 |
| pandas | 3.1.1 |
| numpy | 2.5.4 |
| SHAP | 0.54.1 |
| joblib | 1.6.0 |
| FastAPI | 0.163.0 |
| Pydantic | 2.14.3 |
| Uvicorn | 0.54.0 |
| ElevenLabs official SDK | 2.78.0 |
| React | 19.3.1 |
| TypeScript | 7.0.2 |
| Vite | 8.3.8 |
| Playwright (test-only) | 1.65.2 |

The supplied model artifact embeds scikit-learn 1.9.1. It loaded with this environment without compatibility patches or retraining. The existing suite and live requests succeeded. TestClient emits a Starlette/httpx deprecation warning; it does not prevent these tests. Lint has two existing warnings in the preserved, currently unused CountyInspector component.

SHA-256 before and after:

- Model `mlBackend/artifacts/oncoflow_bundle.joblib`: `e49b63f1dd035f94740722a4a8fa8e4d06b22dda0e4595db71a3ba52a6baef21`
- Dataset `mlBackend/data/clean_cancer_training_data.csv`: `90a6ef9760ca3a2d3b8e0f2afa513f58e56bf0a89bc1f2bc30fd849e93fc42c9`

No existing ML source, tests, artifact or CSV was modified. Package checksums and TLS verification remained enabled.
