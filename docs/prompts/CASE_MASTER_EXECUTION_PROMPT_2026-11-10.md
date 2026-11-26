# PROMPT MASTER DEFINITIVO — CASE
## Auditoría integral, hardening, consolidación arquitectónica, implementación, validación y preparación evolutiva

**Repositorio:** `C:\Users\JUAN\Desktop\Proyectos\CASE`  
**Remoto:** `https://github.com/juandelaf1/CASE.git`  
**Rama principal de trabajo identificada:** `v4/portfolio-release`  
**Último HEAD comunicado:** `b7021bb4316eec063633bbfdd99d1e0cb9164295`

---

# 0. TU ENCARGO: NO QUIERO OTRO INFORME DE PENDIENTES

Actúa como un equipo técnico completo compuesto por:

- Arquitecto principal de software.
- Principal Engineer.
- Especialista en arquitectura hexagonal.
- Ingeniero de seguridad de aplicaciones.
- Especialista en autenticación, autorización y aislamiento multi-tenant.
- Ingeniero de persistencia y bases de datos.
- Especialista en fiabilidad y sistemas distribuidos.
- Ingeniero de calidad y automatización de pruebas.
- Responsable de DevSecOps y packaging.
- Revisor independiente de arquitectura y código.

Tu responsabilidad es llevar CASE hasta el máximo nivel de madurez que pueda alcanzarse mediante trabajo técnico verificable, sin inventar garantías ni ocultar limitaciones.

**No te estoy pidiendo que me digas qué habría que hacer. Te estoy encargando que hagas el trabajo.**

Debes:

1. Comprender exhaustivamente CASE antes de modificarlo.
2. Reconstruir su arquitectura y evolución histórica.
3. Revisar todo el código relevante, todas las ramas y todos los cambios locales.
4. Auditar las garantías funcionales y de seguridad.
5. Identificar todos los problemas demostrables.
6. Diseñar una secuencia de correcciones coherente.
7. Implementar las correcciones necesarias.
8. Crear las pruebas que falten.
9. Ejecutar los quality gates.
10. Revisar la documentación y actualizarla.
11. Comprobar que el producto funciona en entornos reproducibles.
12. Revisar los cambios realizados como si los hubiera implementado otra persona.
13. Continuar con el siguiente bloque de trabajo sin detenerte cuando termines un simple informe.
14. Entregar una auditoría final que determine qué está terminado, qué garantías se han demostrado y qué bloqueos reales permanecen.

No finalices tu trabajo después del diagnóstico, la planificación o la primera tanda de correcciones.

**Continúa ejecutando todo lo que sea técnicamente necesario, seguro, verificable y posible en el entorno disponible.**

Solo debes detener una acción concreta cuando dependa realmente de una intervención humana, autorización externa, infraestructura no disponible, secretos no proporcionados, servicios de terceros, datos reales sensibles o revisión independiente. En ese caso, deja esa acción completamente preparada y continúa con el resto.

---

# 1. CONTEXTO REAL DE PARTIDA

La última auditoría comunicó lo siguiente. Debes verificarlo antes de utilizarlo como base definitiva.

## 1.1. Qué es CASE

CASE es una plataforma autónoma de orquestación y evaluación estructurada de decisiones asistidas por IA, orientada a contextos operativos.

Tiene una arquitectura basada en:

- Contratos Pydantic v2.
- Puertos y adaptadores.
- `TriageEngine`.
- `DomainRegistry`.
- `DomainPolicy`.
- `AutomationPolicy`.
- `PromptBuilder`.
- Proveedores LLM.
- `ReliabilityPipeline`.
- Evaluación de riesgo.
- HITL.
- Persistencia.
- Auditoría.
- API FastAPI.
- Interfaz Streamlit.
- Adaptadores de fuentes y sistemas externos.

CASE no es un sistema autónomo de decisión sin supervisión humana. Tampoco es un simple endpoint de otro producto.

**CASE debe conservar su autonomía como plataforma y su capacidad de trabajar de manera independiente.**

## 1.2. Estado funcional comunicado

En la última revisión estaban conectados al flujo principal:

- FastAPI.
- Composition.
- `TriageEngine`.
- `DomainRegistry`.
- Cinco dominios.
- Políticas de dominio y automatización.
- Proveedores Mock, Groq, Ollama y Cloud opcional.
- Circuit breaker.
- Reliability pipeline.
- Evaluación y enrutamiento de riesgo.
- Persistencia SQLite.
- Auditoría.
- Endpoints HITL.
- `/api/v1/evaluate`, en modalidad recommendation-only.

Los cinco dominios comunicados eran:

- `infrastructure`
- `logistics`
- `real_estate`
- `seismic_risk`
- `urban_operations`

Hay módulos que se describieron como aislados o insuficientemente conectados:

- ML.
- Governance.
- Hybrid Decision Engine.
- Production utilities.
- Partes de evaluación avanzada.
- Algunas capacidades de Streamlit.
- Duplicidades y rutas independientes de logística.

No debes conectar todos esos componentes por el mero hecho de que existan. Determina cuáles aportan valor real, cuáles están preparados para integrarse y cuáles deben seguir siendo independientes.

## 1.3. Hardening comunicado

El working tree ya contenía un ciclo de hardening que incluía:

- Modos `dev`, `shared` y `prod`.
- Comportamiento fail-closed en modos estrictos.
- `SecurityContext`.
- Propagación de contexto.
- Scopes server-derived.
- Stamping y filtrado por contexto.
- Idempotencia compuesta y persistente en `/api/v1/evaluate` en strict.
- Protección frente a spoofing de tenant y organización en flujos endurecidos.
- Migraciones SQLite versionadas v1↔v2.
- Una PoC de aislamiento por instancias strict separadas.
- Pruebas de replay, conflicto e in-progress.
- Compatibilidad del modo dev.
- Bloqueo deliberado de shared multi-consumer.

Debes comprender todos esos cambios y su relación con la arquitectura original. No los sustituyas por una implementación nueva sin haber determinado primero si la existente es correcta.

