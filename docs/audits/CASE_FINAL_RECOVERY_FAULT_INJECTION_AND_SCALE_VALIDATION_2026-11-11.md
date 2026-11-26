# CASE — Final Recovery, Fault Injection & Scale Validation (cierre técnico incremental)

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `v4/portfolio-release`  
**HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` (sin commits nuevos; working tree preservado)

> No sobrescribe informes previos. **Sin commit/push/merge/PR/despliegue.** Shared multi-consumer y producción **no habilitados**. Evidencia local/aislada; **revisión de seguridad externa no realizada**.

---

## 1. Estado inicial
- Baseline heredada y endurecimiento previo (SecurityContext, authz strict, idempotencia compuesta, migraciones v1↔v2, PoCs aisladas, runbooks). Riesgo conocido: fallo de `complete()` podía liberar `in_progress` y permitir duplicación (corregido en sesiones previas reteniendo `in_progress`).
- Insumos: `docs/audits/CASE_INTEGRITY_RECOVERY_AND_SCALE_READINESS_2026-11-11.md`, `CASE_SCALING_AND_INTEGRITY_EVOLUTION_2026-11-11.md`, `CASE_FINAL_SINGLE_CONSUMER_INTEGRITY_CLOSURE_2026-11-11.md`, `CASE_FULL_EXECUTION_AND_FINAL_AUDIT_2026-11-10.md`, `CASE_DEEP_AUDIT_AND_EVOLUTION_2026-11-10.md`.

## 2. Baseline
| Gate | Comando | Resultado | Evidencia |
|---|---|---|---|
| Ruff | `ruff check src tests scripts/reconcile_idempotency.py` | **PASS** | ejecución local 2026-11-11 |
| Mypy | `mypy src --ignore-missing-imports` | **PASS** (102 archivos) | ejecución local |
| Suite determinista no-live | `pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **840 passed, 0 failed, 0 skipped** (84.85s) | `docs/audits/pytest_deterministic_full_2026-11-11_r3.txt` |
| Seguridad/integridad/recuperación/migraciones (focalizado) | `pytest tests/integration/test_evaluate_security.py tests/integration/test_strict_authz_matrix.py tests/integration/test_denial_effects.py tests/integration/test_strict_integrity_e2e.py tests/integration/test_idempotency_recovery.py tests/unit/test_sqlite_migrations.py -q` | **32 passed** | ejecución local |

> Historial suite: r1 8 fallos por contaminación de tests (`pytest_deterministic_full_2026-11-11.txt`) corregida con restore de env/estado global; r2 837 passed; r3 840 passed.

## 3. Modelo de idempotencia
- **Ámbito (strict):** clave compuesta `(consumer_id, tenant_id, operation, idempotency_key)` + `request_hash` del payload server-bound; tabla `idempotency_keys` (SQLite).
- **Estados soportados:** `in_progress`, `completed`, `recovery_required`, `failed`, `reconciling`.
- **Semántica API:** replay 200 si `completed` + hash igual + `response_json`; 409 `IDEMPOTENCY_CONFLICT` si hash distinto; 409 `IDEMPOTENCY_IN_PROGRESS` si en progreso; 409 `IDEMPOTENCY_RECOVERY_REQUIRED` si requiere recuperación.
- **Integridad:** en fallo de `complete()` tras ejecución, no se libera (evita duplicación); registro puede quedar bloqueado hasta reconciliación segura.

## 4. Correlación
- **Implementado:** contexto/tenant/consumer en stamping de decisión/auditoría (vías existentes), hash de request en idempotencia, `correlation_id` propagado en request/auditoría según rutas.
- **No implementado/demostrado:** correlación persistida fuerte e inequívoca `idempotency(operation key) ↔ decision_id/case_ref ↔ audit events/result` como fuente de verdad para reconciliación automática en todos los fallos; falta `operation_id` interno propagado end-to-end.

## 5. Máquina de estados
- **Transiciones prácticas:** reserva→`in_progress`; éxito→`completed`; fallo pre-complete con posible side-effect→retención `in_progress` (bloqueo); operador/herramienta→`recovery_required` (fail-closed) o `complete_reconciled`→`completed` solo con respuesta verificada provista.
- **No completado:** estados/transiciones formales completas para incertidumbre, lease/fencing/versionado, compare-and-swap de reconciliación concurrente, timeout sin liberación automática de ejecución.

