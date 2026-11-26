# CASE — Ciclo 4: plan de ejecución y consolidación

**Rama de trabajo:** juan/ciclo4-consolidacion-case  
**Base:** 4/portfolio-release @ b7021bb + cambios locales en curso (no consolidados)  
**Fecha:** 2026-11-11  
**Autor de rama:** Juan  

> Documento operativo para ejecutar el Ciclo 4 en incrementos verificables. No habilita multi-consumidor compartido ni declara producción.

## 0. Estado inicial observado (inventario rápido)

- **Rama actual:** juan/ciclo4-consolidacion-case.
- **Working tree:** múltiples archivos modificados y sin seguimiento (hardening auth/context/persistencia, tests de seguridad/integridad, docs/runbooks/matriz, scripts de migración). Evidencia de avance parcial de Ciclos 2-3 aún no consolidado en commit limpio.
- **Artefactos ya presentes:** docs/MULTICONSUMER_SECURITY_HARDENING.md, docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md, docs/adr/ADR-CASE-MC-001-deployment-and-isolation-strategy.md, docs/RUNBOOK_{DEV_LOCAL,STRICT_SINGLE_CONSUMER,DEPLOYMENT_SECURE}.md, scripts/migrate_case_sqlite.py, tests 	est_strict_authz_matrix.py, 	est_denial_effects.py, 	est_strict_integrity_e2e.py, 	est_multiconsumer_isolation_poc.py, 	est_sqlite_migrations.py, etc.
- **Gates declarados en docs:** integración no-live y pruebas de seguridad/migraciones parciales en verde (según hardening/matriz/runbook); reproducción completa en este entorno **pendiente de registrar** con comando, commit y resultado (ver §7).

## 1. Mapa Ciclo 4 → estado, brechas y evidencia requerida

| # | Objetivo Ciclo 4 | Estado actual (evidencia en repo) | Brechas principales | Evidencia para cerrar |
|---|---|---|---|---|
| 1 | Instancias aisladas por consumidor + plantilla reproducible | ADR-001 (autonomous-first) y runbooks existen; compose.yaml/.env.example genéricos | Falta plantilla explícita por consumidor (config, credenciales, DB, políticas, auditoría, backup, actualización), ejemplos CASE-POOLAR/EnRuta/Anexo/otros y doc operativa de instancia | Plantilla versionada + guía de parametrización + demostración local reproducible (sin despliegue prod) |
| 2 | Trazabilidad completa de SecurityContext | security.py/contracts/security.py, propagación parcial en endpoints/engine/repos (cambios locales) | Auditar *todos* los caminos (async, errores, reintentos, pipeline/auditorías, adaptadores restantes) y probar no-pérdida/no-sustitución desde payload | Matriz de flujo + tests específicos por camino (incl. negativos de spoofing/sustitución) |
| 3 | Matriz de autorización exhaustiva | Matriz y tests (strict_authz_matrix, denial_effects) cubren 17 rutas; scopes granulares propuestos | Completar cobertura de **todas** las rutas (nuevas/emergentes), recurso/operación/contexto, efectos y excepciones justificadas; validar en strict y regresión dev | Matriz completa con evidencia por ruta + suite negativa sistemática + excepciones documentadas |
| 4 | Persistencia e integridad + PostgreSQL | Migraciones SQLite (sqlite_migrations.py, script), tests de migración/roundtrip; columnas contextuales e idempotencia | Probar migraciones sobre copias con datos representativos; estrategia/versionado formal PG; aislamiento/integridad en PG **no validado** | Evidencia de migración en copia, plan/artefactos PG (schemas, fixtures, tests, workflow) y gate externo marcado si no hay entorno |
| 5 | Multi-tenant compartido (preparación, bloqueado) | Gate fail-closed, primitivas parciales (stamping/filtrado/idempotencia scoped), PoC repo | Aislamiento E2E completo (consultas/escrituras/evidencias/decisiones/auditoría/eventos), idempotencia compuesta en todos los casos, concurrencia, revisión independiente | Batería E2E+concurrencia+negativos y revisión independiente; **mantener bloqueado** hasta evidencia total |
| 6 | Integración L1 con POOLAR (instancia aislada CASE) | No implementada en repo CASE; endpoint case-eval/v0.1-draft como contrato a preservar | Diseñar/implementar flujo L1 con datos sintéticos, identidad consumidor, respuesta con recomendación/evidencias/riesgos/procedencia/versión de política; sin ejecución automática sensible | Contrato/adapter + tests de contrato/seguridad + demo sintética; coordinar con POOLAR (repo externo) |
| 7 | Revisión de calidad reproducible | Suites y tools definidos (pytest, ruff, mypy) | Reproducir y registrar en este estado/entorno (no-live, seguridad, migraciones, API, contratos, aislamiento, lint, concurrencia) | Registro de comandos, entorno, commit, resultados y fallos |
| 8 | Auditoría independiente | No realizada | Revisión por agente/revisor distinto del implementador; corrección de críticos reproducibles y revalidación | Informe de auditoría + fixes + re-test evidence |
| 9 | Coordinación otros productos | Fuera del alcance directo de este repo salvo contratos/referencias | POOLAR Fase 0 PG, EnRuta/SkyCast contratos, Anexo Risk recuperación Git, gobernanza canónica | Seguimiento cruzado documentado (dependencias externas) |
| 10 | Entregables documentales y calificación | Hardening/matriz/runbooks/ADR parciales | Actualizar catálogo de contratos, tests, registro de deuda, backlog, evidencias, changelog, continuidad y calificación por modalidad | Conjunto documental coherente y trazable |