## 1.4. Resultados comunicados en la última auditoría

En el estado final de aquella ejecución:

| Gate | Resultado comunicado |
|---|---|
| `ruff check src tests` | PASS, 0 errores |
| `mypy src --ignore-missing-imports` | PASS, 102 archivos |
| Suite no-live | 826 passed |
| Construcción wheel | PASS |
| Inclusión de `logistics_adapter` | Verificada |
| Inclusión de `usgs_adapter` | Verificada |
| Instalación en entorno limpio | No demostrada |
| PostgreSQL | No validado |
| Shared multi-consumer | No apto |
| Producción | No apto |
| Revisión independiente de seguridad | Pendiente |

Comando de suite no-live comunicado:

`pytest tests/ -q --ignore=tests/unit/test_streamlit_client.py --ignore=tests/integration/test_groq_live.py --ignore=tests/integration/test_ollama_integration.py`

**Estos resultados son una referencia histórica. No los presentes como resultados actuales sin volver a ejecutarlos.**

## 1.5. Estado Git comunicado

Rama:

`v4/portfolio-release`

HEAD:

`b7021bb4316eec063633bbfdd99d1e0cb9164295`

Se comunicó que el working tree estaba sucio, sin cambios staged, y que no se habían hecho commits ni pushes.

### Archivos modificados comunicados

- `pyproject.toml`
- `src/case_api/api/v1/app.py`
- `src/case_api/api/v1/auth.py`
- `src/case_core/application/engine.py`
- `src/case_core/ports/audit.py`
- `src/case_core/ports/decision_repository.py`
- `src/case_core/ports/repository.py`
- `src/case_core/reliability/pipeline.py`
- `src/case_infra/persistence/sqlite_adapter.py`
- `src/case_infra/persistence/sqlite_audit.py`
- `src/case_infra/persistence/sqlite_decision_repository.py`
- `tests/integration/test_evaluate_contract.py`
- `tests/unit/test_behavioral.py`
- `tests/unit/test_bootstrap.py`
- `tests/unit/test_persistence_roundtrip.py`
- `tests/unit/test_reliability.py`
- `tests/unit/test_security.py`
- `tests/unit/test_sqlite.py`
- `tests/unit/test_triage_engine.py`

### Archivos untracked comunicados

- `AGENTS.md.backup`
- `docs/AUTHZ_MATRIX_ENDPOINT_SCOPE.md`
- `docs/MULTICONSUMER_SECURITY_HARDENING.md`
- `docs/adr/`
- `docs/audits/`
- `pytest_case.txt`
- `scripts/migrate_case_sqlite.py`
- `src/case_api/api/v1/security.py`
- `src/case_core/contracts/security.py`
- `src/case_infra/persistence/sqlite_idempotency.py`
- `src/case_infra/persistence/sqlite_migrations.py`
- `src/pytest_case.txt`
- `src/pytest_output.txt`
- `tests/integration/test_evaluate_security.py`
- `tests/integration/test_multiconsumer_isolation_poc.py`
- `tests/unit/test_sqlite_migrations.py`

La auditoría generó también:

`docs/audits/CASE_DEEP_AUDIT_AND_EVOLUTION_2026-11-10.md`

El estado real puede haber cambiado. Vuelve a inspeccionarlo.

---

# 2. REGLAS NO NEGOCIABLES

Estas reglas prevalecen sobre cualquier preferencia de implementación.

## 2.1. Preservar la identidad de CASE

No conviertas CASE en:

- Una API genérica de llamadas a LLM.
- Una simple capa de POOLAR.
- Un motor de reglas sin trazabilidad.
- Un sistema autónomo que ejecute decisiones sensibles sin supervisión.
- Un framework de plugins dinámicos innecesariamente complejo.
- Un conjunto de microservicios sin necesidad demostrada.

Debe conservar su arquitectura de evaluación, validación, riesgo, fiabilidad, decisión supervisada y auditoría.

## 2.2. Preservar los invariantes

Lee `AGENTS.md` y todos los documentos de autoridad del repositorio.

Respeta:

- I01–I15.
- Contratos congelados.
- Puertos.
- Separación del dominio.
- Independencia de proveedores.
- Validación de las salidas LLM.
- Límites del Core.
- Política de riesgo.
- HITL.
- Auditoría.
- Compatibilidad.

No cambies un invariante para facilitar una implementación.

Si encuentras una contradicción, documenta el problema y resuélvelo mediante una decisión arquitectónica explícita.

## 2.3. No inventar garantías

No confundas:

- Código existente con funcionalidad integrada.
- Test unitario con garantía E2E.
- Dos instancias separadas con aislamiento shared multi-consumer.
- SQLite con garantías de concurrencia de PostgreSQL.
- API key con identidad completa.
- Scope declarado con autorización efectiva.
- Migración de una copia con migración operativa segura.
- Mock con integración real.
- Wheel construido con paquete instalado y ejecutado correctamente.
- Health check con disponibilidad real.
- Auditoría escrita con auditoría íntegra.
- Documento con evidencia.
- Calidad local con preparación de producción.

Cuando no puedas demostrar algo, utiliza expresamente:

**NO DEMOSTRADO.**

---

# 3. PROTECCIÓN DEL REPOSITORIO Y DEL TRABAJO EXISTENTE

Antes de cambiar nada, inspecciona:

- Rama actual.
- HEAD.
- Tracking.
- Estado local y remoto.
- Cambios staged.
- Cambios unstaged.
- Archivos untracked.
- Archivos ignorados relevantes.
- Contenido de los informes anteriores.
- Configuración del proyecto.

Genera un inventario de estado inicial.

Preserva todo el trabajo anterior, incluso el que no comprendas todavía.

No elimines artefactos hasta demostrar que son prescindibles y conocer su origen.

No uses operaciones destructivas ni cambies de rama con cambios sin consolidar.

### Operaciones que no debes realizar

Sin autorización expresa:

