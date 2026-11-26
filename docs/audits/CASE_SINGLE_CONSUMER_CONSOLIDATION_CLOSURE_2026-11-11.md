# CASE — Informe de consolidación single-consumer y auditoría final

**Fecha:** 2026-11-11  
**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Rama:** `juan/ciclo4-consolidacion-case` — **HEAD:** `b7021bb4316eec063633bbfdd99d1e0cb9164295`  
**Alcance:** consolidación y cierre de la base **single-consumer** (Nivel A/B según evidencia). Sin commit/push/merge/rebase/PR/deploy. Estado real preservado.

## 1. Entorno soportado (objetivo de esta etapa)

**Soportado (declarado y verificado en la medida indicada):**
- **Un consumidor** autorizado, **una instancia** CASE, **un proceso** de aplicación.
- **SQLite** como persistencia (`decisions`/`audit_events`/`idempotency_keys` en DB de decision/audit; stores defensivos).
- **Recuperación administrativa controlada** con **un único reconciliador activo** (CLI fail-closed, basada en evidencia persistida verificada; sin fabricación/liberación automática incierta).
- **Sin ejecución irreversible no autorizada** (modos/controles implementados; fail-closed en strict).
- **Sin modo shared ni soporte multi-worker declarado**. No se anuncian garantías de concurrencia distribuida/multi-proceso.

**Restricciones operativas (no garantías técnicas completas):** SQLite con límites de locking/concurrencia; aislamiento compartido multi-consumidor y multi-proceso **no demostrado**; coherencia total en todos los fallos/caminos **no demostrada** fuera de escenarios cubiertos.

## 2. Estado Git (inicio y fin de verificación)

- **Inicio (ciclo actual):** rama `juan/ciclo4-consolidacion-case`, HEAD `b7021bb` (`b7021bb4316eec063633bbfdd99d1e0cb9164295`), working tree sucio (modificados rastreados + untracked previos y del ciclo), sin staging.
- **Fin:** **sin cambios de rama/HEAD/staging**; no se ejecutaron operaciones git destructivas ni de publicación. El working tree permanece sucio con los mismos cambios preservados más artefactos/evidencia generados en este ciclo (tests, docs/audits, scripts, código de consolidación). **No commiteado, no pusheado.**

## 3. Evidencia de quality gates (ejecutada y conservada)

| Gate | Resultado | Evidencia |
|---|---|---|
| `python -m ruff check src tests scripts/reconcile_idempotency.py` | **PASS** (All checks passed) | ejecución 2026-11-11 |
| `python -m mypy src --ignore-missing-imports` | **PASS** (Success: no issues found in 103 source files) | ejecución 2026-11-11 |
| `python -m pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py` | **PASS — 857 passed, 0 failed, 0 skipped** (86.81s) | `docs/audits/pytest_deterministic_full_2026-11-11_r7.txt` |

## 4. Cierre de fallos críticos (harness existente) — B, D, F

Ejecutados en `tests/integration/test_fault_injection_ag.py` (suite determinista, DB SQLite temporal aislada, hooks test-only `CASE_TEST_FAULT_INJECTION=1`):

| Escenario | Cobertura | Decisión/Caso | Auditoría | Idempotencia | operation_id | Duplicación | Retry/Recuperación | Estado |
|---|---|---|---|---|---|---|---|---|
| **B** Decisión persistida y fallo al escribir auditoría (post-persist) | Hook tras persistencia arma fallo de audit write | **1** decisión persistida | fallo inyectado post-persist; sin duplicado | sin completado indebido; retry sin duplicar | presente en flujo | **No** (=1) | retry seguro (200/409 según estado) | **Cubierto (escenario controlado)** |
| **D** Interrupción después de persistir y antes de devolver respuesta | Hook tras `complete` idempotency (efectos persistidos) antes de retorno | **≤/==1** | coherente con efectos previos | completada; replay coherente | presente | **No** | retry/replay **200** con estado coherente | **Cubierto (escenario controlado)** |
| **F** Fallo transitorio seguido de retry | Provider falla 1ª llamada y éxito en 2ª, misma operación idempotente | **≤1** | sin duplicados observados | sin duplicación por retry | presente en flujo | **No** | retry controlado (200/409/422/500 según resultado) | **Cubierto (escenario controlado)** |

