# CASE — Scaling & Integrity Evolution (Strict Single-Consumer → Shared Multi-Consumer, base controlada)

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `v4/portfolio-release`  
**HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` (sin commits nuevos; working tree preservado)

> Informe de evolución técnica incremental sobre el estado real del working tree. No reemplaza auditorías previas. No se realizó commit/push/merge/PR/despliegue. **C (shared multi-consumer) y D (producción) no habilitados.**

---

## 1. Estado inicial
- Baseline heredado: hardening previo (SecurityContext, authz/scopes, stamping/filtrado, idempotencia compuesta `/api/v1/evaluate`, migraciones SQLite v1↔v2, PoCs aisladas, runbooks/auditorías previas). Nivel B comunicado como APTO CON RESERVAS; C/D NO APTO.
- Riesgo identificado: fallo en `complete()` de idempotencia liberaba marcador `in_progress` tras ejecución → posibilidad de duplicación en retry.

## 2. Baseline de tests y quality gates (esta sesión)
| Gate | Resultado | Evidencia |
|---|---|---|
| `ruff check src tests` | **PASS** | All checks passed |
| `mypy src --ignore-missing-imports` | **PASS** | 102 source files |
| Suite determinista completa no-live: `pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **837 passed, 0 failed, 0 skipped** (84.70s) | `docs/audits/pytest_deterministic_full_2026-11-11_r2.txt` |
| Focalizados seguridad/integridad/migraciones | **29 passed** (evaluate_security 15, strict_authz_matrix 2, denial_effects 4, strict_integrity_e2e 5, sqlite_migrations 3) | ejecución local |

> Nota: una ejecución anterior de la suite completa mostró 8 fallos por contaminación de entorno (`CASE_DB_PATH`/estado de módulo) introducida por helpers de tests nuevos; se corrigió el aislamiento (save/restore env y repos/idempotency store de `case_api.api.v1.app`) y la suite completa quedó verde en re-ejecución.

## 3. Arquitectura actual (resumen operativo)
- API FastAPI + `TriageEngine` + `ReliabilityPipeline` + repos/adapters SQLite (decisiones, auditoría) + `SQLiteIdempotencyStore` (scoped) + `SecurityContext` server-derived en strict. 17 rutas de negocio protegidas en strict por auth+scopes; `/health`, docs raíz exentas.
- Persistencia por defecto compartiendo `CASE_DB_PATH` (`case_audit.db`) en composición, pero con conexiones/operaciones separadas (sin atomicidad transaccional cross-conexión demostrada).
- Idempotencia compuesta `(consumer_id, tenant_id, operation, idempotency_key)` con hash de payload, estados prácticos `in_progress`/`completed` en tabla; replay/conflicto/in-progress aplicados en `/api/v1/evaluate` (strict).

## 4. Máquina de estados de idempotencia (actual + cambio)
- **Actual en almacenamiento:** `in_progress` → `completed` (vía `complete`), o eliminación en fallo de negocio previo a completar (vía `release` en path de error de triage). Replay: respuesta cacheada si `completed` y hash coincide; conflicto 409 si hash difiere; 409 si `in_progress`.
- **Cambio aplicado (integridad):** si `complete()` falla tras evaluación ejecutada, **no** se libera el registro (antes se borraba) para evitar re-ejecución/duplicación. El registro permanece `in_progress`.
- **Implicación:** evita duplicados, pero puede requerir **recuperación/reconciliación operativa** cuando la operación de negocio sí persistió. No implementada aún una máquina de estados explícita (`failed`/`recovery_required`/lease/fencing/reconciliación automática segura).

## 5. Recuperación de operaciones incompletas
- **Estado:** **parcial/no automatizado**. Existe protección contra duplicación (retención de `in_progress` en fallo de `complete`), pero falta: detección/consulta de atascados, correlación con decisión/auditoría persistida, reconciliación segura idempotente, endpoint/script admin protegido, auditoría de intervención, manejo de estado incierto, leases/heartbeat y pruebas de recuperación/concurrencia de recuperación.
- **Riesgo:** bloqueos 409 hasta intervención manual; reconciliación incorrecta podría ser insegura si se implementa sin pruebas.

## 6. Resultados de fault injection A–G
| Escenario | Estado |
|---|---|
| A Fallo antes de persistir | No ejecutado (harness pendiente) |
| B Decisión persistida, auditoría fallida | No ejecutado |
| C Auditoría escrita, finalización idempotencia fallida | **Mitigación parcial**: no-release en fallo de `complete` evita duplicación por retry; falta inyección determinista que fuerce excepción y verifique estado/recuperación |
| D Timeout después de persistir | No ejecutado |
| E Error del provider | No ejecutado |
| F Retry después de error | Parcial (replay/conflicto/in-progress cubiertos) |
| G Error al devolver respuesta tras persistencia | No ejecutado |