- `git reset --hard`
- `git clean`
- `git restore` descartando modificaciones.
- `git stash`
- Rebase.
- Merge.
- Cherry-pick.
- Cambio de rama con working tree sucio.
- Commit de cambios mezclados.
- Push.
- Merge remoto.
- Apertura de PR.
- Despliegue público.

Puedes utilizar `git diff`, `git log`, `git show`, `git status`, comparaciones de referencias y copias temporales.

Puedes crear archivos, corregir código y actualizar documentación dentro del repositorio.

Antes de modificar un archivo que ya tenga cambios locales, estudia el diff y conserva su contenido y su intención.

Al final, deja el working tree íntegro y describe sus diferencias.

---

# 4. FASE I — COMPRENSIÓN COMPLETA DE CASE

No empieces con refactors.

Primero comprende el sistema.

## 4.1. Estudia el repositorio

Inspecciona como mínimo:

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `src/case_core/`
- `src/case_api/`
- `src/case_infra/`
- `src/logistics_adapter/`
- `src/usgs_adapter/`
- `case_logistics/`
- `tests/`
- `docs/`
- `Dockerfile`
- `render.yaml`
- Configuración CI.
- Scripts de ejecución, migración y mantenimiento.

Busca además cualquier módulo adicional que intervenga en la ejecución.

## 4.2. Traza los flujos reales

Reconstruye el recorrido efectivo de una operación:

`API → AuthN → AuthZ → SecurityContext → Application → TriageEngine → Domain Policy → Provider → ReliabilityPipeline → Risk / Automation → Repository → Audit → Response`

Comprueba si este flujo coincide con el código y dónde existen rutas alternativas.

Para cada componente documenta:

- Responsabilidad.
- Archivo.
- Contrato.
- Consumidores.
- Dependencias.
- Datos que recibe.
- Datos que devuelve.
- Errores posibles.
- Comportamiento ante fallos.
- Validaciones.
- Persistencia.
- Cobertura de pruebas.
- Integración real.

## 4.3. Construye un mapa de dependencias

Identifica:

- Dependencias entre módulos.
- Ciclos de importación.
- Imports que cruzan límites del dominio.
- Interfaces utilizadas.
- Interfaces no utilizadas.
- Adaptadores conectados.
- Componentes duplicados.
- Código muerto.
- Módulos aislados.
- Puntos donde se concentran responsabilidades excesivas.

No elimines código basándote únicamente en que no aparece en el flujo principal. Puede tener consumidores independientes o formar parte de una capacidad deliberadamente aislada.

## 4.4. Reconstruye la arquitectura lógica

Diferencia claramente:

1. Domain.
2. Application.
3. Ports.
4. Adapters.
5. Infrastructure.
6. API.
7. Composition.
8. Presentation.
9. External integrations.

Detecta cualquier inversión de dependencias incorrecta o fuga de lógica.

**Resultado obligatorio:** un documento de arquitectura que represente el código real, no la arquitectura deseada.

---

# 5. FASE II — CONSOLIDAR EL ESTADO REAL DE LOS DOMINIOS

Inspecciona la composición y todos los dominios.

Para cada uno:

- Identificador.
- Registro.
- Policy.
- Automation Policy.
- Contratos.
- Evaluadores.
- Evidencia.
- Reglas.
- Provider.
- Persistencia.
- Tests.
- Estado funcional.
- Integración real.

Confirma los cinco dominios históricos y descubre si han aparecido otros.

## 5.1. Domain Registry

Determina qué capacidades tiene realmente el registry.

No llames plugin dinámico a un diccionario en memoria.

Valora si hace falta formalizar un contrato de Domain Pack con:

- Manifest.
- Identificador.
- Versión.
- Policy.
- Automation Policy.
- Contratos.
- Evaluadores.
- Adaptadores de evidencia.
- Suite de validación.
- Dependencias.
- Habilitación.
- Compatibilidad con Core.

Implementa solo la parte necesaria para reducir acoplamiento y mejorar la mantenibilidad.

No implementes descubrimiento dinámico, carga arbitraria o ejecución de código externo sin un caso real y un modelo de seguridad adecuado.

## 5.2. Duplicidades

Investiga exhaustivamente:

- `case_logistics/`.
- `src/case_core/domain/logistics_*`.
- `src/logistics_adapter/`.

Identifica la implementación canónica, los consumidores de cada una y las diferencias semánticas.

Determina si la duplicidad responde a responsabilidades distintas o a deuda técnica.

Si hay duplicidad innecesaria:

1. Define una fuente canónica.
2. Mantén adaptadores de compatibilidad si son necesarios.
3. Migra consumidores de forma controlada.
4. Añade tests de equivalencia o regresión.
5. Documenta el cambio.

No hagas una fusión indiscriminada.

## 5.3. Módulos aislados

Examina:

- ML Adaptation.
- Specialist Models.
- Hybrid Decision Engine.
- Governance.
- Production utilities.
- Evaluación avanzada.
- Streamlit.

Clasifícalos como integrados, parciales, aislados, experimentales o pendientes.

Decide para cada uno si debe:

- Integrarse.
- Mantenerse autónomo.
- Convertirse en un adapter.
- Formalizar un contrato.
- Documentarse como experimental.
- Eliminarse en el futuro tras confirmar que no tiene consumidores.

No fuerces su integración para aumentar artificialmente el número de funcionalidades.

---

# 6. FASE III — CERRAR HARDENING STRICT SINGLE-CONSUMER

Este es el siguiente objetivo técnico obligatorio.

No avances a una declaración de aptitud superior hasta demostrar el comportamiento de extremo a extremo.

## 6.1. Modos de ejecución

Audita `dev`, `shared` y `prod`.

Define el comportamiento esperado y comprueba su implementación.

### Dev

- Compatible con desarrollo local.
- Configurable.
- Testeable.
- No debe contaminar las garantías strict.
- Debe dejar claro cuándo funciona sin autenticación.

### Strict single-consumer

- Fail-closed.
- Identidad verificable.
- Configuración obligatoria.
- Autorización efectiva.
- Scopes.
- Contexto.
- Persistencia aislada.
- Auditoría coherente.
- Idempotencia en operaciones soportadas.
- Pruebas negativas.
- Comportamiento seguro ante errores.

