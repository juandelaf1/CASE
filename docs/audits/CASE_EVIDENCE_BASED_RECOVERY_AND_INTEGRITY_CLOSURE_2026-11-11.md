# CASE — Evidence-Based Recovery & Integrity Closure (estado real, cierre incremental)

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `v4/portfolio-release`  
**HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` (sin commits nuevos; working tree preservado)

> No sobrescribe auditorías previas (`CASE_*` 2026-11-10/11). **Sin commit/push/merge/PR/rebase/despliegue.** Nivel C/D no habilitados. Evidencia local/aislada; revisión de seguridad externa pendiente.

---

## A. Diagnóstico ejecutivo
- **Avances demostrados en esta sesión:** baseline determinista completa **840 passed** (r4), ruff/mypy PASS, corrección de contaminación de tests, anti-duplicación por retención de `in_progress` en fallo de `complete()`, estados de recuperación fail-closed en API/store, **eliminación/inhabilitación del completado de reconciliación desde respuesta no verificada** (`complete_reconciled` rechaza; CLI `--complete` rechazado), migración formal v2 alineada para columnas/índices de recuperación idempotente, pruebas de denegación sin efectos persistentes (17 rutas), integridad E2E parcial (replay/conflicto/in-progress, IDOR/HITL básico), smoke de wheel instalado fuera del repo (**EXIT 0**, módulos en `site-packages`) y smoke Uvicorn desde instalación aislada con `/health` 200, `/domains` (5), `/api/v1/evaluate` mock OK y cierre limpio.
- **No cerrado:** correlación persistida inequívoca end-to-end (`operation_id`/vínculos idempotency↔decision↔audit↔resultado), recuperación evidence-based automática/completa (sin fabricar resultados), fencing/CAS/lease y concurrencia de recuperación, harness y ejecución de fault injection **A–G**, consistencia total ante fallos parciales, deduplicación/semántica final de `CASE_RECEIVED`, matriz HITL exhaustiva, concurrencia/multi-proceso/PostgreSQL demostrados, PoC shared multi-consumer real (misma app+DB), ADRs y alineación documental completa, revisión externa.
- **Evaluación:** A/B **APTO CON RESERVAS** (B no cerrado); C/D **NO APTO**.

## B. Baseline y quality gates
| Gate | Comando | Resultado | Evidencia |
|---|---|---|---|
| Ruff | `ruff check src tests scripts/reconcile_idempotency.py` | **PASS** | ejecución local 2026-11-11 |
| Mypy | `mypy src --ignore-missing-imports` | **PASS** (102 source files) | ejecución local |
| Suite determinista no-live | `pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **840 passed, 0 failed, 0 skipped** (86.06s) | `docs/audits/pytest_deterministic_full_2026-11-11_r4.txt` |
| Focalizados | `pytest tests/integration/test_idempotency_recovery.py tests/integration/test_denial_effects.py tests/integration/test_strict_integrity_e2e.py tests/unit/test_sqlite_migrations.py -q` | **15 passed** | ejecución local |
| Focalizados (ampliado, sesión) | `evaluate_security + strict_authz_matrix + denial_effects + strict_integrity_e2e + idempotency_recovery + sqlite_migrations` | **32 passed** | ejecución local |

Historial: r1 8 fallos por contaminación (`pytest_deterministic_full_2026-11-11.txt`), corregido con restore de env/estado (`test_denial_effects.py`, `test_strict_integrity_e2e.py`); r2 837; r3 840; r4 840.

## C. Modelo de correlación
- **Implementado:** `SecurityContext` server-derived, stamping/filtrado por `consumer_id/tenant_id/organization_id` en persistencia/auditoría (caminos existentes), `correlation_id` en request/eventos según flujo, clave idempotente compuesta `(consumer, tenant, operation, idempotency_key)` + `request_hash`.
- **No implementado:** `operation_id` interno único generado en reserva y propagado end-to-end; vínculos persistidos inequívocos idempotency↔decision↔case↔audit↔resultado; restricciones/índices de correlación completos.
- **Estado:** **parcial / no demostrado** para recuperación automática evidence-based en todos los casos.