## 7. Consistencia decisión/auditoría
- Demostrada parcialmente: replay no incrementa decisiones/auditorías; denegaciones no generan efectos de negocio en escenarios cubiertos. No demostrada consistencia total ante fallos parciales ni deduplicación de `CASE_RECEIVED` (emitido en engine y pipeline).

## 8. Tests HITL
- **Probado:** acceso/mutación cross-contexto → 404 sin efectos en objeto autorizado; transición inválida (reject desde approved forzado) → 400 sin cambio de lifecycle ni incremento de auditoría.
- **Pendiente:** matriz completa de transiciones permitidas/inválidas/repetidas/concurrentes para pending/under-review/approve/reject/modify/escalate con aserciones de persistencia+auditoría+actor server-derived en cada caso.

## 9. Concurrencia SQLite
- Cobertura previa básica (PoC/threads) referenciada; sin nuevas pruebas multi-proceso robustas en esta sesión. Límites SQLite (locking/conexiones/procesos) no revalidados exhaustivamente.

## 10. Pruebas multi-proceso
- **No ejecutadas** (entorno/alcance de sesión).

## 11. PostgreSQL
- **No validado** en esta sesión (no disponible/ejecutado como instancia desechable aquí). Migraciones/adaptadores preparados parcialmente en diseño previo; requiere PoC transaccional y concurrencia real.

## 12. Modelo de identidad multi-consumer (diseño objetivo, no demostrado)
- Diferenciar `consumer_id`, `tenant_id`, `organization_id`, actor/principal, credencial y scopes; límite de aislamiento por (consumer, tenant[, org]) según política. `SecurityContext` ya transporta campos base pero no valida despliegue compartido real multi-consumer en misma app/DB.

## 13. Arquitectura objetivo compartida (Nivel C, experimental/bloqueada)
- Misma app, persistencia compartida (preferente PostgreSQL) con aislamiento en capa de datos (constraints/índices/FKs + filtros obligatorios + opcional RLS evaluada), idempotencia/auditoría/HITL particionadas por contexto, transacciones y control de concurrencia, pruebas de no-fuga cross-consumer bajo carga concurrente. **No implementado/activado.**

## 14. PoC shared
- **No ejecutada** como shared real (misma app+misma DB compartida multi-consumer). Existen PoCs de instancias aisladas (previas) — no equivalen a Nivel C.

## 15. Wheel y Uvicorn
- Script `scripts/smoke_installed_wheel.py` endurecido (aislamiento de imports/paths). **No re-ejecutado** en esta sesión: build+install en venv limpio fuera del repo, verificación `site-packages`, arranque Uvicorn con DB temporal/readiness/health/evaluate/shutdown y exit code 0.

## 16. Documentación actualizada (esta sesión)
- `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` (efectos de denegación + integridad E2E parcial).
- `docs/audits/CASE_FINAL_SINGLE_CONSUMER_INTEGRITY_CLOSURE_2026-11-11.md`.
- `docs/audits/CASE_SCALING_AND_INTEGRITY_EVOLUTION_2026-11-11.md` (este informe).
- Evidencia: `docs/audits/pytest_deterministic_full_2026-11-11.txt` (r1, 8 fallos por contaminación), `docs/audits/pytest_deterministic_full_2026-11-11_r2.txt` (r2, 837 passed).
- Pendiente: alineación completa README/ARCHITECTURE/ROADMAP/CAPABILITY_AUDIT/FUTURE_EVOLUTION/MULTICONSUMER_SECURITY_HARDENING/runbooks con recuperación, límites SQLite, garantías demostradas/no demostradas.

## 17. Quality gates finales
- ruff/mypy/suite determinista completa: **PASS** (ver tabla sección 2). Gates adicionales requeridos por prompt (fault injection completo, concurrencia multi-proceso, PostgreSQL, wheel+uvicorn externo, PoC shared): **no completados**.

## 18. Auditoría interna
- Revisión puntual aplicada: corrección de riesgo de duplicación en `complete()`; aislamiento de tests para evitar contaminación; verificación de denegaciones sin efectos en casos cubiertos. **No** equivale a auditoría independiente completa de todos los diffs/caminos.

