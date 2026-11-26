# CASE — Cierre técnico Nivel B: Strict Single-Consumer Integrity & E2E Verification (sesión de cierre)

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `v4/portfolio-release`  
**HEAD de referencia (inicio):** `b7021bb4316eec063633bbfdd99d1e0cb9164295` (sin commits nuevos; working tree no limpio, preservado)

> **Alcance de este documento:** cierre técnico local **incremental** ejecutado en esta sesión sobre el estado ya existente en el working tree. No sustituye auditorías previas (`CASE_DEEP_AUDIT_AND_EVOLUTION_2026-11-10.md`, `CASE_FULL_EXECUTION_AND_FINAL_AUDIT_2026-11-10.md`, `CASE_STRICT_SINGLE_CONSUMER_CLOSURE_2026-11-11.md`). No se realizaron commit, push, merge, PR ni despliegue. No se habilitó shared multi-consumer ni producción.

---

## A. Diagnóstico ejecutivo

- **Cerrado/verificado en esta sesión (local):**
  - **Efectos de denegación (401/403, credenciales inválidas, consumidor revocado):** verificado para las 17 rutas de negocio protegidas que las peticiones denegadas **no crean** decisiones, eventos de auditoría ni registros de idempotencia en DB aislada (`tests/integration/test_denial_effects.py`, 4 tests PASS).
  - **Integridad E2E estricta parcial (`/api/v1/evaluate` + HITL/objetos):** replay con misma clave/payload no duplica decisiones ni eventos de auditoría; conflicto (misma clave, payload distinto) devuelve 409 sin efectos adicionales; in-progress devuelve 409 sin ejecución adicional; acceso/mutación HITL cross-contexto sobre objetos ajenos devuelve 404 sin modificar estado/auditoría del objeto autorizado; transición HITL inválida devuelve 400 sin cambio de lifecycle ni evento HITL de negocio (`tests/integration/test_strict_integrity_e2e.py`, 5 tests PASS).
  - **Corrección de integridad (idempotencia):** en `/api/v1/evaluate` (strict), si falla la finalización (`complete`) del registro de idempotencia tras una evaluación ya ejecutada, **ya no se libera** el marcador in-progress (antes se eliminaba, permitiendo re-ejecución/duplicación en reintentos). Ahora se conserva in-progress para rechazar reintentos (409) y evitar duplicación de efectos; requiere recuperación/operación explícita según runbook (trade-off documentado).
  - **Smoke del wheel (script):** `scripts/smoke_installed_wheel.py` reforzado para eliminar cwd/src del `sys.path` y comprobar que módulos (`case_api`, `case_core`, `case_infra`, `logistics_adapter`, `usgs_adapter`) no se resuelven desde árbol fuente (`src/case_*`) cuando sea detectable; reporta paths de módulos.
  - **Documentación de evidencia:** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` actualizada con evidencia de efectos de denegación e integridad E2E parcial.
- **No cerrado en esta sesión:** fault injection determinista completo para escenarios A–G con todas las aserciones de estado persistente/recuperación, cobertura E2E exhaustiva de errores/reintentos/persistencia/auditoría/HITL en todos los caminos, consistencia total decisión↔auditoría↔idempotencia↔respuesta ante todos los fallos parciales, concurrencia multi-proceso robusta, validación PostgreSQL, arranque prolongado Uvicorn desde wheel instalado fuera del repo con evidencia completa, alineación completa de README/ARCHITECTURE/ROADMAP/CAPABILITY_AUDIT/FUTURE_EVOLUTION, revisión independiente externa.
- **Nivel alcanzado (esta sesión):** avance técnico verificable adicional sobre **B (Strict single-consumer)**; **no** se declara B plenamente APTO por pendientes críticos/externos. **C permanece NO APTO (bloqueado)**. **D permanece NO APTO**.

## B. Efectos de denegación

| Cobertura | Resultado | Evidencia |
|---|---|---|
| 401 sin credenciales (17 rutas protegidas) | PASS; sin incremento de `decisions`, `audit_events`, `idempotency_keys` en DB aislada | `tests/integration/test_denial_effects.py::test_401_no_credentials_leaves_persistence_untouched` |
| 403 scope insuficiente (17 rutas, identidad autenticada con scope ajeno) | PASS; sin efectos persistentes | `tests/integration/test_denial_effects.py::test_403_insufficient_scope_leaves_persistence_untouched` |
| 403 consumidor revocado (`active:false`) | PASS; sin efectos persistentes | `tests/integration/test_denial_effects.py::test_403_revoked_consumer_leaves_persistence_untouched` |
| 401 credenciales inválidas | PASS; sin efectos persistentes | `tests/integration/test_denial_effects.py::test_invalid_credentials_leave_persistence_untouched` |
| 401/403 status matrix sistemática (17 rutas) | PASS (preexistente, revalidado) | `tests/integration/test_strict_authz_matrix.py` |

**Rutas cubiertas:** `POST /api/v1/evaluate`, `POST /api/v1/triage`, `GET /api/v1/cases`, `GET /api/v1/cases/{case_id}`, `GET /api/v1/audit/{case_id}`, `GET /api/v1/hitl/pending`, `GET /api/v1/hitl/{decision_id}`, `POST /api/v1/hitl/{decision_id}/under-review`, `POST /api/v1/hitl/{decision_id}/approve`, `POST /api/v1/hitl/{decision_id}/reject`, `POST /api/v1/hitl/{decision_id}/escalate`, `POST /api/v1/hitl/{decision_id}/modify`, `POST /api/v1/comparison`, `GET /domains`, `GET /api/v1/providers`, `GET /api/v1/seismic/events`, `GET /api/v1/seismic/health`.

**Limitaciones:** no se verificaron en esta sesión todas las variantes de payload inválido post-authz, todos los 404/409 aplicables por endpoint con aserciones de efectos en cada caso, ni distinción exhaustiva entre eventos técnicos legítimos de rechazo y eventos de negocio para cada operación (las denegaciones probadas ocurren en auth/middleware o chequeo de scope antes de lógica de negocio; snapshots de tablas de negocio permanecen en 0).

## C. Integridad de evaluación

- **Flujo observado (alto nivel):** auth middleware → identidad/contexto verificado → scope/tenant binding (strict) → reserva idempotencia compuesta (`begin`, tabla `idempotency_keys`, PK consumer/tenant/operation/key) → ejecución triage/engine/pipeline → persistencia decisión y auditoría (repos/adapters SQLite, conexiones separadas; composición por defecto comparte `CASE_DB_PATH`=`case_audit.db`) → `complete` idempotencia o retención segura en fallo de finalización.
- **Topología:** decisiones (`SQLiteDecisionRepository`), auditoría (`SQLiteAuditAdapter`), idempotencia (`SQLiteIdempotencyStore`) — instancias/conexiones independientes; sin garantía transaccional atómica cross-conexión/cross-tabla demostrada en todos los puntos.
- **Cambio aplicado:** en fallo de `complete()` no se hace `release()` (evita duplicación por re-ejecución) → reintentos posteriores: 409 in-progress; recuperación operativa requerida si quedó completada la evaluación pero no el registro.
- **Invariantes demostrados parcialmente:** replay sin duplicar decisión/auditoría; conflicto sin efectos adicionales; in-progress bloquea duplicación; denegaciones sin efectos de negocio en escenarios probados.

## D. Fault injection

| Escenario | Punto de fallo | Esperado | Observado | Resultado | Corrección | Test |
|---|---|---|---|---|---|---|
| Idempotency complete failure (post-evaluación) | `SQLiteIdempotencyStore.complete` lanza excepción tras triage exitoso | No duplicar negocio en retry; evitar liberación insegura | Antes: `release()` permitía re-ejecución; Ahora: se conserva in-progress | **Mitigado (parcial)** | `src/case_api/api/v1/app.py` (no release en fallo de complete) | Cobertura directa de in-progress existente (`test_strict_integrity_e2e.py::test_in_progress_blocks_duplicate_execution`); **falta** test de inyección que fuerce excepción en `complete` y verifique no-duplicación post-retry |
| A–G (prompt: fallo antes de persistir, decisión persistida/auditoría fallida, timeout post-persist, provider error, retry tras error, error durante respuesta) | — | — | — | **No completado** | — | Requiere harness de fault injection determinista |

## E. HITL y acceso por objeto

- **Probado:** acceso/mutación cross-contexto a `decision_id`/`case_id` ajenos → 404, sin cambios en DB del contexto propietario (`test_cross_context_object_access_denied_without_side_effects`). Transición inválida (reject sobre decisión forzada a `approved`) → 400, lifecycle sin cambio, sin incremento de eventos de auditoría (`test_invalid_transition_does_not_change_lifecycle`).
- **No probado exhaustivamente:** todas las transiciones permitidas/prohibidas para cada endpoint HITL con aserciones de efectos persistentes/auditoría por caso, idempotencia/repetición segura de acciones HITL, actor/contexto confiable en todos los eventos, permisos por objeto en cada operación de escritura con payload válido bajo identidades incorrectas.

## F. Concurrencia y SQLite

- **Ejecutado en sesiones previas (referencia):** stress básico concurrente de idempotencia en PoC aislado (`tests/integration/test_multiconsumer_isolation_poc.py`). **En esta sesión:** no se ejecutaron pruebas multi-proceso robustas ni validación PostgreSQL.
- **Límites:** SQLite no se afirma seguro para multi-proceso/multi-worker sin evidencia adicional; modo soportado objetivo: strict single-consumer, instancias aisladas, sin garantía de shared in-process/DB.

## G. Packaging y smoke

- **Script actualizado:** `scripts/smoke_installed_wheel.py` valida imports de `case_api/core/infra/logistics_adapter/usgs_adapter`, limpia `cwd`/`cwd/src` de `sys.path`, intenta detectar cargas desde `src/case_*`, ejecuta `/health`, `/domains`, `POST /api/v1/evaluate` (mock) y reporta paths de módulos.
- **Evidencia de esta sesión:** no se reconstruyó/instaló wheel en venv limpio externo ni se ejecutó Uvicorn prolongado desde wheel instalado fuera del repositorio en este cierre (pendiente de ejecución reproducible end-to-end según bloque 8 del prompt). Última evidencia previa conocida: smoke PASS con TestClient (auditoría 2026-11-11 anterior).

## H. Calidad

| Comando | Resultado |
|---|---|
| `ruff check src tests` | **PASS** (All checks passed) |
| `mypy src --ignore-missing-imports` | **PASS** (102 source files) |
| `python -m pytest tests/integration/test_evaluate_security.py tests/integration/test_strict_authz_matrix.py tests/integration/test_denial_effects.py tests/integration/test_strict_integrity_e2e.py tests/unit/test_sqlite_migrations.py -q` | **29 passed** |
| `python -m pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **No completado en esta sesión** (ejecución larga; evidencia previa comunicada: 828 passed). Requerido re-ejecutar y registrar resultado final antes de declarar gate verde definitivo. |