## D. Recuperación idempotente
- **Estados:** `in_progress`, `completed`, `recovery_required`, `failed`, `reconciling`.
- **API (strict):** replay si `completed`+hash+`response_json`; 409 `IDEMPOTENCY_CONFLICT` (hash distinto); 409 `IDEMPOTENCY_IN_PROGRESS`; 409 `IDEMPOTENCY_RECOVERY_REQUIRED` para estados de recuperación/bloqueo. Fallo de `complete()` tras ejecución no libera registro (anti-duplicación).
- **Store:** `list_stale_in_progress`, `mark_recovery_required`, guardas de `release` (solo `in_progress`). **`complete_reconciled` deshabilitado/denegado** por seguridad: lanza error al rechazar completado desde respuesta no verificada (no fabrica resultados).
- **CLI:** `scripts/reconcile_idempotency.py` permite listar stale y marcar `recovery_required` (fail-closed); `--complete` **rechazado** explícitamente (requiere recuperación evidence-based con correlación verificada, pendiente de implementación).
- **Pruebas:** `tests/integration/test_idempotency_recovery.py` — bloqueo `recovery_required` sin duplicación/efectos; stale→`recovery_required`; rechazo de completado no verificado (registro permanece no completado). Replay/conflicto/in-progress sin duplicación en `tests/integration/test_strict_integrity_e2e.py`.
- **Pendiente:** clasificación demostrada no-ejecutado/ejecutado/incertidumbre, recuperación por evidencia persistida (localizar decisión/auditoría/resultado real y completar sin re-ejecutar), CAS/fencing/lease, recuperación concurrente/autorizada, auditoría administrativa estructurada completa.

## E. Migraciones
- **Alineado:** `sqlite_migrations.py` v2 crea/asegura `idempotency_keys` con columnas de recuperación (`recovery_note`, `recovery_actor`, `recovery_at`) e índices (`idx_idem_consumer_tenant`, `idx_idem_status_updated`) de forma idempotente; stores realizan aseguramiento defensivo en runtime.
- **Probado:** `tests/unit/test_sqlite_migrations.py` **3 passed** (upgrade v1→v2 en copia preserva datos/backfill, downgrade en copia a v1, idempotencia). 
- **Pendiente:** versión formal adicional si se introducen campos de correlación/operation_id; cobertura exhaustiva de estados/fallos parciales de migración y reconciliación de divergencias runtime↔formal.

## F. Fault injection A–G
- **Matriz:** `docs/audits/CASE_FAULT_INJECTION_MATRIX.md` creada (objetivo A–G; la mayoría no demostrado).
- **Estado:** harness determinista **no implementado**. C mitigado parcialmente (no-release, bloqueo); F parcial (replay/conflicto/in-progress). A,B,D,E,G **no demostrados**.
- **Pruebas:** no existen suites dedicadas por escenario con inyección controlada y aserciones completas de DB/auditoría/idempotencia/retry/recuperación.

## G. Consistencia y eventos
- **`CASE_RECEIVED`:** emitido en `TriageEngine.execute` y `ReliabilityPipeline.run` (posible duplicación semántica; tests verifican presencia, no unicidad). **No modificado** (riesgo de regresión en consumidores/semántica); pendiente decisión de origen único/dedupe por `operation_id`/etapa.
- **Consistencia:** demostrada parcialmente en escenarios cubiertos (denegaciones sin efectos, replay sin duplicados, transición HITL inválida sin efectos). **No demostrada** atomicidad/coherencia ante fallos parciales A–G y en todos los caminos de error/retry.

## H. HITL
- **Probado:** acceso/mutación cross-contexto 404 sin efectos en propietario; transición inválida (reject desde approved forzado) 400 sin cambio de lifecycle ni incremento de auditoría de negocio.
- **Pendiente:** matriz completa pending/under-review/approve/reject/modify/escalate (permitidas/prohibidas/repetidas/concurrentes/retry), actor server-derived y auditoría/efectos persistentes en todas las operaciones, control de concurrencia donde aplique.

## I. SQLite y concurrencia
- **Demostrado:** estabilidad funcional en suite determinista y pruebas de integridad focalizadas; aislamiento por contexto en repos.
- **No demostrado:** concurrencia sostenida, multi-proceso, locking/`busy_timeout`/journal/transacciones bajo carga, recuperación concurrente. Límites operativos **no cerrados**; no asumir multi-worker/multi-proceso.