## 19. Riesgos pendientes
| Sev | Riesgo | Evidencia | Acción |
|---|---|---|---|
| Alta | `in_progress` sin recuperación automatizada (posible bloqueo 409) | cambio app.py, sin tooling de reconciliación | diseñar estados/lease/reconciliación segura + tests + runbook/script admin |
| Alta | Fallos parciales A–G no cubiertos | sin harness completo | implementar fault injection determinista y matriz de invariantes |
| Media | Duplicación `CASE_RECEIVED` y no-atomicidad cross-operaciones | flujo engine/pipeline | deduplicar/documentar y reforzar garantías |
| Media | HITL repetición/concurrencia no exhaustiva | cobertura parcial | ampliar matriz y control de concurrencia si aplica |
| Media | Smoke/uvicorn externo no revalidado | pendiente | ejecutar pipeline de wheel aislado |
| Alta | C/D sin evidencia de aislamiento/revisión externa | bloqueadores conocidos | PoC shared real + PostgreSQL + security review |

## 20. Estado de los niveles A–D
| Nivel | Estado | Evidencia | Bloqueadores |
|---|---|---|---|
| A — Local | **APTO CON RESERVAS** | ruff/mypy PASS, 837 passed, fixes de integridad/aislamiento de tests | docs principales no alineadas; smoke uvicorn externo no re-ejecutado |
| B — Strict single-consumer | **APTO CON RESERVAS (no plenamente cerrado)** | denegaciones sin efectos, replay/conflicto/in-progress sin duplicación en casos probados, suite completa verde, corrección anti-duplicación en complete | recuperación de idempotencia incompleta, fault injection A–G, HITL/concurrencia exhaustivos, evidencia operativa completa, revisión externa |
| C — Shared multi-consumer | **NO APTO (bloqueado)** | guards fail-closed y diseño parcial previo | aislamiento compartido real no demostrado, PoC multi-consumer misma app+DB, PostgreSQL/concurrencia, revisión seguridad |
| D — Producción | **NO APTO** | — | depende de B/C, ops/DR/observabilidad/load/secretos/revisión/aprobaciones |

## 21. Roadmap siguiente
1. Implementar recuperación segura de idempotencia (estados explícitos, reconciliación idempotente, tooling protegido, pruebas).
2. Construir harness de fault injection A–G y cerrar matriz de integridad.
3. Completar matriz HITL + concurrencia SQLite/multi-proceso con límites declarados.
4. Revalidar wheel+uvicorn desde instalación aislada fuera del repo.
5. Alinear documentación/runbooks/ADR con garantías reales.
6. Diseñar y ejecutar PoC shared multi-consumer experimental aislada (PostgreSQL) sin habilitar C estable.

## N. Estado Git
- **Rama:** `v4/portfolio-release` | **HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` | **Tracking:** `origin/v4/portfolio-release`
- **Staged:** ninguno. **Commits/push/merge/PR/despliegue:** ninguno.
- **Modificados:** `.env.example`, `pyproject.toml`, `render.yaml`, `scripts/smoke_installed_wheel.py`, `src/case_api/api/v1/app.py`, `src/case_api/api/v1/auth.py`, `src/case_core/application/engine.py`, `src/case_core/ports/{audit,decision_repository,repository}.py`, `src/case_core/reliability/pipeline.py`, `src/case_infra/persistence/{sqlite_adapter,sqlite_audit,sqlite_decision_repository}.py`, `tests/integration/test_evaluate_contract.py`, `tests/integration/test_groq_live.py`, `tests/unit/{test_behavioral,test_bootstrap,test_persistence_roundtrip,test_reliability,test_security,test_sqlite,test_triage_engine}.py` (mezcla preexistente + cambios de sesión en app/smoke/tests nuevos).
- **Untracked relevantes:** `src/case_api/api/v1/security.py`, `src/case_core/contracts/security.py`, `src/case_infra/persistence/{sqlite_idempotency,sqlite_migrations}.py`, `tests/conftest.py`, `tests/integration/{test_denial_effects,test_evaluate_security,test_multiconsumer_isolation_poc,test_strict_authz_matrix,test_strict_integrity_e2e}.py`, `tests/unit/test_sqlite_migrations.py`, `scripts/migrate_case_sqlite.py`, `docs/{AUTHZ_MATRIX_ENDPOINT_SCOPE,MULTICONSUMER_SECURITY_HARDENING,RUNBOOK_DEPLOYMENT_SECURE,RUNBOOK_DEV_LOCAL,RUNBOOK_STRICT_SINGLE_CONSUMER}.md`, `docs/adr/`, `docs/audits/`, `docs/prompts/`, `AGENTS.md.backup`, `pytest_case.txt`, `src/pytest_case.txt`, `src/pytest_output.txt`.
- **Confirmación:** no se realizó publicación ni despliegue.
