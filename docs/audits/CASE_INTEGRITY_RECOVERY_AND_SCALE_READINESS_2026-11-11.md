# CASE — Integrity, Recovery & Scale Readiness (Strict Single-Consumer)

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `v4/portfolio-release`  
**HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` (sin commits nuevos; working tree preservado)

> Informe de continuidad técnica. No sobrescribe auditorías previas. **Sin commit/push/merge/PR/despliegue. C y D no habilitados.** Evidencia local/aislada; revisión de seguridad externa pendiente.

---

## A. Diagnóstico ejecutivo
- **Avance real:** baseline determinista completa recuperada y verde (**840 passed, 0 failed, 0 skipped**), corrección de contaminación de tests, endurecimiento de integridad idempotente (no liberar `in_progress` en fallo de `complete`), mecanismo inicial de recuperación/reconciliación fail-closed (estados `recovery_required/failed/reconciling`, tooling CLI, bloqueo API, pruebas), pruebas de efectos de denegación sin side-effects (17 rutas) e integridad E2E parcial (replay/conflicto/in-progress, IDOR/HITL básico), smoke de wheel instalado fuera del repo en venv limpio (**EXIT 0**, módulos desde `site-packages`).
- **No cerrado:** recuperación idempotente completa (lease/fencing, correlación fuerte operación↔resultado, reconciliación automática segura, todos los casos/incertidumbres), fault injection determinista **A–G** completo con invariantes, consistencia decisión/auditoría/idempotencia ante todos los fallos parciales, matriz HITL exhaustiva y concurrencia, validación multi-proceso/PostgreSQL, arranque Uvicorn prolongado desde wheel instalado, alineación documental/ADR completa, PoC shared multi-consumer real (misma app+DB), revisión independiente de seguridad.
- **Nivel B:** progreso sustancial con reservas; **no** declarado plenamente APTO por pendientes críticos. **C/D:** NO APTO.

## B. Suite y baseline
| Gate | Comando | Resultado | Evidencia |
|---|---|---|---|
| Ruff | `ruff check src tests scripts/reconcile_idempotency.py` | **PASS** | All checks passed (2026-11-11) |
| Mypy | `mypy src --ignore-missing-imports` | **PASS** | 102 source files |
| Suite determinista completa (no-live) | `pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **840 passed, 0 failed, 0 skipped** (84.85s) | `docs/audits/pytest_deterministic_full_2026-11-11_r3.txt` |
| Focalizados (seguridad/integridad/recuperación/migraciones) | `pytest tests/integration/test_idempotency_recovery.py tests/integration/test_strict_integrity_e2e.py tests/integration/test_evaluate_security.py tests/integration/test_denial_effects.py tests/unit/test_sqlite_migrations.py -q` | **30 passed** | ejecución local (3+5+15+4+3) |

Notas: suite r1 (`pytest_deterministic_full_2026-11-11.txt`) tuvo 8 fallos por contaminación (`CASE_DB_PATH`/estado global de `appmod`); corregido con `save/restore` en helpers de tests nuevos. r2 (`..._r2.txt`) 837 passed tras fix de aislamiento; r3 incluye +3 tests de recuperación.

## C. Recuperación idempotente

### Implementado
- **Estados soportados (almacenamiento/API):** `in_progress`, `completed`, `recovery_required`, `failed`, `reconciling` (extensión aditiva; columnas `recovery_note/recovery_actor/recovery_at` auto-migradas en store).
- **Comportamiento API (strict `/api/v1/evaluate`):** replay solo si `completed` + hash coincide + `response_json`; conflicto 409 si hash difiere; 409 `IDEMPOTENCY_IN_PROGRESS` si `in_progress`; 409 `IDEMPOTENCY_RECOVERY_REQUIRED` si `recovery_required/failed/reconciling`. En fallo de `complete()` tras ejecución: **no release** (anti-duplicación) → permanece bloqueado.
- **Store:** `list_stale_in_progress`, `mark_recovery_required`, `complete_reconciled` (requiere respuesta verificada provista por operador; no re-ejecuta negocio). `release` solo elimina `in_progress`.
- **Herramienta operativa:** `scripts/reconcile_idempotency.py` (listar stale, marcar `recovery_required` fail-closed, completar reconciliado con `--response-json` verificado; uso controlado, no producción sin backup/autorización).
- **Pruebas:** `tests/integration/test_idempotency_recovery.py` — bloqueo sin duplicación en `recovery_required`; marcado de stale→`recovery_required`; replay tras `complete_reconciled` sin re-ejecución (3 tests PASS).