## 6. Recuperación
- **Implementado (seguro por defecto):** `SQLiteIdempotencyStore` (`list_stale_in_progress`, `mark_recovery_required`, `complete_reconciled`, `release` solo `in_progress`), API fail-closed para estados de recuperación, pruebas de bloqueo/replay reconciliado sin re-ejecución.
- **CLI:** `scripts/reconcile_idempotency.py` — listar stale, marcar `recovery_required`, completar reconciliado **solo** con `--allow-unverified-response` y JSON provisto por operador (**riesgo reconocido**: no prueba por sí mismo correspondencia con decisión persistida; requiere verificación externa/evidencia). No libera para re-ejecución.
- **Brecha crítica (pendiente):** reconciliación basada en evidencia persistida verificable (recuperar resultado real desde repos/decision+audit) y rechazo de respuestas fabricadas/no correlacionadas; manejo de estado incierto, recovery concurrente, autorización/auditoría administrativa estructurada.

## 7. CLI y auditoría administrativa
- **CLI:** presente, fail-closed para complete sin flag explícita de riesgo, registra `recovery_actor/note/at` en registro de idempotencia.
- **No demostrado:** auditoría administrativa completa inmutable/estructurada (actor, consumer, tenant, operation, key protegida, estado anterior/posterior, motivo, resultado, correlation) accesible y protegida según política; controles de acceso a operaciones de reconciliación más allá de uso local controlado.

## 8. Migraciones
- **Alineado en esta sesión:** `sqlite_migrations.py` v2 actualizado para crear/asegurar columnas de recuperación en `idempotency_keys` (`recovery_note`, `recovery_actor`, `recovery_at`) e índice `idx_idem_status_updated` de forma idempotente; runtime stores también aseguran columnas.
- **Probado:** `tests/unit/test_sqlite_migrations.py` **3 passed** (upgrade v1→v2 en copia, downgrade en copia, idempotencia). Casos adicionales requeridos (DB nueva/versionada formal completa, fallo parcial, rollback operativo específico, compatibilidad exhaustiva con todas las versiones intermedias en campo) **no exhaustivos**.
- **Pendiente:** decisión/versionado formal si se requiere v3 dedicada para campos de recuperación/correlación; eliminar duplicidad semántica runtime↔formal donde proceda.

## 9. Fault injection A–G
| Escenario | Descripción | Estado | Evidencia |
|---|---|---|---|
| A | Antes de persistir decisión | No implementado | — |
| B | Decisión persistida, auditoría fallida | No implementado | — |
| C | Auditoría escrita, complete idempotencia fallido | **Mitigación parcial** | no-release en `app.py`; falta inyección determinista y verificación completa de estado/recuperación |
| D | Timeout después de persistir | No implementado | — |
| E | Error del provider | No implementado | — |
| F | Retry después de error/transitorio | Parcial | replay/conflicto/in-progress/recovery-required probados |
| G | Error al responder tras persistencia | No implementado | — |

- **Harness determinista:** no construido. Matriz de invariantes completa: **pendiente**.

## 10. Consistencia decisión/auditoría
- **Demostrado parcialmente:** denegaciones sin efectos de negocio en escenarios cubiertos; replay sin duplicar decisión/auditoría; transiciones HITL inválidas sin cambio/evento de negocio en caso probado.
- **No demostrado:** atomicidad/consistencia ante fallos parciales, recuperación coherente en todos los estados, ausencia de duplicados/eventos perdidos en todos los caminos.

## 11. Eventos CASE_RECEIVED
- **Hallazgo:** emitido en `TriageEngine.execute` y en `ReliabilityPipeline.run` (posible duplicación semántica por evaluación). Tests existentes verifican presencia, no unicidad.
- **Acción:** no modificado para evitar regresiones sin análisis de consumidores; **pendiente** decidir semántica/origen único o dedupe idempotente y ajustar pruebas.

## 12. HITL
- **Probado:** cross-context access/mutation → 404 sin efectos en propietario; transición inválida (reject desde approved forzado) → 400 sin cambio de lifecycle ni incremento de auditoría.
- **Pendiente:** matriz completa (pending/under-review/approve/reject/modify/escalate), transiciones permitidas/prohibidas/repetidas, concurrencia, actor server-derived y auditoría/efectos persistentes en todas las operaciones, retries.