### Shared

Debe permanecer bloqueado mientras no se demuestre aislamiento real entre consumidores.

No permitas que una configuración incompleta se interprete como shared seguro.

### Prod

No debe aceptar configuraciones inseguras por defecto.

No debe degradarse silenciosamente a dev o a acceso abierto.

Comprueba los errores de arranque y configuración.

## 6.2. Autenticación

Audita:

- Carga de credenciales.
- Ausencia de secretos.
- Secretos vacíos.
- Credenciales incorrectas.
- Comparación segura.
- Revocación.
- Rotación.
- Identificación del consumidor.
- Identidad server-derived.
- Excepciones de rutas públicas.
- Errores.
- Arranque.

Si la autenticación sigue basada en una API key global, determina exactamente sus límites.

No presentes una API key global como un sistema completo de identidad multi-tenant.

Implementa las mejoras que sean necesarias para el nivel single-consumer, sin romper compatibilidad.

## 6.3. Autorización

Construye una matriz completa de operación/recurso/scope.

Verifica tanto accesos permitidos como denegados.

Cubre, cuando existan:

- Evaluate.
- Triage.
- Cases.
- Domains.
- Providers.
- Comparison.
- Seismic.
- Audit.
- HITL.
- Approvals.
- Decisions.
- Listados.
- Consultas por identificador.
- Escrituras.
- Modificaciones.
- Reintentos.
- Operaciones internas expuestas.

Prueba específicamente:

- Sin credenciales.
- Identidad inválida.
- Consumidor revocado.
- Scope ausente.
- Scope incorrecto.
- Tenant manipulado.
- Organization manipulada.
- SecurityContext ausente.
- Contexto de otro consumidor.
- Objeto perteneciente a otro contexto.
- Identificador válido pero no autorizado.

Comprueba que ninguna ruta evita la autorización mediante una ruta secundaria.

No te limites a verificar middleware: revisa también la capa de aplicación y persistencia.

## 6.4. Seguridad de objeto y prevención IDOR

Para cada endpoint que recibe identificadores:

- Identifica el objeto.
- Comprueba propietario/contexto.
- Valida el scope.
- Verifica la consulta.
- Evita que una comprobación posterior revele información sensible.
- Devuelve el código correcto.

Distingue cuándo corresponde `401`, `403`, `404` o `409`.

La respuesta HTTP no debe ser la única prueba: verifica también que no se hayan producido escrituras, auditorías incorrectas o efectos colaterales.

---

# 7. FASE IV — PROPAGACIÓN Y CONSISTENCIA DE SECURITY CONTEXT

Esta fase es crítica.

Traza `SecurityContext` desde el middleware hasta cada punto donde se consulta, persiste, transforma, registra o decide algo.

Cubre:

`Middleware → API → Application → Engine → Reliability → Domain → Provider → Repository → Audit`

No basta con el camino de éxito.

Prueba:

1. Éxito.
2. Validación fallida.
3. Rechazo de autorización.
4. Excepción de dominio.
5. Error de provider.
6. Timeout.
7. Retry.
8. Circuit breaker.
9. Persistencia fallida.
10. Auditoría fallida.
11. Cancelación.
12. Idempotencia replay.
13. Conflicto idempotente.
14. Operación simultánea.
15. Adaptadores.
16. HITL.

Comprueba que:

- No se pierde el contexto.
- No se sustituye por datos controlables por el usuario.
- No se mezcla un contexto anterior con uno nuevo.
- Los resultados tienen el consumidor correcto.
- Los datos persistidos tienen el contexto correcto.
- La auditoría tiene el contexto correcto.
- Los errores no filtran datos cruzados.
- Los reintentos reutilizan el contexto autorizado, no uno reconstruido de forma insegura.

Construye tests E2E reales para los recorridos críticos.

Si alguna función necesita una ampliación de contrato, diseña la modificación sin romper invariantes y documenta la decisión.

---

# 8. FASE V — PERSISTENCIA, IDEMPOTENCIA Y CONSISTENCIA TRANSACCIONAL

## 8.1. Persistencia

Revisa todos los repositorios SQLite y sus puertos.

Comprueba:

- Consultas filtradas por contexto.
- Inserciones con contexto.
- Actualizaciones con contexto.
- Eliminaciones, si existen.
- Restricciones.
- Índices.
- Transacciones.
- Rollback.
- Integridad.
- Persistencia de auditoría.
- Persistencia de decisiones.
- Persistencia de idempotencia.

No dependas de que la API haya comprobado previamente algo si el repositorio puede reforzar la garantía.

## 8.2. Idempotencia

Audita `/api/v1/evaluate` y otras operaciones que realmente la necesiten.

Verifica:

- Clave.
- Consumidor.
- Operación.
- Contexto.
- Payload.
- Hash o firma de contenido.
- Expiración.
- Replay.
- Conflicto.
- In-progress.
- Finalización.
- Timeout.
- Error antes de persistir.
- Error después de persistir.
- Error durante auditoría.

Determina si dos operaciones distintas pueden colisionar.

Comprueba la persistencia y las carreras concurrentes.

No añadas idempotencia a operaciones que no tengan una semántica clara de repetición; primero define qué significa repetirlas y qué efectos deben evitarse.

## 8.3. Consistencia de auditoría

Determina qué sucede cuando:

- La evaluación termina, pero falla la auditoría.
- Se persiste una decisión y falla la respuesta.
- Se reintenta una operación.
- Se repite una operación idempotente.
- Se produce un error durante HITL.
- Se modifica una decisión.
- Se revoca un consumidor.

No afirmes que la auditoría es completa si existen caminos donde puede perderse un evento relevante.

Diseña e implementa garantías razonables y verificables.

Si hace falta patrón outbox, transacción común o mecanismo de reconciliación, justifica la elección y el coste antes de introducirlo.

---

# 9. FASE VI — MIGRACIONES Y EVOLUCIÓN DEL ESQUEMA

Audita todas las versiones de esquema.

Formaliza un sistema de migraciones reproducible.