También preservados/cubiertos: **A** (antes de persistir, 0→retry sin duplicar), **C** (fallo en complete, sin duplicar, recovery), **E** (fallo proveedor antes de decisión válida, 0 decisiones), **G** (error antes de retorno tras persistir, sin duplicar). Evidencia: 7 tests PASS en `test_fault_injection_ag.py`.

> Nota: invariantes exhaustivas (conteos/eventos por tipo en todos los puntos, multiproceso, todos los caminos de auditoría) no se reclaman como completas más allá de lo observado en estos escenarios.

## 5. HITL — cierre funcional (single-consumer)

**Implementado (cambios de consolidación):** validación de transiciones y protección contra sobrescritura silenciosa en actualizaciones de ciclo de vida (CAS por `expected_lifecycle`/estado actual en repositorio y endpoints), guardas para `modify` desde estados finales/concurrentes, rechazo con 409 en conflicto concurrente observado.

**Probado (`tests/integration/test_hitl_functional.py`, 4 PASS):**
- Transiciones permitidas (p.ej. `ai_proposed → under_review → approved`) con auditoría HITL registrada.
- Transiciones prohibidas y repetición sin efectos adicionales (estado estable, sin nuevos eventos HITL).
- Actor/ámbito no autorizado (scope insuficiente 401/403) y **contexto ajeno** (404 por aislamiento, sin modificación).
- **Dos acciones incompatibles simultáneas** sobre la misma decisión: exactamente 1 éxito (200) y la otra rechazada (400/409), estado final consistente (`approved|rejected`), sin doble éxito silencioso (CAS).

**Reserva:** exhaustividad completa de todas las combinaciones de actores/estados/reintentos y coordinación distribuida no demostrada; se declara protección necesaria para single-consumer, no infraestructura distribuida.

## 6. Recuperación e idempotencia (coherencia)

**Conservado y verificado en suites existentes:**
- Recuperación desde `response_json` persistido verificado y reconstrucción determinista desde decisión+auditoría con `request_context` almacenado (cuando la evidencia es suficiente).
- Rechazo de respuestas aportadas manualmente / completado no verificado (`--complete` rechazado; `complete_reconciled` no permitido).
- Bloqueo fail-closed cuando la evidencia es insuficiente o incierta; sin liberación automática de operaciones inciertas.
- Protección contra reejecución y duplicaciones en escenarios cubiertos (integridad/fault-injection/recovery).
- CLI y API con comportamiento coherente de fail-closed/recovery en los caminos soportados (evidencia por tests y diseño actual).

## 7. Migraciones SQLite (v1–v5)

**Verificado (`tests/unit/test_sqlite_migrations.py`, 6 PASS):**
- Cadena formal aditiva `upgrade(1..5)` idempotente y preservación de registros/columnas/índices requeridos (decisions/audit/idempotency, correlación, `request_context_json`).
- Base nueva, versiones anteriores con datos representativos (v2/v3/v4) migradas a v5, migración repetida.
- Inicialización correcta de repositorios tras migrar (decision/audit/idempotency operativos).

**Notas:** `scripts/migrate_case_sqlite.py` es un helper legacy para columnas de contexto (no ejecuta la cadena completa v3–v5); la ruta formal recomendada es `case_infra.persistence.sqlite_migrations.upgrade(db_path, 5)` (idempotente, in-place, no destructivo). Downgrade solo en copia (`downgrade_on_copy`).

## 8. Packaging y ejecución real (wheel + Uvicorn)

**Revalidado (2026-11-11):**
1. Build wheel: `python -m build --wheel` → `case-1.0.0-py3-none-any.whl` generado. **OK**
2. Instalación en venv limpio (temporal). **OK**
3. Ejecución fuera del checkout, imports desde `site-packages` (`case_api/case_core/case_infra/logistics_adapter/usgs_adapter`). **OK** (smoke)
4. Uvicorn sobre app instalada, DB SQLite temporal: **/health 200, /domains 200 (5 dominios), /api/v1/evaluate mock 200 `status=ok`**. **OK**
5. Shutdown limpio, **sin procesos huérfanos**, `SMOKE_EXIT=0` / `OVERALL_OK=True`. **OK**

Sin bases de datos reales.

## 9. Documentación actualizada (mínima necesaria)

