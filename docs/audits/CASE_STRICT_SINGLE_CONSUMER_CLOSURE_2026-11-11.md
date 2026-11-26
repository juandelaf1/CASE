# CASE — Cierre Strict Single-Consumer: validación integral y auditoría final

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE` (local, working tree, sin commit/push)  
**Rama/HEAD:** `v4/portfolio-release @ b7021bb4316eec063633bbfdd99d1e0cb9164295` (`origin/v4/portfolio-release`, al día tras `git fetch origin`)  
**Prompt maestro preservado:** `docs/prompts/CASE_MASTER_EXECUTION_PROMPT_2026-11-10.md`  
**Informes previos (no sobrescritos):** `docs/audits/CASE_DEEP_AUDIT_AND_EVOLUTION_2026-11-10.md`, `docs/audits/CASE_FULL_EXECUTION_AND_FINAL_AUDIT_2026-11-11.md` (no creado previamente con ese nombre; este documento es el cierre solicitado).

## 1. Preservación y estado inicial (verificado)
- `git status -sb`/`git fetch origin` (sin `--prune`): rama alineada con remoto, sin commits locales adelantados. Working tree sucio preexistente + cambios de sesiones previas **preservados**. Sin operaciones destructivas, sin staging forzado, sin commit/push/merge/PR/deploy.

## 2. P0 — Smoke test del wheel (código de salida 1) — CAUSA DEMOSTRADA Y RESUELTA EN REPRODUCCIÓN

### 2.1 Síntoma comunicado
Instalación en venv limpio, imports OK, `/health` 200, `/domains` 200 (5 dominios), warning deprecación `httpx`/`TestClient`, proceso reportado como `Exited with code 1`.

### 2.2 Reproducción e investigación
- **Entorno wheel verificado:** wheel reconstruido (`python -m build --wheel`) e instalado en venv limpio temporal (`C:\Users\JUAN\AppData\Local\Temp\opencode\case-wheel-test`), `CASE_PROVIDER=mock`, `CASE_SECURITY_MODE=dev`, DB temporal.
- **Ejecución directa del proceso Python:** `SMOKE_OK` / `SMOKE_FULL_OK` con **`PY_EXIT=0` / `EXIT=0`** en ejecuciones controladas (imports, `/health`, `/domains`=5, `POST /api/v1/evaluate` mock 200 con contrato/correlación válidos).
- **Causa del “exit code 1” observado previamente:** **artefacto de manejo de stderr en PowerShell** (`NativeCommandError`) al emitirse warning de deprecación `StarletteDeprecationWarning` (`httpx`/`starlette.testclient`) por stderr; el **proceso Python finalizó correctamente (exit 0)** y las aserciones/operaciones completaron. No se reprodujo fallo funcional, excepción de app ni cierre erróneo del artefacto instalado.

### 2.3 Corrección / endurecimiento de evidencia
- Script reproducible añadido: `scripts/smoke_installed_wheel.py` (ejecuta contra paquete instalado, DB temporal, health/domains/evaluate mock, imprime JSON y retorna 0).
- Evidencia actual: `python scripts/smoke_installed_wheel.py` desde paquete instalado → **`{"smoke":"ok","domains":5,"evaluate":"ok"}`**, **`EXIT=0`**. Wheel contiene `case_api`, `case_core`, `case_infra`, `logistics_adapter`, `usgs_adapter`.
- **Limitación:** warning de deprecación upstream (fastapi/starlette/httpx/testclient) persiste en stderr; no se suprime globalmente. Arranque `uvicorn` prolongado desde wheel no ejecutado como prueba separada en esta sesión (**smoke API en proceso/TestClient demostrado**).

**Criterio P0:** smoke reproducible, documentado y con **código de salida 0** del proceso Python demostrado. Causa original explicada con evidencia (no inferida sin prueba).

## 3. P0 — AuthN/AuthZ (inventario, matriz y negativas)

- **Inventario de rutas (FastAPI, verificado):** 23 rutas registradas (docs/openapi/root/health exentas + 17 rutas de negocio protegidas).
- **Rutas de negocio protegidas:** `POST /api/v1/evaluate`, `POST /api/v1/triage`, `GET /api/v1/cases`, `GET /api/v1/cases/{case_id}`, `GET /api/v1/audit/{case_id}`, `GET /api/v1/hitl/pending`, `GET /api/v1/hitl/{decision_id}`, `POST /api/v1/hitl/{decision_id}/under-review|approve|reject|escalate|modify`, `POST /api/v1/comparison`, `GET /domains`, `GET /api/v1/providers`, `GET /api/v1/seismic/events`, `GET /api/v1/seismic/health`.
- **Evidencia nueva:** `tests/integration/test_strict_authz_matrix.py` (**2 passed**) valida para **todas** las rutas protegidas: **401** sin credenciales y **403** con identidad autenticada y scope insuficiente (payloads válidos para alcanzar checks de handler).
- **Matriz:** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` refleja enforcement actual en strict; cobertura **no exhaustiva** para todos los casos borde/efectos secundarios por operación (401/403/404/409 y auditoría/persistencia en cada rama) — **parcial**.
- **IDOR/objeto:** checks 404 fuera de contexto y filtrado en rutas clave demostrados en PoCs/tests previos y en diseño de repos; batería exhaustiva por endpoint/efecto **NO DEMOSTRADA**.