## 2. Clasificación objetivo (a mantener honesta)

| Modalidad | Objetivo Ciclo 4 | Criterio |
|---|---|---|
| Desarrollo autónomo | Consolidar y evidenciar | Gates locales reproducidos y registrados |
| Instancia aislada estricta (consumidor único) | Reforzar hacia “apto con reservas” sólido | Contexto/auditoría/migraciones/negativos demostrados end-to-end en alcance |
| Integración POOLAR-CASE (L1, aislada) | Preparar y demostrar con datos sintéticos | Flujo completo, sin acciones reales, contrato preservado/evolución justificada |
| Multi-tenant compartido | **Seguir bloqueado** | Solo preparación; habilitación únicamente con evidencia total + revisión independiente |
| Producción | **No apto** | Requiere hardening/ops/observabilidad/cumplimiento y aprobación humana |

## 3. Secuencia de implementación propuesta (incremental, verificable)

1. **Consolidación de base (esta rama):** inventario de cambios locales, ejecución y registro de gates no-live/lint/tipos sobre estado actual; fijar línea base de fallos conocidos.
2. **Punto 1:** plantilla reproducible de instancia aislada (deploy/templates/isolated-instance/) + doc de configuración independiente (credenciales, DB, políticas, auditoría, backup, actualizaciones) con ejemplos por consumidor.
3. **Puntos 2-3:** auditoría de propagación de SecurityContext por camino y cierre de matriz authz (rutas faltantes/nuevas, scopes, negativos, efectos) con tests.
4. **Punto 4:** validación de migraciones SQLite sobre copias con datasets representativos; preparación PG (schemas/fixtures/tests/workflow) y marcaje explícito de gate externo si no hay entorno.
5. **Punto 5:** plan y pruebas de preparación multi-tenant (sin desbloquear gate): ampliar E2E/concurrencia donde sea seguro demostrar.
6. **Punto 6:** diseño/contrato de integración L1 POOLAR (instancia aislada, sintético) y pruebas de contrato; coordinación con repo POOLAR según disponibilidad.
7. **Puntos 7-10:** registro de evidencias, actualización de docs (hardening, matriz, ADRs, catálogo contratos, deuda, backlog, changelog, continuidad) y paquete para auditoría independiente.

## 4. Dependencias y bloqueos explícitos

- **PostgreSQL:** validación de aislamiento/integridad y migraciones reales requiere entorno disponible; mientras tanto, preparar artefactos y dejar gate **NO VALIDADO**.
- **POOLAR / otros productos:** integración y Fase 0 PG dependen de infra/repos externos; no forzar integraciones sin caso de uso y derechos verificados.
- **Multi-consumidor compartido:** bloqueo se mantiene hasta evidencia completa + revisión independiente (no remover por conveniencia).
- **Producción / despliegues reales:** fuera de alcance; no automatizar.

## 5. Registro de trabajo (a completar en cada iteración)

| Fecha | Commit | Cambio | Comandos | Resultado | Notas |
|---|---|---|---|---|---|
| 2026-11-11 | (working tree) | Rama creada; plan Ciclo 4 y plantilla instancia aislada (inicial) | ver §7 al reproducir | pendiente | base para consolidación |

## 6. Próximos pasos inmediatos (ejecutables)

- [ ] Reproducir gates no-live/seguridad/migraciones/lint/mypy y registrar evidencia.
- [ ] Añadir/ajustar plantilla de instancia aislada y ejemplos por consumidor.
- [ ] Completar inventario de rutas/flows para cerrar §2-§3 con pruebas.
- [ ] Documentar estado PG (preparado vs validado) y pruebas de migración en copia.