### Limitaciones / no demostrado
- No existe correlación persistida fuerte idempotency↔`decision_id/case_ref` en el registro para probar automáticamente “ejecutado y persistido” en todos los fallos; reconciliación automática segura **no implementada**.
- Sin lease/heartbeat/fencing/versionado para recuperación concurrente; sin endpoint admin protegido; sin auditoría estructurada de intervención en tabla dedicada.
- Casos A/B/C (distinción completa no-ejecutado/ejecutado/incertidumbre) y recuperación concurrente/autorizada por contexto **no cubiertos exhaustivamente** por fault injection.
- `sqlite_migrations.py` (versionado formal) no actualizado explícitamente para nuevas columnas de idempotencia (el store las añade en runtime); pendiente alinear migración formal.

## D. Fault injection A–G
| Escenario | Fallo | Estado | Resultado |
|---|---|---|---|
| A | Antes de persistir decisión | No implementado | **No demostrado** |
| B | Decisión persistida, auditoría fallida | No implementado | **No demostrado** |
| C | Auditoría escrita, finalización idempotencia fallida | Parcial | **Mitigado** (no-release evita duplicación; falta inyección determinista + verificación de estado/recuperación completa) |
| D | Timeout después de persistir | No implementado | **No demostrado** |
| E | Error del provider | No implementado | **No demostrado** |
| F | Retry después de error | Parcial | Replay/conflicto/in-progress/recovery-required probados en escenarios controlados; falta inyección de fallo transitorio completo |
| G | Error al responder tras persistencia | No implementado | **No demostrado** |

Harness determinista de inyección: **no construido**.

## E. Consistencia de decisión y auditoría
- **Observado:** engine emite `CASE_RECEIVED` y `pipeline.run` también emite `CASE_RECEIVED` (posible duplicación semántica); operaciones de decisión/auditoría/idempotencia en conexiones/instancias separadas (sin atomicidad cross-operación demostrada incluso en mismo fichero SQLite por defecto).
- **Demostrado parcialmente:** denegaciones sin efectos de negocio en rutas/escenarios cubiertos; replay sin duplicar decisiones/auditorías; HITL inválido sin cambio de estado ni evento HITL de negocio en caso probado.
- **Pendiente:** deduplicación/semántica de eventos, invariantes completos ante fallos parciales, trazabilidad actor/contexto/correlation en todos los caminos.

## F. HITL
- **Probado:** acceso/mutación cross-contexto → 404 sin efectos en propietario; transición inválida (reject desde approved forzado) → 400 sin cambio de lifecycle ni incremento de auditoría.
- **Pendiente:** matriz completa pending/under-review/approve/reject/modify/escalate (permitidas, inválidas, repetidas, concurrentes) con aserciones de DB+auditoría+actor server-derived, retries y ownership en todas las operaciones.

## G. SQLite, concurrencia y procesos
- **SQLite:** suite determinista verde; pruebas de integridad/idempotencia en procesos/threads limitados (previas/parciales). Límites operativos (workers/procesos, locking, journal/busy_timeout, transacciones) **no revalidados exhaustivamente** en esta sesión.
- **Multi-proceso:** **no demostrado**.
- **Configuración recomendada (provisional, no plenamente demostrada):** strict single-consumer, instancia aislada, evitar asumir multi-worker/multi-proceso hasta evidencia.

## H. PostgreSQL y evolución shared
- **PostgreSQL:** `psql` no disponible en entorno; Docker presente pero no se levantó/validó instancia desechable PostgreSQL en esta sesión. **No demostrado.**
- **Modelo/arquitectura shared (diseño, no implementado/activado):** identidad diferenciada consumer/tenant/org/actor, `SecurityContext` no global-mutable, persistencia compartida con aislamiento en capa de datos (constraints/índices/filtros/ownership, evaluación RLS como defensa en profundidad), idempotencia/auditoría/HITL particionadas, transacciones y concurrencia demostrada, PoC en misma app+misma DB.
- **PoC shared real:** **no ejecutada** (las PoCs previas son instancias/DB aisladas, no equivalentes a Nivel C). Nivel C permanece **fail-closed/bloqueado**.