Comprueba:

- Base nueva.
- Esquema v1.
- Esquema v2.
- Upgrade.
- Downgrade cuando esté soportado.
- Reejecución.
- Migración parcial.
- Datos existentes.
- Fallo intermedio.
- Recuperación.
- Compatibilidad con el código actual.

Las pruebas se deben realizar con bases temporales y copias.

No alteres bases de datos reales del usuario.

Prepara:

- Runbook.
- Backup previo.
- Verificación posterior.
- Procedimiento de rollback.
- Límites de reversibilidad.
- Matriz de versiones soportadas.

Comprueba que `scripts/migrate_case_sqlite.py` y los módulos de migración son coherentes.

Si el sistema de migraciones actual no ofrece seguridad suficiente, corrígelo.

---

# 10. FASE VII — CONCURRENCIA, STRESS Y VALIDACIÓN MULTI-CONSUMER

No confundas el objetivo single-consumer con el objetivo shared.

## 10.1. Single-consumer

Cierra todas las pruebas relevantes de:

- Requests simultáneos.
- Reintentos.
- Idempotencia.
- Escrituras.
- Lecturas.
- Auditoría.
- Persistencia.
- Timeout.
- Fallos intermedios.
- Consistencia del estado.

## 10.2. Shared multi-consumer

Determina la arquitectura necesaria para habilitarlo de manera segura.

Evalúa:

- Base de datos compartida.
- Proceso compartido.
- Varios workers.
- Transacciones.
- Índices compuestos.
- Aislamiento por consumidor.
- Consultas filtradas.
- Idempotencia compartida.
- Auditoría.
- Locks.
- Concurrencia.
- Revocación.
- Consistencia de permisos.

La PoC anterior de instancias strict separadas no es prueba suficiente.

Diseña y ejecuta una prueba realista con consumidores diferentes que utilicen el mismo servicio y la misma persistencia.

Los escenarios de prueba deben intentar acceder a datos de otros consumidores y demostrar que no se produce exposición ni modificación cruzada.

## 10.3. PostgreSQL

Comprueba si PostgreSQL es necesario para demostrar las garantías que se pretenden ofrecer.

Si el entorno lo permite:

- Levanta una instancia local desechable.
- Prepara pruebas de integración.
- Prueba transacciones.
- Prueba idempotencia concurrente.
- Prueba varios procesos.
- Comprueba aislamiento y rollback.
- Verifica migraciones.
- Comprueba restricciones e índices.

No utilices bases compartidas externas ni credenciales ajenas.

Si PostgreSQL no está disponible, prepara la infraestructura de pruebas necesaria, pero marca claramente como no demostrados los resultados que no hayas podido ejecutar.

Valora RLS solo si aporta defensa en profundidad real y encaja en el modelo elegido.

**Nunca habilites shared multi-consumer solo porque una PoC o algunos tests hayan pasado.**

---

# 11. FASE VIII — ADAPTADORES, PROVIDERS Y FIABILIDAD

Audita todos los providers y adaptadores.

Para cada uno:

- Entradas.
- Salidas.
- Contratos.
- Validación.
- Autenticación.
- Timeouts.
- Retry.
- Circuit breaker.
- Error handling.
- Contexto.
- Auditoría.
- Procedencia.
- Tests.
- Fallback.

Comprueba especialmente:

- Mock provider.
- Groq.
- Ollama.
- Cloud.
- USAID/logística.
- USGS/sísmica.
- Otros adaptadores existentes.

Asegúrate de que los datos externos no se consideran evidencia confiable sin validación.

No permitas que las respuestas externas eludan el Core, las policies, la evaluación de riesgo o la supervisión que corresponda.

Verifica específicamente si `LogisticsPipeline` invoca realmente `TriageEngine` o si solo construye y clasifica `OperationalCase`.

Corrige cualquier discrepancia entre docstrings, documentación y ejecución real.

No hagas llamadas live que puedan consumir dinero, modificar servicios externos o usar credenciales sin autorización.

---

# 12. FASE IX — PACKAGING, INSTALACIÓN Y EJECUCIÓN REPRODUCIBLE

La construcción del wheel ya se comunicó como correcta. Falta verificar instalación y ejecución desde un entorno limpio.

Realiza:

1. Construcción del wheel.
2. Inspección de paquetes.
3. Creación de un entorno virtual temporal.
4. Instalación del wheel.
5. Importación de módulos públicos.
6. Arranque de API.
7. Health check.
8. Ejecución de una operación de prueba.
9. Verificación de providers y adaptadores empaquetados.

Comprueba específicamente que `logistics_adapter` y `usgs_adapter` se pueden importar después de instalar el wheel, sin depender del árbol fuente del repositorio.

Inspecciona:

- Dependencias declaradas.
- Dependencias opcionales.
- Imports dinámicos.
- Recursos empaquetados.
- Configuración.
- Paths.
- Entry points.

Corrige cualquier problema reproducible.

No confundas una importación desde el repositorio con una instalación correcta del paquete.

---

# 13. FASE X — DEVSECOPS Y DESPLIEGUE

Audita Docker, CI, Render y otros mecanismos reales de ejecución.

Comprueba:

- Instalación.
- Build reproducible.
- Usuario del contenedor.
- Configuración de puertos.
- Secretos.
- Variables obligatorias.
- Health.
- Ready.
- Persistencia.
- Logs.
- Errores de arranque.
- Configuración de proveedor.
- Seguridad de rutas.
- Datos persistentes.
- Versiones.

Revisa expresamente el riesgo histórico de `render.yaml`: la plantilla parecía no establecer variables de seguridad explícitas y el middleware podía admitir tráfico abierto si `CASE_API_KEY` estaba vacío.

Comprueba si el comportamiento actual lo ha corregido.

Si hay una configuración que pueda desplegar CASE de forma abierta o insegura:

- Corrígela.
- Añade validación de arranque.
- Añade pruebas.
- Documenta las variables obligatorias.
- Actualiza la plantilla.
- Evita secretos hardcodeados.

No despliegues públicamente.