## 4. P0 — SecurityContext, E2E, errores/retries/HITL (parcial)

- Propagación y stamping/filtrado verificados en flujos principales (API/engine/pipeline/repos/auditoría) y PoC de aislamiento por instancias separadas (`test_multiconsumer_isolation_poc.py`, 3 passed en conjunto previo/final). HITL y operaciones protegidas ejercitadas en suites de integración/API existentes.
- **NO DEMOSTRADO:** cobertura E2E completa de todos los caminos requeridos (fallo de auditoría/persistencia intermedio, todos los retries/circuit-breaker/timeout por ruta, adaptadores en cada error, consistencia transaccional auditoría+persistencia+respuesta, concurrencia multi-proceso).

## 5. P0 — Idempotencia, persistencia y migraciones (parcial)

- Idempotencia evaluate strict (replay/conflicto/in-progress) y store compuesto verificados. Concurrencia básica sin 5xx en prueba controlada (SQLite con límites).
- Migraciones v1↔v2 verificadas en copias (upgrade/downgrade best-effort en copia, idempotencia/backfill): `tests/unit/test_sqlite_migrations.py` **3 passed**.
- **NO DEMOSTRADO:** semántica de idempotencia en otras operaciones, carreras multi-proceso, garantías transaccionales fuertes, validación PostgreSQL, procedimiento operativo completo en todos los estados/DBs.

## 6. P1 — Calidad, configuración y documentación operativa

- **Determinismo:** `tests/conftest.py` fuerza `CASE_PROVIDER=mock` en corridas no-`live`; marker `live` registrado/aplicado a `test_groq_live.py`. `.env` local ya no contamina suite determinista no-live.
- **Configuración:** `.env.example` y `render.yaml` actualizados con modos/vars de seguridad (strict, secretos `sync:false`, scopes ejemplo) manteniendo `dev` local; runbooks dev/strict/deploy creados/mejorados (strict aclara que `shared` no implica multi-consumer soportado; scopes/vars deben alinearse con código).
- **Docs históricas:** README/arquitectura/roadmap no actualizados completamente (**pendiente**).

## 7. Quality gates y pruebas (estado final, verificadas)

| Comando / conjunto | Resultado | Detalle |
|---|---|---|
| `ruff check src tests` | **PASS** | 0 errores |
| `mypy src --ignore-missing-imports` | **PASS** | 0 errores (102 source files) |
| Suite determinista no-live (oficial acordado) | **PASS** | **826 passed** (83.98s) — `--ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` |
| `tests/integration/test_strict_authz_matrix.py` | **PASS** | 2 passed (401/403 en 17 rutas protegidas) |
| `tests/integration/test_evaluate_security.py` | **PASS** | 15 passed |
| `tests/integration/test_multiconsumer_isolation_poc.py` | **PASS** | 3 passed (ejecución previa en sesión) |
| `tests/unit/test_sqlite_migrations.py` | **PASS** | 3 passed |
| Packaging + smoke instalado | **PASS** | wheel build/inspect OK; venv limpio install/import OK; `scripts/smoke_installed_wheel.py` **EXIT 0** (`domains=5`, `evaluate=ok`) |

## 8. Evaluación de cierre Nivel B (Strict Single-Consumer)

- **Cumplido/parcialmente demostrado:** configuración strict fail-closed, identidad/scopes server-derived en rutas endurecidas, stamping/filtrado y controles de objeto en flujos clave, idempotencia evaluate, migraciones en copias, gates deterministas, packaging+smoke reproducible con exit 0, matriz de rutas protegidas con negativas 401/403 sistemáticas.
- **Reservas abiertas (impiden “plenamente verificado”):** E2E/authz negativa y por efectos **no exhaustiva** en todos los caminos/operaciones; consistencia auditoría-persistencia ante fallos parciales **NO DEMOSTRADA**; concurrencia multi-proceso/PG **NO DEMOSTRADA**; revisión independiente **pendiente**; alineación documental histórica incompleta.
- **Veredicto B:** **APTO CON RESERVAS** (no plenamente verificado). **C: NO APTO (bloqueado). D: NO APTO.**

## 9. Paquete para revisión independiente (preparado, no ejecutado externamente)

- Arquitectura/flujo y hardening: `docs/MULTICONSUMER_SECURITY_HARDENING.md`, `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, `docs/adr/ADR-CASE-MC-001-deployment-and-isolation-strategy.md`.
- Evidencia técnica: tests de seguridad/aislamiento/migraciones/matriz, script `scripts/smoke_installed_wheel.py`, resultados de gates, informes en `docs/audits/`.
- Runbooks: `docs/RUNBOOK_DEV_LOCAL.md`, `docs/RUNBOOK_STRICT_SINGLE_CONSUMER.md`, `docs/RUNBOOK_DEPLOYMENT_SECURE.md`.
- Limitaciones explícitas: SQLite/concurrencia, sin shared in-process, sin revisión externa, sin validación operativa/producción.

## 10. Estado Git final
- `v4/portfolio-release @ b7021bb`, tracking `origin/v4/portfolio-release`, sin commits locales, sin staging, **sin commit/push/merge/PR/deploy**. Working tree con modificaciones/untracked preexistentes y de estas sesiones preservados. Ignorados relevantes: `build/`, `dist/`, `src/case.egg-info/`.

*NO SE DECLARA revisión independiente realizada, ni cumplimiento normativo, ni aptitud C/D.*