## I. Wheel y Uvicorn
- **Build:** `python -m pip wheel . -w <tmp> --no-deps` → `case-1.0.0-py3-none-any.whl` creado.
- **Instalación aislada:** venv limpio en `%LOCALAPPDATA%\Temp\opencode\case-wheel-smoke`, instalación del wheel + dependencias OK.
- **Smoke fuera del repo:** ejecutado desde directorio temporal de trabajo externo con `scripts/smoke_installed_wheel.py` → **EXIT 0**, `{"smoke":"ok","domains":5,"evaluate":"ok"}`.
- **Imports verificados (site-packages del venv):** `case_api`, `case_core`, `case_infra`, `logistics_adapter`, `usgs_adapter` en `...\\case-wheel-smoke\\venv\\Lib\\site-packages\\...`
- **Limitación:** stderr mostró `StarletteDeprecationWarning` (httpx/testclient upstream), sin fallo funcional; **arranque Uvicorn prolongado** (readiness loop, request HTTP real, shutdown limpio, verificación sin procesos huérfanos) **no ejecutado** en esta sesión.

## J. Documentación y ADR
- **Actualizados:** `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md` (efectos de denegación e integridad E2E parcial).
- **Creados/actualizados (auditoría/evidencia):** `docs/audits/CASE_FINAL_SINGLE_CONSUMER_INTEGRITY_CLOSURE_2026-11-11.md`, `docs/audits/CASE_SCALING_AND_INTEGRITY_EVOLUTION_2026-11-11.md`, `docs/audits/CASE_INTEGRITY_RECOVERY_AND_SCALE_READINESS_2026-11-11.md`, `docs/audits/pytest_deterministic_full_2026-11-11_r{1,2,3}.txt`.
- **Pendiente:** ADRs específicos (recuperación idempotencia, consistencia decisión/auditoría, límites SQLite, evolución PostgreSQL, arquitectura shared), alineación completa de README/ARCHITECTURE/ROADMAP/CAPABILITY_AUDIT/FUTURE_EVOLUTION y runbooks (recuperación, estados, reconciliación, límites, garantías/no-garantías).