Prepara un entorno local y una configuración reproducible que permita verificarlo.

---

# 14. FASE XI — CALIDAD Y SUITE DETERMINISTA

Necesitamos un sistema de validación que pueda ejecutarse repetidamente y producir evidencia confiable.

El problema histórico era que `.env` y la configuración de provider podían contaminar la suite no-live.

Aísla correctamente las pruebas.

## 14.1. Política de tests

Separa de forma explícita:

- Unit.
- Integration.
- E2E.
- Security.
- Migration.
- Concurrency.
- Live provider.
- External API.

No ocultes tests mediante exclusiones silenciosas.

Usa markers de pytest, configuración clara y selección explícita.

Los tests live deben ser opt-in y tener requisitos de configuración conocidos.

La suite determinista debe:

- Ignorar la configuración personal de proveedores externos.
- Utilizar mocks controlados cuando corresponda.
- No requerir secretos.
- No llamar servicios de pago.
- Ser reproducible.
- Mantener una cobertura funcional útil.

No conviertas tests que antes ejecutaban código real en mocks solo para que pasen.

## 14.2. Quality gates obligatorios

Ejecuta los gates definidos en `AGENTS.md`, CI y `pyproject.toml`.

Como mínimo:

- `ruff check src tests`
- `mypy src --ignore-missing-imports`
- Suite determinista completa.
- Tests de seguridad.
- Tests de E2E.
- Tests de migración.
- Tests de packaging.
- Tests de providers.
- Tests de dominios.
- Tests de persistencia.
- Tests de adaptadores.
- Tests de concurrencia aplicables.

No modifiques los comandos oficiales para esconder fallos.

Cada test fallido debe quedar registrado.

Si un test falla por un servicio externo o secreto ausente, identifica el motivo y no lo presentes como fallo interno ni como éxito.

## 14.3. Regresión

Después de cada bloque:

- Ejecuta los tests relacionados.
- Revisa los resultados.
- Corrige regresiones.
- Vuelve a probar.

Al terminar, ejecuta la suite completa acordada en el estado final.

---

# 15. FASE XII — OBSERVABILIDAD Y OPERACIÓN

Determina qué necesita CASE para poder operarse con garantías.

Revisa:

- Logs estructurados.
- Correlation ID.
- Request ID.
- Identidad del consumidor, sin filtrar secretos.
- Tiempos y resultados.
- Errores.
- Circuit breaker.
- Providers.
- Auditoría.
- Health.
- Readiness.
- Métricas.
- Diagnóstico.
- Recuperación.

No registres:

- API keys.
- Tokens.
- Secretos.
- Datos personales innecesarios.
- Contenido sensible sin una justificación y controles.

Comprueba que el sistema puede diagnosticar qué ha sucedido sin convertir los logs en una fuga de datos.

Implementa las mejoras razonables para el nivel de madurez que se pretende alcanzar.

No añadas observabilidad empresarial pesada si la necesidad puede resolverse con un diseño más sencillo.

---

# 16. FASE XIII — DOCUMENTACIÓN, ADR Y CONTRATOS

La documentación debe representar el estado real del software.

Inspecciona y corrige:

- README.
- Architecture.
- Roadmap.
- API documentation.
- Capability audit.
- V4 proposal.
- Future evolution.
- Case study.
- Seguridad.
- Migraciones.
- Runbooks.
- Tests.
- Packaging.
- Despliegue.

Actualiza cifras de:

- Dominios.
- Endpoints.
- Tests.
- Providers.
- Módulos conectados.
- Capacidades reales.

Cuando haya divergencias, prevalece el código ejecutable y la evidencia obtenida, no una afirmación histórica del README.

Crea ADR para decisiones que alteren:

- Contratos.
- Persistencia.
- Seguridad.
- Identidad.
- Contexto.
- Domain Packs.
- Idempotencia.
- Integraciones.
- Límites del Core.

Cada ADR debe incluir:

- Contexto.
- Problema.
- Alternativas.
- Decisión.
- Consecuencias.
- Compatibilidad.
- Migración.
- Tests.
- Reversibilidad.

No crees documentos duplicados innecesarios.

---

# 17. FASE XIV — CONSOLIDACIÓN ARQUITECTÓNICA

Después de cerrar los riesgos principales, evalúa si la arquitectura necesita simplificación.

Busca:

- Duplicidades.
- Responsabilidades mezcladas.
- Abstracciones sin consumidores.
- Interfaces innecesarias.
- Clases excesivamente grandes.
- Imports incorrectos.
- Configuración dispersa.
- Lógica duplicada.
- Contratos inconsistentes.
- Estados ambiguos.
- Errores que se silencian.
- Fallbacks inseguros.

Refactoriza cuando el beneficio sea concreto.

Conserva interfaces estables cuando cambiar no aporte un valor claro.

No introduzcas tecnología nueva por moda.

Justifica especialmente cualquier propuesta de:

- Microservicios.
- Plugin dinámico.
- Agentes autónomos.
- LangGraph.
- LoRA.
- PostGIS.
- Nuevos brokers.
- Nuevas bases de datos.
- Nuevas capas de abstracción.

CASE debe evolucionar manteniendo un Core pequeño, fiable, explicable y gobernable.

---

# 18. FASE XV — EVALUAR Y PREPARAR LOS SIGUIENTES NIVELES

No confundas los cuatro niveles.

## Nivel A — Desarrollo local

Objetivo: un entorno local reproducible, estable y testeable.

Debe haber:

- Instalación reproducible.
- Configuración documentada.
- Suite determinista.
- Tests relevantes.
- Logs útiles.
- Comportamiento de desarrollo definido.

## Nivel B — Single-consumer strict

Objetivo prioritario.

Debe haber:

- AuthN verificable.
- AuthZ efectiva.
- Scopes server-derived.
- Contexto propagado.
- Filtrado y stamping.
- Protección de objetos.
- Persistencia coherente.
- Auditoría consistente.
- Idempotencia donde corresponda.
- Pruebas negativas y E2E.
- Migraciones verificadas.
- Configuración fail-closed.
- Runbook.
- Paquete reproducible.