## 13. SQLite
- **Demostrado:** suite 840 passed, idempotencia/integridad básica en escenarios controlados, repos con aislamiento por contexto.
- **No demostrado:** límites operativos completos bajo concurrencia sostenida, multi-proceso con garantías declaradas, `busy_timeout`/journal/locking tuning validado, escenarios de carrera HITL/recuperación.

## 14. Multi-proceso
- **Estado:** no ejecutado/demostrado. No se equiparan pruebas de threads con multi-proceso.

## 15. PostgreSQL
- **Entorno:** `psql` no disponible; Docker presente pero instancia PostgreSQL desechable **no levantada/validada** en esta sesión.
- **Estado:** no demostrado (transacciones, concurrencia, idempotencia compartida, multi-proceso). Preparación de scripts/tests de PoC: **pendiente**.

## 16. PoC shared experimental
- **Estado:** no ejecutada como shared real (misma app + misma persistencia compartida multi-consumer). PoCs previas = instancias/DB aisladas (no equivalentes). **Nivel C bloqueado/fail-closed**, no habilitado.

## 17. Wheel y Uvicorn
- **Wheel:** `case-1.0.0-py3-none-any.whl` construido e instalado en venv limpio temporal.
- **Smoke instalado fuera del repo:** `scripts/smoke_installed_wheel.py` desde directorio de trabajo externo → **EXIT 0**, `{"smoke":"ok","domains":5,"evaluate":"ok"}`; módulos (`case_api, case_core, case_infra, logistics_adapter, usgs_adapter`) desde `site-packages` de `%LOCALAPPDATA%\Temp\opencode\case-wheel-smoke\venv\...`
- **Uvicorn (instalado, fuera de repo, DB temporal):** arranque en `127.0.0.1:8765`, readiness/`/health` 200, `/domains` 5 dominios, `POST /api/v1/evaluate` mock OK, proceso detenido limpio (`PROC=stopped`). Stderr: warning upstream Starlette/httpx (no funcional).
- **Limitación:** prueba de mayor duración/carga y verificación exhaustiva de procesos huérfanos en escenarios largos no ejecutada.

## 18. Documentación
- **Actualizados:** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, informes en `docs/audits/*` (incluye este).
- **Pendiente:** alineación completa de `README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md`, `docs/CAPABILITY_AUDIT.md`, `docs/FUTURE_EVOLUTION.md`, `docs/MULTICONSUMER_SECURITY_HARDENING.md`, runbooks (`DEV_LOCAL`, `STRICT_SINGLE_CONSUMER`, `DEPLOYMENT_SECURE`) con recuperación, estados, reconciliación, límites SQLite/procesos, garantías reales/no demostradas.

## 19. ADR
- **Estado:** no creados/actualizados en esta sesión (carpeta `docs/adr/` preexistente sin nuevos ADRs requeridos añadidos). **Pendiente:** recuperación idempotente, correlación solicitud/decisión/auditoría, fallos parciales, transacciones/consistencia, límites SQLite, evolución PostgreSQL, shared multi-consumer.

## 20. Quality gates
- Ruff **PASS**, Mypy **PASS**, suite determinista **PASS (840)**, smoke wheel+uvicorn aislado **PASS**. Gates incompletos: fault injection A–G, HITL/concurrencia/multi-proceso/PostgreSQL exhaustivos, PoC shared real, revisión externa.

## 21. Auditoría interna
- Revisión focal aplicada (idempotencia anti-duplicación, recuperación fail-closed, endurecimiento CLI, aislamiento de tests, denegaciones sin efectos en cobertura realizada). **No** sustituye auditoría independiente completa ni security review externa.