**Nota:** tests live/external permanecen fuera del gate determinista indicado.

## I. Documentación

- **Actualizados (esta sesión):** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` (evidencia de efectos de denegación e integridad E2E parcial). `scripts/smoke_installed_wheel.py` (verificación de imports/paths).
- **Creados (esta sesión):** `tests/integration/test_denial_effects.py`, `tests/integration/test_strict_integrity_e2e.py`, `docs/audits/CASE_FINAL_SINGLE_CONSUMER_INTEGRITY_CLOSURE_2026-11-11.md`.
- **Pendiente:** alineación completa de `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/CAPABILITY_AUDIT.md`, `docs/FUTURE_EVOLUTION.md` y runbooks con garantías/límites demostrados y operaciones de recuperación de idempotencia.

## J. Cambios de código

**Introducidos/modificados en esta sesión (sobre working tree existente):**
- `src/case_api/api/v1/app.py` — no liberar registro de idempotencia en fallo de `complete()` (evitar duplicación por retry).
- `scripts/smoke_installed_wheel.py` — endurecimiento de aislamiento de imports y reporte de paths de módulos.
- `tests/integration/test_denial_effects.py` — **nuevo**: efectos de denegación sin side-effects persistentes (17 rutas).
- `tests/integration/test_strict_integrity_e2e.py` — **nuevo**: replay/conflicto/in-progress, acceso HITL cross-contexto, transición HITL inválida.
- `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` — evidencia adicional.
- `docs/audits/CASE_FINAL_SINGLE_CONSUMER_INTEGRITY_CLOSURE_2026-11-11.md` — **nuevo** (este informe).

**Preexistentes en working tree (no introducidos en esta sesión, preservados):** modificaciones y untracked listados en `git status`/`git diff --stat` (hardening previo de seguridad, persistencia, migraciones, tests, docs, scripts, config, etc.). No se revertieron ni descartaron.

## K. Evaluación por niveles

| Nivel | Estado | Evidencia | Reservas |
|---|---|---|---|
| A — Local | APTO CON RESERVAS | ruff/mypy PASS; tests de seguridad/integridad focalizados PASS (29); smoke script mejorado; evidencia previa de suite/wheel | Suite determinista completa no re-ejecutada hasta el final en esta sesión; documentación principal no totalmente alineada |
| B — Strict single-consumer | APTO CON RESERVAS (no plenamente cerrado) | Denegaciones sin efectos de negocio demostradas en escenarios cubiertos; replay/conflicto/in-progress sin duplicación en casos probados; IDOR/HITL básico sin efectos cruzados; corrección de riesgo de duplicación en fallo de complete | Faltan fault injection A–G completo, E2E exhaustivo de fallos/reintentos/recovery, concurrencia multi-proceso, Uvicorn/wheel externo completo, revisión independiente, alineación documental total |
| C — Shared multi-consumer | **NO APTO (bloqueado)** | Fail-closed/startup guards y PoCs aislados (previos) | Aislamiento compartido real, authz exhaustiva, concurrencia/DB compartida, revisión de seguridad independiente no demostrados |
| D — Producción | **NO APTO** | — | Sin evidencia operativa/deploy/DR/observabilidad/load/secretos validados; depende de B cerrado y aprobaciones externas |

## L. Riesgos pendientes

| Severidad | Riesgo | Impacto | Evidencia | Próxima acción |
|---|---|---|---|---|
| Alta | Idempotencia en `in_progress` tras fallo de `complete` puede requerir recuperación manual | Bloqueo de reintentos legítimos (409) hasta reconciliación; evita duplicación pero afecta disponibilidad | Cambio en `app.py`; sin mecanismo de recovery automatizado probado | Definir/probar política de recuperación/reconciliación y runbook; considerar estado `completed_pending_finalize` solo si demostrable sin duplicación |
| Alta | Fallos parciales decisión/auditoría/idempotencia no cubiertos por fault injection completo | Posible inconsistencia no detectada en escenarios no probados | Ausencia de harness A–G completo | Implementar fault injection determinista y tests de invariantes por escenario |
| Media | Duplicación de `CASE_RECEIVED` (engine + pipeline) y operaciones no atómicas cross-DB/conexión | Ruido/inconsistencia de trazabilidad; garantías transaccionales limitadas en SQLite | Revisión de flujo (`engine.py`, `reliability/pipeline.py`) | Evaluar deduplicación/idempotencia de eventos y documentar límites transaccionales reales |
| Media | HITL repetición/idempotencia de acciones no formalizada más allá de guardas de estado | Posibles 400/efectos ambiguos ante retries de cliente | Tests parciales | Definir semántica de retry por operación HITL y cubrirla |
| Media | Smoke Uvicorn/wheel instalado fuera del repo no re-ejecutado en esta sesión | Regresión de empaquetado/arranque no detectada | Pendiente | Ejecutar build+install+smoke desde directorio temporal externo y, si es seguro, arranque Uvicorn con shutdown limpio |
| Alta | Revisión independiente de seguridad no realizada | Riesgos no descubiertos | Externo | Paquetizar evidencia y solicitar revisión |

## M. Revisión externa

- **Preparado en repo/local:** matriz de authz y evidencia de denegaciones/integridad parcial (`docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`), tests `test_strict_authz_matrix.py`, `test_denial_effects.py`, `test_strict_integrity_e2e.py`, `test_evaluate_security.py`, migraciones y runbooks existentes.
- **Debe revisar persona independiente:** modelo de amenazas y enforcement server-side, aislamiento de contexto en todos los caminos (incl. errores/retries/adapters), semántica de idempotencia y recuperación ante fallos parciales, consistencia auditoría↔decisión, configuración operativa strict/single-consumer y límites SQLite.

## N. Estado Git final

- **Rama:** `v4/portfolio-release`
- **HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295`
- **Tracking:** `[origin/v4/portfolio-release]` (sin commits locales adelantados)
- **Staged:** ninguno
- **Modificados (working tree, sin stage):** `.env.example`, `pyproject.toml`, `render.yaml`, `src/case_api/api/v1/app.py`, `src/case_api/api/v1/auth.py`, `src/case_core/application/engine.py`, `src/case_core/ports/audit.py`, `src/case_core/ports/decision_repository.py`, `src/case_core/ports/repository.py`, `src/case_core/reliability/pipeline.py`, `src/case_infra/persistence/sqlite_adapter.py`, `src/case_infra/persistence/sqlite_audit.py`, `src/case_infra/persistence/sqlite_decision_repository.py`, `tests/integration/test_evaluate_contract.py`, `tests/integration/test_groq_live.py`, `tests/unit/test_behavioral.py`, `tests/unit/test_bootstrap.py`, `tests/unit/test_persistence_roundtrip.py`, `tests/unit/test_reliability.py`, `tests/unit/test_security.py`, `tests/unit/test_sqlite.py`, `tests/unit/test_triage_engine.py` (mezcla de cambios preexistentes y cambios de esta sesión en `app.py`).
- **Untracked (relevantes):** `src/case_api/api/v1/security.py`, `src/case_core/contracts/security.py`, `src/case_infra/persistence/sqlite_idempotency.py`, `src/case_infra/persistence/sqlite_migrations.py`, `tests/conftest.py`, `tests/integration/test_evaluate_security.py`, `tests/integration/test_multiconsumer_isolation_poc.py`, `tests/integration/test_strict_authz_matrix.py`, `tests/integration/test_denial_effects.py`, `tests/integration/test_strict_integrity_e2e.py`, `tests/unit/test_sqlite_migrations.py`, `scripts/migrate_case_sqlite.py`, `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, `docs/MULTICONSUMER_SECURITY_HARDENING.md`, `docs/RUNBOOK_*.md`, `docs/adr/`, `docs/audits/`, `docs/prompts/`, `AGENTS.md.backup`, `pytest_case.txt`, `src/pytest_case.txt`, `src/pytest_output.txt`.
- **Commits/push/merge/PR/despliegue:** **ninguno realizado**.

---

## 23. Declaración de cierre

**No se declara NIVEL B plenamente APTO** en esta sesión: persisten brechas técnicas y evidencias pendientes (fault injection A–G completo, E2E exhaustivo de fallos/recovery, concurrencia multi-proceso, validación Uvicorn/wheel externo completa, alineación documental total, re-ejecución registrada de la suite determinista completa y revisión independiente). Se declara **progreso técnico verificable** con reservas explícitas; **C** permanece bloqueado y **D** no apto.