Lleva este nivel hasta **APTO** cuando toda la evidencia esté disponible. Si hay bloqueos externos, deja el resultado como APTO CON RESERVAS o NO DEMOSTRADO.

## Nivel C — Shared multi-consumer

Objetivo evolutivo posterior.

Para considerarlo apto se necesita:

- Identidad diferenciada.
- Autorización por consumidor.
- Aislamiento de datos.
- Queries filtradas.
- Integridad transaccional.
- Idempotencia compartida.
- Auditoría independiente.
- Protección frente a IDOR.
- Pruebas con varios consumidores en la misma aplicación y persistencia.
- Concurrencia.
- Multi-proceso.
- Migraciones.
- Validación del backend de producción.
- Revisión independiente de seguridad.

Puedes implementar todo lo que sea necesario para prepararlo, pero no habilites este modo mientras no estén superadas todas las pruebas.

## Nivel D — Producción

Comprueba:

- Threat model.
- Configuración segura.
- Gestión de secretos.
- Persistencia.
- Backups.
- Restauración.
- Observabilidad.
- Gestión de incidentes.
- Health y readiness.
- Despliegue reproducible.
- Dependencias.
- Parches.
- Seguridad.
- Pruebas operativas.
- Procedimientos de recuperación.
- Revisión independiente.
- Validación humana/legal cuando corresponda.

No afirmes que está listo para producción solo porque todos los tests locales pasen.

---

# 19. ORDEN DE EJECUCIÓN: DEBES CONTINUAR HASTA COMPLETAR TODO LO POSIBLE

Sigue esta secuencia sin quedarte en la planificación:

### Bloque 1 — Diagnóstico y preservación

- Comprende el estado.
- Revisa diferencias.
- Identifica cambios anteriores.
- Crea fotografía inicial.

### Bloque 2 — Arquitectura y contratos

- Completa el mapa.
- Determina componentes integrados.
- Detecta problemas.
- Decide correcciones necesarias.

### Bloque 3 — Seguridad strict

- Corrige AuthN.
- Corrige AuthZ.
- Corrige scopes.
- Corrige propagación.
- Corrige acceso a objetos.
- Añade pruebas negativas.

### Bloque 4 — Persistencia e integridad

- Corrige repositorios.
- Corrige filtrado.
- Corrige idempotencia.
- Corrige auditoría.
- Formaliza migraciones.

### Bloque 5 — E2E y concurrencia

- Implementa pruebas críticas.
- Comprueba fallos.
- Comprueba reintentos.
- Comprueba operaciones simultáneas.
- Valida PostgreSQL si está disponible.

### Bloque 6 — Packaging y ejecución

- Wheel.
- Entorno limpio.
- Instalación.
- Imports.
- Arranque.
- Smoke tests.

### Bloque 7 — Integraciones y fiabilidad

- Providers.
- Adaptadores.
- Validación de datos externos.
- Timeout.
- Retry.
- Circuit breaker.
- Trazabilidad.

### Bloque 8 — Documentación y operación

- README.
- Arquitectura.
- ADR.
- Runbooks.
- CI.
- Configuración segura.

### Bloque 9 — Consolidación

- Revisa duplicidades.
- Corrige deuda técnica prioritaria.
- Conserva capacidades independientes.
- Evita refactors masivos.

### Bloque 10 — Preparación de multi-consumer

- Determina requisitos reales.
- Implementa lo que sea seguro y justificable.
- Prueba sobre infraestructura compartida cuando esté disponible.
- Mantén el modo bloqueado si faltan garantías.

### Bloque 11 — Auditoría independiente interna

Actúa como un segundo revisor que no confía en las decisiones de la primera fase.

Vuelve a examinar todos los cambios desde cero.

### Bloque 12 — Validación y cierre

- Suite final.
- Gates.
- Diff.
- Invariantes.
- Documentación.
- Estado Git.
- Informe de cierre.

**Cuando termines un bloque, pasa al siguiente. No esperes instrucciones entre bloques.**

---

# 20. CRITERIOS DE CALIDAD PARA CADA CAMBIO

Cada cambio debe tener una razón y una demostración.

Para cada bug:

1. Reproduce el problema.
2. Añade un test que falle antes de corregirlo.
3. Corrige el comportamiento.
4. Ejecuta el test.
5. Ejecuta regresión.
6. Documenta el resultado.

Para cada cambio de arquitectura:

1. Explica el problema actual.
2. Compara alternativas.
3. Justifica la elegida.
4. Define compatibilidad.
5. Implementa.
6. Añade tests.
7. Documenta.

Para cada cambio de seguridad:

1. Define la amenaza.
2. Define el comportamiento permitido.
3. Define el comportamiento denegado.
4. Implementa el control.
5. Testea casos positivos.
6. Testea casos negativos.
7. Comprueba efectos persistentes.
8. Comprueba los logs y la auditoría.
9. Comprueba que no se ha introducido un bypass.

No aceptes tests que solo prueben que una función devuelve un valor cuando la garantía real afecta a todo un flujo.

---

# 21. GOBERNANZA DE CAMBIOS Y DECISIONES

Debes trabajar con autonomía técnica, no pedir permiso para cada corrección.

Estás autorizado a:

- Modificar código.
- Crear código nuevo.
- Corregir bugs.
- Mejorar contratos cuando sea imprescindible.
- Añadir tests.
- Añadir documentación.
- Añadir ADR.
- Crear scripts de mantenimiento.
- Preparar infraestructura de tests local.
- Corregir CI.
- Mejorar configuración.
- Crear herramientas de auditoría.
- Ejecutar comandos y pruebas locales.
- Construir artefactos temporales.
- Instalar dependencias de desarrollo declaradas, cuando sea seguro.

No estás autorizado a:

- Publicar cambios.
- Hacer push.
- Fusionar ramas.
- Desplegar servicios públicamente.
- Utilizar secretos ajenos.
- Consumir servicios de pago sin permiso.
- Modificar datos reales.
- Ejecutar pruebas destructivas en infraestructura compartida.
- Afirmar revisión independiente cuando solo has hecho una revisión interna.
- Declarar cumplimiento legal o normativo sin verificación competente.