## 22. Evaluación A–D
| Nivel | Estado | Evidencia | Bloqueadores |
|---|---|---|---|
| A — Local | **APTO CON RESERVAS** | ruff/mypy PASS, 840 tests, wheel+uvicorn smoke aislado PASS | docs/ADRs/runbooks no alineados; smoke prolongado/carga no realizado |
| B — Strict single-consumer | **APTO CON RESERVAS (no cerrado)** | authz/denegaciones sin efectos (cobertura realizada), idempotencia con replay/conflicto/bloqueo y recuperación básica, suite verde | correlación y recuperación basada en evidencia completa, fault injection A–G, HITL/concurrencia/multi-proceso exhaustivos, consistencia transaccional demostrada, revisión externa |
| C — Shared multi-consumer | **NO APTO (bloqueado)** | fail-closed, preparación parcial | aislamiento compartido real no demostrado, PostgreSQL/concurrencia/ataques cruzados, PoC misma app+DB, revisión seguridad |
| D — Producción | **NO APTO** | — | ops/DR/observabilidad/secretos/load, cierre B/C, aprobaciones |

## 23. Riesgos
| Sev | Riesgo | Acción |
|---|---|---|
| Alta | Reconciliación `complete` depende de respuesta provista por operador (flag) sin prueba automática de correspondencia con resultado persistido | implementar correlación fuerte y recuperación evidence-based; restringir/eliminar path no verificado |
| Alta | Fallos parciales A–G y atomicidad decisión/auditoría/idempotencia no demostradas | harness fault injection + invariantes + estrategia transaccional/reconciliación |
| Alta | Estados inciertos, lease/fencing y recuperación concurrente no resueltos | diseñar CAS/lease/versionado y pruebas |
| Media | Duplicación `CASE_RECEIVED`, HITL y concurrencia incompletos | análisis semántico + dedupe; matriz HITL; pruebas multi-proceso/SQLite |
| Media | PostgreSQL y shared PoC no validados | entorno desechable Docker/PostgreSQL + PoC experimental aislada |
| Alta | Sin revisión de seguridad independiente | paquete de evidencia y revisión externa |

## 24. Próximo hito
1. Correlación persistida end-to-end + recuperación evidence-based (sin completar por JSON no verificado) con pruebas de estados inciertos/concurrencia.  
2. Harness fault injection determinista A–G y matriz de consistencia.  
3. HITL completo + concurrencia SQLite/multi-proceso con límites declarados.  
4. PostgreSQL desechable + PoC shared experimental (misma app+DB) sin habilitar C.  
5. Alineación documental/ADRs y paquete de revisión externa.

## 25. Estado Git
- **Rama/HEAD:** `v4/portfolio-release` @ `b7021bb4316eec063633bbfdd99d1e0cb9164295` · tracking `origin/v4/portfolio-release`
- **Staged:** ninguno | **Operaciones:** sin commit/push/merge/PR/rebase/despliegue
- **Modificados (tracked):** `.env.example`, `pyproject.toml`, `render.yaml`, `scripts/smoke_installed_wheel.py`, `src/case_api/api/v1/app.py`, `src/case_api/api/v1/auth.py`, `src/case_core/application/engine.py`, `src/case_core/ports/{audit,decision_repository,repository}.py`, `src/case_core/reliability/pipeline.py`, `src/case_infra/persistence/{sqlite_adapter,sqlite_audit,sqlite_decision_repository,sqlite_idempotency,sqlite_migrations}.py`, `tests/integration/test_evaluate_contract.py`, `tests/integration/test_groq_live.py`, `tests/unit/{test_behavioral,test_bootstrap,test_persistence_roundtrip,test_reliability,test_security,test_sqlite,test_triage_engine}.py`
- **Untracked relevantes:** `src/case_api/api/v1/security.py`, `src/case_core/contracts/security.py`, `tests/conftest.py`, `tests/integration/{test_denial_effects,test_evaluate_security,test_idempotency_recovery,test_multiconsumer_isolation_poc,test_strict_authz_matrix,test_strict_integrity_e2e}.py`, `tests/unit/test_sqlite_migrations.py`, `scripts/{migrate_case_sqlite,reconcile_idempotency}.py`, `docs/{AUTHZ_MATRIX_ENDPOINT_SCOPE,MULTICONSUMER_SECURITY_HARDENING,RUNBOOK_*}.md`, `docs/adr/`, `docs/audits/`, `docs/prompts/`, `AGENTS.md.backup`, `pytest_case.txt`, `src/pytest_case.txt`, `src/pytest_output.txt`
- **Ignorados relevantes (no modificados por esta sesión):** `build/`, `dist/`, `src/case.egg-info/` (si presentes)

**Confirmación:** no se realizó publicación ni despliegue; no se habilitó Nivel C/D.
