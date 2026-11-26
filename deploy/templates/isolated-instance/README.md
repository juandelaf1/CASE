# CASE — Plantilla de instancia aislada por consumidor (Ciclo 4)

> **Objetivo:** demostrar una configuración reproducible en local para ejecutar CASE como **instancia independiente** por consumidor.  
> **No** es un despliegue de producción ni habilita el modo multi-consumidor compartido.

## Principios
- **Un consumidor / un contexto autorizado por instancia** (modo estricto single-consumer).
- **Aislamiento por despliegue:** configuración, credenciales, base de datos, auditoría, backups y actualizaciones independientes.
- **Fail-closed:** sin credenciales válidas en shared/prod no arranca; multi-consumidor compartido bloqueado hasta evidencia completa.
- **Datos:** usar datos sintéticos para demos/integraciones de validación; no ejecutar operaciones reales sensibles.

## Archivos de la plantilla
- .env.consumer.example — variables por consumidor (copiar a .env.<consumer> y completar secretos fuera de git).
- compose.isolated.yml — compose parametrizable por variables (proyecto, puertos, volumen/DB, imagen).
- instances.example.yaml — catálogo declarativo de ejemplos (POOLAR, EnRuta, Anexo Risk, genérico).
- README.md — esta guía.

## Uso rápido (local)
1. Copiar .env.consumer.example a .env.poolar (o el consumidor deseado) y completar:
   - CASE_API_KEY (secreto), CASE_CONSUMER_ID, CASE_TENANT_ID, CASE_API_SCOPES.
   - CASE_DB_PATH apuntando a un fichero **propio** del consumidor (p.ej. /app/data/case_poolar.db).
   - Puertos/host si se ejecuta más de una instancia en la misma máquina.
2. Levantar (ejemplo):
   - docker compose -p case-poolar --env-file .env.poolar -f deploy/templates/isolated-instance/compose.isolated.yml up -d --build
3. Verificar: GET /health y pruebas de auth/scope según docs/RUNBOOK_STRICT_SINGLE_CONSUMER.md.
4. **No** reutilizar la misma DB/volumen entre consumidores.

## Independencia requerida por instancia
| Elemento | Práctica |
|---|---|
| Configuración | Fichero .env.<consumer> propio, versionado solo como ejemplo sin secretos |
| Credenciales | CASE_API_KEY/CASE_API_KEYS únicos por consumidor; rotación independiente |
| Contexto | CASE_CONSUMER_ID/CASE_TENANT_ID/CASE_ORGANIZATION_ID definidos y coherentes |
| Persistencia | CASE_DB_PATH y volumen Docker dedicados; nunca compartidos |
| Políticas/scopes | CASE_API_SCOPES mínimos por capacidad; revisión por cambio |
| Auditoría | DB/logs de auditoría del propio consumidor; retención definida |
| Backups | Copia/restore por instancia (ver runbook de migraciones; probar en copia) |
| Actualizaciones | Ventana y validación por instancia (gates no-live antes de promover imagen) |

## Ejemplos de consumidores
Ver instances.example.yaml para perfiles orientativos: **POOLAR**, **EnRuta**, **Anexo Risk** y **genérico**. Ajustar puertos, scopes y políticas al caso de uso real; no asumir integraciones activas sin verificación de derechos/contratos.

## Limitaciones
- Plantilla para **demostración/reproducibilidad local**. Hardening operativo/producción pendiente (observabilidad, TLS/ingress, gestión de secretos, compliance) — ver docs/RUNBOOK_DEPLOYMENT_SECURE.md.
- PostgreSQL y aislamiento multi-tenant compartido: **no validados/no habilitados** en esta plantilla.
