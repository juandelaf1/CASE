# Runbook — Despliegue seguro (preparación, NO DESPLEGADO)

**Estado:** preparación documental/técnica. **Nivel D (Producción): NO APTO.** No se realizó despliegue público.

## Principios
- Fail-closed por defecto en entornos no locales: `CASE_SECURITY_MODE=shared` o `prod` con credenciales obligatorias.
- No exponer CASE en `dev` abierto en redes públicas.
- Secretos solo vía gestor/variables seguras (no en repo, no hardcodeados). Rotación y mínimo privilegio.
- Shared multi-consumer **no habilitar** (bloqueado/no demostrado).

## Variables críticas (API)
- `CASE_SECURITY_MODE` (`shared`/`prod` para estricto), `CASE_API_KEY`/`CASE_API_KEYS` (sync: false), `CASE_CONSUMER_ID`, `CASE_TENANT_ID`, `CASE_API_SCOPES`.
- `CASE_PROVIDER` y credenciales de provider solo si se usan (no requeridos para mock).
- `CASE_DB_PATH` en volumen persistente; plan de backup/restore.

## Docker / Render (estado actual)
- `Dockerfile`: imagen slim, usuario no-root, healthcheck `/health`, volumen de datos configurable.
- `render.yaml`: plantilla con defaults seguros sugeridos (security vars presentes, secret sync: false) pero **debe revisarse** antes de cualquier despliegue (URLs, scopes mínimos, proveedor, persistencia, políticas de red). `autoDeploy` y exposición pública requieren decisión humana.
- UI (`streamlit`) consume API: asegurar que la API no quede abierta en despliegues expuestos.

## Checklist previa (obligatoria, no ejecutada aquí)
- [ ] Threat model y revisión de seguridad (independiente para C/D).
- [ ] Configuración strict validada en entorno staging aislado (autorizado).
- [ ] Backups/restore y migraciones probadas en copias.
- [ ] Observabilidad/logs sin secretos ni datos sensibles; alertas/incident response.
- [ ] Dependencias parcheadas, imagen escaneada, health/readiness verificados.
- [ ] Pruebas E2E/concurrencia/carga según objetivo; PostgreSQL si se requiere.
- [ ] Validaciones legales/compliance/humanas aplicables.

## Evidencia local disponible
- Gates ruff/mypy/suite determinista OK; wheel build + instalación/import smoke en venv limpio OK. No sustituye validación operativa/deploy.