# Runbook — Desarrollo local (CASE)

**Estado:** operativo para entorno local (Nivel A, con reservas).  
**Alcance:** ejecución local reproducible sin depender de servicios externos/live.

## Prerrequisitos
- Python 3.11+
- Dependencias: `pip install -e ".[dev]"` (desde raíz del repo)

## Configuración
- Copiar `.env.example` a `.env` (no commitear `.env`).
- Para suite determinista local: `CASE_PROVIDER=mock`, `CASE_SECURITY_MODE=dev`.
- `dev` sin credenciales: acceso abierto permitido por diseño para desarrollo local. No usar como configuración pública.

## Ejecución
- API: `uvicorn case_api.api.v1.app:app --reload --host 0.0.0.0 --port 8000`
- UI: `streamlit run streamlit_app/app.py`
- Docs: `http://localhost:8000/docs`

## Quality gates (deterministas, sin live)
- `ruff check src tests`
- `mypy src --ignore-missing-imports`
- `pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py`

> Nota: `.env` local puede definir proveedores/credenciales; `tests/conftest.py` fuerza `CASE_PROVIDER=mock` en corridas no marcadas como `live`. Tests live (`pytest -m live` / archivos `test_groq_live.py`, integraciones externas) son opt-in y requieren servicios/keys.

## Packaging (verificación local)
- `python -m build --wheel`
- Inspección: `python -m zipfile -l dist/case-*.whl`
- Smoke en venv limpio: instalar wheel e importar `case_core`, `case_api`, `case_infra`, `logistics_adapter`, `usgs_adapter`.

## Limitaciones conocidas
- SQLite (single-process/concurrencia limitada), sin garantías de aislamiento compartido multi-consumidor.
- Integraciones externas (Groq/Ollama/Cloud/USGS) no deterministas; no ejercitarlas sin autorización/configuración.