## K. Cambios exactos (esta sesión, sobre working tree preservado)
- `src/case_api/api/v1/app.py` — no-release en fallo de `complete`; manejo explícito 409 para `recovery_required/failed/reconciling`.
- `src/case_infra/persistence/sqlite_idempotency.py` — estados de recuperación, columnas/índices de soporte, `mark_recovery_required`, `complete_reconciled`, `list_stale_in_progress`, guards de `release`.
- `scripts/smoke_installed_wheel.py` — aislamiento de imports y reporte de paths.
- `scripts/reconcile_idempotency.py` — **nuevo** (CLI de reconciliación fail-closed).
- `tests/integration/test_denial_effects.py`, `tests/integration/test_strict_integrity_e2e.py`, `tests/integration/test_idempotency_recovery.py` — **nuevos** (con restore de entorno/estado).
- `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, informes/evidencias en `docs/audits/*` indicados.
- (Preexistentes en working tree: hardening/archivos previos listados en `git status`; no revertidos.)

## L. Quality gates
- ruff: **PASS** | mypy: **PASS** | suite determinista completa: **PASS (840)** | wheel smoke aislado fuera de repo: **PASS (EXIT 0)**.
- Gates no completados: fault injection A–G, HITL/concurrencia exhaustiva, multi-proceso, PostgreSQL, Uvicorn prolongado, PoC shared real, revisión externa.

## M. Evaluación A–D
| Nivel | Estado | Evidencia | Bloqueadores |
|---|---|---|---|
| A — Local | **APTO CON RESERVAS** | ruff/mypy PASS, 840 passed, smoke wheel instalado fuera de repo PASS, fixes de integridad | docs/runbooks/ADRs no alineados; Uvicorn prolongado no revalidado |
| B — Strict single-consumer | **APTO CON RESERVAS (no cerrado)** | denegaciones sin efectos (17 rutas), replay/conflicto/in-progress/recovery-required sin duplicación en casos probados, reconciliación básica/tooling, suite verde | recuperación completa/incertidumbre/lease, fault injection A–G, HITL y concurrencia exhaustivos, consistencia transaccional/atomicidad no demostrada, revisión externa |
| C — Shared multi-consumer | **NO APTO (bloqueado)** | fail-closed, diseño parcial | aislamiento compartido real no demostrado (misma app+DB), PostgreSQL/concurrencia/multi-proceso, ataques cruzados, revisión seguridad |
| D — Producción | **NO APTO** | — | ops/DR/observabilidad/load/secretos, cierre B/C, aprobaciones |

## N. Riesgos restantes
| Sev | Riesgo | Acción |
|---|---|---|
| Alta | Registros `in_progress/recovery_required` sin reconciliación automática segura ni correlación fuerte a resultado | modelar estados/lease/fencing, persistir referencia de resultado, pruebas de incertidumbre y recuperación concurrente |
| Alta | Fallos parciales A–G y atomicidad decisión/auditoría/idempotencia no demostradas | harness fault injection + matriz de invariantes + estrategia transaccional/reconciliación documentada |
| Media | Duplicación semántica `CASE_RECEIVED` y cobertura HITL/concurrencia incompleta | auditar emisores, deduplicar si aplica, completar matriz HITL y pruebas multi-proceso/SQLite |
| Media | Uvicorn prolongado y PostgreSQL no validados | smoke uvicorn aislado; PoC PostgreSQL desechable local si disponible |
| Alta | C bloqueado y sin revisión externa | PoC shared real experimental aislada + paquete de evidencia para security review |

## O. Próximo hito
1. Recovery completa y segura (correlación resultado, reconciliación idempotente, lease/fencing, pruebas de estados inciertos/concurrencia/autorización).  
2. Fault injection A–G determinista + matriz de consistencia decisión/auditoría/idempotencia/respuesta.  
3. HITL exhaustivo + concurrencia SQLite/multi-proceso con límites declarados.  
4. Uvicorn smoke aislado + alineación documental/ADRs + PoC PostgreSQL/shared experimental (sin habilitar C).

## P. Estado Git final
- **Rama:** `v4/portfolio-release` | **HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295` | **Tracking:** `origin/v4/portfolio-release` | **Staged:** ninguno.
- **Modificados:** `.env.example`, `pyproject.toml`, `render.yaml`, `scripts/smoke_installed_wheel.py`, `src/case_api/api/v1/app.py`, `src/case_api/api/v1/auth.py`, `src/case_core/application/engine.py`, `src/case_core/ports/{audit,decision_repository,repository}.py`, `src/case_core/reliability/pipeline.py`, `src/case_infra/persistence/{sqlite_adapter,sqlite_audit,sqlite_decision_repository,sqlite_idempotency}.py`, `tests/integration/test_evaluate_contract.py`, `tests/integration/test_groq_live.py`, `tests/unit/{test_behavioral,test_bootstrap,test_persistence_roundtrip,test_reliability,test_security,test_sqlite,test_triage_engine}.py`.
- **Untracked relevantes:** `src/case_api/api/v1/security.py`, `src/case_core/contracts/security.py`, `src/case_infra/persistence/sqlite_migrations.py`, `tests/conftest.py`, `tests/integration/{test_denial_effects,test_evaluate_security,test_idempotency_recovery,test_multiconsumer_isolation_poc,test_strict_authz_matrix,test_strict_integrity_e2e}.py`, `tests/unit/test_sqlite_migrations.py`, `scripts/{migrate_case_sqlite,reconcile_idempotency}.py`, `docs/{AUTHZ_MATRIX_ENDPOINT_SCOPE,MULTICONSUMER_SECURITY_HARDENING,RUNBOOK_DEPLOYMENT_SECURE,RUNBOOK_DEV_LOCAL,RUNBOOK_STRICT_SINGLE_CONSUMER}.md`, `docs/adr/`, `docs/audits/`, `docs/prompts/`, `AGENTS.md.backup`, `pytest_case.txt`, `src/pytest_case.txt`, `src/pytest_output.txt`.
- **Confirmación:** no se realizó commit, push, merge, PR ni despliegue.