Si una actividad depende de una de esas autorizaciones, prepara un paquete completo para que pueda realizarse después. No bloquees el resto del trabajo.

---

# 22. ARTEFACTOS QUE DEBES ENTREGAR

Crea una carpeta de auditoría si no existe.

No sobrescribas informes anteriores.

Guarda un nuevo informe con fecha y hora, por ejemplo:

`docs/audits/CASE_FULL_EXECUTION_AND_FINAL_AUDIT_2026-11-10.md`

Entrega dentro de la documentación los artefactos que realmente aporten valor:

1. Informe integral.
2. Mapa de arquitectura real.
3. Inventario de módulos y dominios.
4. Grafo de dependencias o equivalente.
5. Matriz AuthN/AuthZ.
6. Matriz de propagación de contexto.
7. Matriz de cobertura E2E.
8. Matriz de migraciones.
9. Evidencia de packaging.
10. Runbook de desarrollo.
11. Runbook single-consumer strict.
12. Runbook de despliegue seguro.
13. Plan de shared multi-consumer.
14. Registro de riesgos.
15. ADR de decisiones relevantes.
16. Roadmap actualizado.

No generes documentos redundantes solo para completar una lista. Si un documento existente ya cumple la función, actualízalo.

Todos los documentos deben diferenciar con claridad estado real, propuestas y trabajo pendiente.

---

# 23. INFORME FINAL: DEBES RENDIR CUENTAS DEL RESULTADO

Tu respuesta final debe contener:

## A. Resultado ejecutivo

Qué es CASE ahora, qué profundidad tiene y cuál es su nivel real de madurez.

## B. Arquitectura final

Qué está integrado, qué es independiente, qué es experimental y qué ha cambiado.

## C. Seguridad

Estado de autenticación, autorización, scopes, contexto, objetos, idempotencia, persistencia y auditoría.

## D. Niveles de preparación

Una tabla:

| Nivel | Estado | Evidencia | Bloqueadores |
|---|---|---|---|
| A — Local | APTO / RESERVAS / NO APTO | ... | ... |
| B — Strict single-consumer | APTO / RESERVAS / NO APTO | ... | ... |
| C — Shared multi-consumer | APTO / RESERVAS / NO APTO | ... | ... |
| D — Producción | APTO / RESERVAS / NO APTO | ... | ... |

## E. Trabajo realizado

Lista exacta de:

- Archivos creados.
- Archivos modificados.
- Bugs corregidos.
- Contratos cambiados.
- Tests nuevos.
- Documentación actualizada.
- Scripts nuevos.
- ADR nuevos.

Diferencia claramente tus cambios de los que ya existían antes.

## F. Pruebas y evidencias

Para cada gate:

- Comando.
- Entorno.
- Resultado.
- Número de tests.
- Duración.
- Skipped.
- Fallos.
- Warnings.
- Limitaciones.

Incluye pruebas ejecutadas sobre el estado final, no solo pruebas intermedias.

## G. Riesgos restantes

Solo los riesgos reales que sigan sin cerrar.

Cada uno debe incluir:

- Severidad.
- Evidencia.
- Impacto.
- Próxima acción.
- Dependencia externa, si la tiene.

## H. Próximo hito

Indica qué debe suceder después y qué criterio objetivo permitirá considerar cerrado ese hito.

## I. Estado Git

- Rama.
- HEAD.
- Tracking.
- Cambios modificados.
- Archivos nuevos.
- Archivos staged.
- Artefactos ignorados relevantes.
- Commits locales.
- Operaciones remotas.

Confirma que no se ha perdido ningún cambio preexistente y que no has publicado ni desplegado.

---

# 24. REGLAS DE CIERRE: NO TE AUTOCONCEDAS LA APROBACIÓN

No declares finalizado un objetivo solo porque hayas escrito su documentación.

Un objetivo está terminado únicamente cuando:

- La implementación existe.
- Está integrada donde corresponde.
- Los contratos están claros.
- Tiene pruebas adecuadas.
- Las pruebas se han ejecutado.
- No introduce regresiones conocidas.
- La documentación coincide.
- Existe evidencia reproducible.

Cuando dependa de infraestructura que no esté disponible, indica qué se ha preparado y qué no puede afirmarse.

Cuando dependa de revisión independiente, prepara la evidencia, pero no te atribuyas esa aprobación.

Cuando no puedas demostrar una propiedad, deja constancia de que sigue abierta.

No reduzcas un criterio de aceptación para hacer que un objetivo aparezca como terminado.

**La prioridad es la integridad de CASE, no el porcentaje aparente de tareas completadas.**

---

# 25. INSTRUCCIÓN FINAL

Quiero que trabajes con mentalidad de responsable técnico de CASE, con visión de producto y responsabilidad sobre sus garantías.

No destruyas ni rehagas por preferencia personal lo que ya funciona.

No te quedes en una auditoría descriptiva.

No te detengas en una lista de recomendaciones.

No solicites confirmación entre tareas locales seguras.

No ocultes problemas.

No maquilles resultados.

No habilites funciones que no puedas garantizar.

**Ejecuta, corrige, prueba, documenta, consolida y audita.**

Primero protege y comprende el trabajo que ya existe. Después termina el hardening strict single-consumer. A continuación, prepara y valida la arquitectura necesaria para shared multi-consumer sin habilitarla prematuramente. Finalmente, lleva packaging, operación, documentación y calidad al nivel más alto que pueda demostrarse.

Continúa hasta que hayas completado todas las tareas técnicas posibles en el entorno disponible y hayas preparado de forma concreta todas las que requieran una intervención externa.

El resultado debe ser una versión de CASE más sólida, coherente, mantenible, segura y verificable, no simplemente un repositorio con más código o más documentación.

**No busco que CASE parezca terminado. Busco que CASE esté realmente mejor construido y que cada garantía que afirmemos pueda demostrarse.**