## J. PostgreSQL y PoC shared
- **PostgreSQL:** `psql` no disponible; Docker presente pero instancia desechable **no levantada/validada** en esta sesión. **No demostrado.**
- **PoC shared multi-consumer real:** **no ejecutada** (requerida: misma app + misma persistencia compartida + ≥2 consumidores + concurrencia + lecturas/escrituras/idempotencia/auditoría/HITL con pruebas negativas cruzadas). PoCs previas de instancias aisladas no equivalen a Nivel C. **C bloqueado/fail-closed, experimental no habilitado.**

## K. Wheel/Uvicorn
- **Wheel:** `case-1.0.0-py3-none-any.whl` construido e instalado en venv limpio temporal (`%LOCALAPPDATA%\Temp\opencode\case-wheel-smoke`).
- **Smoke fuera del repo (instalado):** desde directorio externo, `scripts/smoke_installed_wheel.py` → **EXIT 0**, `{"smoke":"ok","domains":5,"evaluate":"ok"}`, módulos desde `site-packages` del venv: `case_api`, `case_core`, `case_infra`, `logistics_adapter`, `usgs_adapter`.
- **Uvicorn (instalado, fuera de repo, DB temporal):** `127.0.0.1:8765`, readiness OK, `GET /health` 200, `GET /domains` 5 dominios, `POST /api/v1/evaluate` mock OK, shutdown limpio (`PROC=stopped`). Warning stderr upstream (Starlette/httpx) no funcional.
- **Pendiente:** prueba prolongada/carga y verificación exhaustiva de no-huérfanos en escenarios largos.

## L. Documentación y ADR
- **Actualizados/creados:** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, `docs/audits/CASE_FAULT_INJECTION_MATRIX.md`, informes de cierre/evolución/evidencia y resultados de suite (`pytest_deterministic_full_2026-11-11_r{1..4}.txt`).
- **Pendiente:** alineación completa de `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/CAPABILITY_AUDIT.md`, `docs/FUTURE_EVOLUTION.md`, `docs/MULTICONSUMER_SECURITY_HARDENING.md`, runbooks; ADRs requeridos (correlación, recuperación evidence-based, migración esquema, fault injection/consistencia, eventos/dedupe, HITL/concurrencia, SQLite/PostgreSQL, shared multi-consumer).