- `docs/RUNBOOK_STRICT_SINGLE_CONSUMER.md`: entorno soportado explícito (1/1/1), reconciliador único, migración formal a v5, coherencia API/CLI, límites y no-garantías.
- `docs/audits/CASE_FAULT_INJECTION_MATRIX.md`: matriz A–G con resultados B/D/F/A/C/E/G cubiertos en escenarios controlados y reservas.
- `docs/audits/pytest_deterministic_full_2026-11-11_r7.txt`: evidencia suite completa.
- Este informe: consolidación, evidencia, configuración soportada, operación/recuperación, límites SQLite, instalación/ejecución y auditoría final.

## 10. Auditoría final (revisión única)

| Hallazgo / área | Clasificación | Justificación / evidencia |
|---|---|---|
| Seguridad de evaluate (authz/scopes/contexto server-derived, fail-closed strict) | **Reserva aceptada y documentada** | Cobertura verificada en suites de seguridad/integridad/denegación (matrices y efectos); no se reclama exhaustividad total en todos los caminos/adaptadores. |
| Idempotencia y recuperación (anti-dup, replay/conflict/in-progress, evidence-based, sin fabricación) | **Reserva aceptada y documentada** | Probado en `test_idempotency_recovery`, `test_strict_integrity_e2e`, fault injection; clasificación completa de todos los estados/ausencia de efectos no demostrada exhaustivamente. |
| Correlación operación–decisión–auditoría (`operation_id`, propagación/persistencia) | **Reserva aceptada y documentada** | Implementada y ejercitada en flujos cubiertos; correlación transaccional/inequívoca en **todos** los fallos/caminos no demostrada. |
| HITL (transiciones, repetición, scope/contexto, concurrencia incompatible, sin overwrite silencioso) | **Reserva aceptada y documentada** | Cierre funcional single-consumer demostrado con CAS/guardas y tests; matriz exhaustiva de todas las combinaciones/distribuida no demostrada. |
| Persistencia SQLite y consistencia en escenarios cubiertos | **Reserva aceptada y documentada** | Comportamiento correcto en pruebas deterministas; locking/concurrencia multi-proceso no validada. |
| Migraciones v1–v5 (cadena, datos, idempotencia, init repos) | **Reserva aceptada y documentada** | Verificado por tests; interrupción/fallo parcial en todos los entornos operativos no ejercitado; helper legacy `scripts/migrate_case_sqlite.py` no cubre v3–v5. |
| Packaging / instalación / Uvicorn / smoke fuera de repo | **Reserva aceptada y documentada** | Revalidado OK en venv limpio/DB temporal (mock); no implica validación productiva/externa. |
| Compatibilidad de contratos | **Reserva aceptada y documentada** | Cambios aditivos y suites contractuales deterministas en verde; compatibilidad con consumidores externos reales no re-certificada. |
| Configuración soportada (single-consumer, strict fail-closed, sin shared/multi-worker) | **Reserva aceptada y documentada** | Alineada en runbook/config; imposición técnica de “un proceso/un reconciliador” es parcialmente operativa (política/procedimiento). |
| Multi-proceso/SQLite bajo carga, PostgreSQL, shared multi-consumer, producción distribuida | **Evolución futura** | Fuera del entorno soportado; no demostrado ni habilitado. |
| Observabilidad/DR/load/secret rotation/revisión seguridad independiente/deploy | **Evolución futura** | No ejecutado; requiere fase/infra/aprobaciones posteriores. |

**Bloqueantes para el entorno single-consumer:** **ninguno identificado** en los flujos y controles críticos cubiertos por la evidencia anterior (gates en verde, B/D/F/HITL/migraciones/packaging revalidados). Riesgos remanentes tratados como reservas aceptadas/documentadas o evolución futura.

## 11. Criterio de finalización

Se declara la **base single-consumer consolidada (Nivel A/B con reservas documentadas)** porque: flujos críticos probados (incl. B,D,F,HITL funcional), sin duplicación en fallos cubiertos, recuperación basada en evidencia verificable, HITL sin transiciones incompatibles por concurrencia en escenarios probados (CAS), migraciones v1–v5 preservan datos en pruebas, wheel y Uvicorn funcionan fuera del checkout, ruff/mypy/suite determinista pasan, documentación coherente para el entorno soportado y limitaciones declaradas.

**No se declara:** cierre total sin reservas, Nivel C (shared multi-consumer) ni Nivel D (producción). Integración en primera fase controlada con POOLAR: **preparación técnica razonable dentro del entorno single-consumer soportado, sujeta a reservas y controles operativos documentados**.
