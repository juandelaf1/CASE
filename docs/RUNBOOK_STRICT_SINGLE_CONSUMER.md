# Runbook — Strict single-consumer (CASE)

**Estado:** Consolidado para **Nivel B (single-consumer estricto) con reservas documentadas**. Shared multi-consumer **NO APTO / bloqueado fail-closed**. No producción distribuida.

## Entorno soportado (declarado)
- **1 consumidor** autorizado, **1 instancia** CASE, **1 proceso** de aplicación.
- **SQLite** como persistencia.
- **Recuperación administrativa controlada** con **un único reconciliador activo**.
- **Sin ejecución irreversible no autorizada**. **Sin modo shared ni soporte multi-worker declarado**.

> Limitaciones de concurrencia/locking SQLite y coordinación distribuida **no se anuncian como garantías**; operar bajo estas restricciones.

## Configuración mínima (fail-closed)
- `CASE_SECURITY_MODE=shared` (o `prod`)
- `CASE_API_KEY=<secreto>` **obligatorio** (o `CASE_API_KEYS` con **un solo** consumidor)
- `CASE_CONSUMER_ID=<id>`
- `CASE_TENANT_ID=<tenant>` (recomendado)
- `CASE_API_SCOPES=<scopes mínimos necesarios>` (ej. `case:evaluate,case:read,case:hitl:write,case:decision:read,case:audit:read,...`)

**Arranque rechazado (por diseño):** sin credenciales en strict, múltiples consumidores/tenants en strict, o configuraciones que impliquen aislamiento no demostrado.

## Comportamiento esperado
- Rutas de negocio requieren credenciales válidas; `/health` exenta (revisar exposición en despliegues).
- Scopes verificados server-side en strict; identidad/contexto derivados del servidor (no confiables desde payload).
- Persistencia/auditoría: stamping y filtrado por contexto; accesos fuera de contexto → 404 en objetos protegidos (sin leak de existencia).
- `/api/v1/evaluate`: idempotencia compuesta `(consumer,tenant,operation,key)` con replay/conflicto/in-progress/recovery en strict.
- HITL: transiciones validadas con protección contra sobrescritura silenciosa por concurrencia (CAS) en el alcance single-consumer; acciones incompatibles no deben ambas tener éxito.

## Recuperación e idempotencia (coherente API/CLI)
- Recuperación **solo** desde evidencia persistida verificada (`response_json` persistido) o reconstrucción determinista desde decisión+auditoría con contexto almacenado, cuando sea suficiente.
- **No** se aceptan respuestas aportadas manualmente; CLI `--complete` rechazado. Bloqueo fail-closed si la evidencia es insuficiente.
- No liberar automáticamente operaciones inciertas. Mantener **un único reconciliador activo**.
- CLI: `--inspect`, `--list-stale`, `--mark-recovery-required`, `--complete-from-evidence` (`scripts/reconcile_idempotency.py`).

## Migraciones SQLite (decision/audit/idempotency DB)
- Backup/copia obligatoria antes de operar sobre datos existentes.
- **Ruta formal (v1→v5, aditiva, idempotente, in-place):**  
  `python -c "from case_infra.persistence.sqlite_migrations import upgrade; print(upgrade('case_audit.db', 5))"`
- `scripts/migrate_case_sqlite.py` es helper legacy (columnas de contexto) y **no** reemplaza la cadena completa v3–v5; preferir el módulo formal anterior.
- Downgrade **solo en copia** (best-effort, rebuild v1): `downgrade_on_copy(copy_path, 1)`. No ejecutar downgrade en DB real sin autorización/respaldo.
- Validar post-migración sobre copia (`tests/unit/test_sqlite_migrations.py`, conteos/integridad, init de repositorios).

## Verificación recomendada (antes de uso controlado)
- Gates: `python -m ruff check src tests scripts/reconcile_idempotency.py`, `python -m mypy src --ignore-missing-imports`, suite determinista no-live:  
  `python -m pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py`
- Seguridad/integridad/HITL/migraciones según necesidad: `tests/integration/test_evaluate_security.py`, `test_denial_effects.py`, `test_strict_authz_matrix.py`, `test_strict_integrity_e2e.py`, `test_idempotency_recovery.py`, `test_fault_injection_ag.py`, `test_hitl_functional.py`, `tests/unit/test_sqlite_migrations.py`.
- Revisar `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`, `docs/MULTICONSUMER_SECURITY_HARDENING.md`, `docs/audits/CASE_SINGLE_CONSUMER_CONSOLIDATION_CLOSURE_2026-11-11.md`.

## Límites y no-garantías
- SQLite: concurrencia multi-proceso/bajo carga, `SQLITE_BUSY` en contención y comportamiento distribuido **no validados**.
- Correlación/recovery/HITL/faults: demostrados en escenarios cubiertos; **no** se reclama exhaustividad total de caminos/fallos ni garantías distribuidas.
- **No habilita shared multi-consumer, multi-worker ni producción**. Revisión independiente de seguridad y gates operativos externos pendientes.