## M. Cambios exactos
- **Modificados:** `src/case_api/api/v1/app.py`, `src/case_infra/persistence/sqlite_idempotency.py`, `src/case_infra/persistence/sqlite_migrations.py`, `scripts/smoke_installed_wheel.py`, `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, `tests/integration/test_denial_effects.py`, `tests/integration/test_strict_integrity_e2e.py`, `tests/integration/test_idempotency_recovery.py`.
- **Nuevos:** `scripts/reconcile_idempotency.py`, `docs/audits/CASE_FAULT_INJECTION_MATRIX.md`, `docs/audits/CASE_EVIDENCE_BASED_RECOVERY_AND_INTEGRITY_CLOSURE_2026-11-11.md`, evidencias de suite en `docs/audits/pytest_deterministic_full_2026-11-11_r{1..4}.txt` (y otros artefactos untracked preexistentes preservados).
- **Preservados (preexistentes, no revertidos):** cambios/untracked de hardening previo listados en estado Git.

## N. Auditoría independiente interna
- Revisión focal: eliminación de ruta de completado no verificado, retención anti-duplicación, bloqueos de recuperación, pruebas de denegación sin efectos e integridad parcial, aislamiento de tests, gates verdes. **No** constituye auditoría independiente completa de todos los diffs/caminos ni revisión de seguridad externa.

## O. Estado A–D
| Nivel | Estado | Evidencia | Bloqueadores |
|---|---|---|---|
| A — Local | **APTO CON RESERVAS** | ruff/mypy PASS, 840 passed, wheel+Uvicorn smoke aislado PASS | docs/ADRs/runbooks, smoke prolongado/carga |
| B — Strict single-consumer | **APTO CON RESERVAS (no cerrado)** | authz fail-closed en rutas cubiertas, denegaciones sin efectos, idempotencia sin duplicación en casos probados, recuperación bloqueada fail-closed, gates verdes | correlación end-to-end, recovery evidence-based completa, fault injection A–G, consistencia total, HITL/concurrencia/multi-proceso, migración formal ampliada, revisión externa |
| C — Shared multi-consumer | **NO APTO (bloqueado)** | diseño/guards parciales | misma app+DB compartida no demostrada, PostgreSQL/concurrencia/ataques cruzados, idempotencia/auditoría/HITL compartidos validados, revisión seguridad |
| D — Producción | **NO APTO** | — | infraestructura/ops/secretos/DR/observabilidad/load, cierre B/C, aprobaciones |

## P. Riesgos
| Sev | Riesgo | Acción |
|---|---|---|
| Alta | Sin correlación/evidencia persistida fuerte para reconciliación automática segura; estados inciertos no resueltos | implementar `operation_id`+vínculos, recovery evidence-based, CAS/lease/fencing y pruebas |
| Alta | Fault injection A–G y garantías ante fallos parciales no demostradas | harness determinista + matriz con evidencia por escenario |
| Media | Duplicación `CASE_RECEIVED`, HITL/concurrencia incompletos | semántica/dedupe, matriz HITL completa, pruebas multi-proceso/SQLite |
| Media | PostgreSQL/shared PoC no validados | Docker/PostgreSQL desechable + PoC experimental aislada (sin habilitar C) |
| Alta | Sin revisión de seguridad independiente | paquete de evidencia y revisión externa |

## Q. Próximo hito
1. Correlación end-to-end y recuperación **evidence-based** (sin respuestas fabricadas), con concurrencia de recuperación y auditoría administrativa.  
2. Harness fault injection A–G + invariantes decisión/auditoría/idempotencia/respuesta/retry.  
3. HITL exhaustivo y validación SQLite/multi-proceso (límites declarados).  
4. PostgreSQL desechable y PoC shared experimental real (misma app+DB), mantener C bloqueado.  
5. Alineación documental/ADRs y paquete de revisión externa.

## R. Estado Git final
- **Rama/HEAD:** `v4/portfolio-release` @ `b7021bb4316eec063633bbfdd99d1e0cb9164295` | **Tracking:** `origin/v4/portfolio-release` | **Staged:** ninguno
- **Operaciones:** sin commit, push, merge, PR, rebase ni despliegue
- **Modificados (tracked):** `.env.example`, `pyproject.toml`, `render.yaml`, `scripts/smoke_installed_wheel.py`, `src/case_api/api/v1/app.py`, `src/case_api/api/v1/auth.py`, `src/case_core/application/engine.py`, `src/case_core/ports/{audit,decision_repository,repository}.py`, `src/case_core/reliability/pipeline.py`, `src/case_infra/persistence/{sqlite_adapter,sqlite_audit,sqlite_decision_repository,sqlite_idempotency,sqlite_migrations}.py`, `tests/integration/test_evaluate_contract.py`, `tests/integration/test_groq_live.py`, `tests/unit/{test_behavioral,test_bootstrap,test_persistence_roundtrip,test_reliability,test_security,test_sqlite,test_triage_engine}.py`
- **Untracked relevantes:** `src/case_api/api/v1/security.py`, `src/case_core/contracts/security.py`, `tests/conftest.py`, `tests/integration/{test_denial_effects,test_evaluate_security,test_idempotency_recovery,test_multiconsumer_isolation_poc,test_strict_authz_matrix,test_strict_integrity_e2e}.py`, `tests/unit/test_sqlite_migrations.py`, `scripts/{migrate_case_sqlite,reconcile_idempotency}.py`, `docs/{AUTHZ_MATRIX_ENDPOINT_SCOPE,MULTICONSUMER_SECURITY_HARDENING,RUNBOOK_*}.md`, `docs/adr/`, `docs/audits/`, `docs/prompts/`, `AGENTS.md.backup`, `pytest_case.txt`, `src/pytest_case.txt`, `src/pytest_output.txt`
- **Confirmación:** trabajo en local, sin publicación ni despliegue; C/D permanecen bloqueados/no aptos.