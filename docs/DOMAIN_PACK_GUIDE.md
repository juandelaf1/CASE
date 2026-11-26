# Domain Pack Guide

## Goal
Add a new business domain to CASE without changing core decision logic.

## What a domain pack provides
1. **DomainPolicy** (`case_core.ports.domain.DomainPolicy`)
   - `domain_name`: stable string identifier
   - `validate_evidence(...)`: domain evidence rules
   - `classify_urgency(...)`: domain urgency heuristic
   - `get_domain_context()`: context for prompt/evaluation
2. **AutomationPolicy** (`case_core.ports.automation.AutomationPolicy`)
   - `assess_risk(...)`: returns `RiskAssessment` (level, automation decision, HITL, factors)
   - `get_risk_factors()`, `get_automation_rules()`
3. **Registration** in `case_core.composition.create_app_dependencies()` (or test registry)
4. **Tests**: unit tests for policy/automation + integration test through `TriageEngine`/API.

## Minimal checklist
- [ ] New `case_core/domain/<name>_policy.py` (or package) implementing DomainPolicy.
- [ ] New automation policy implementing AutomationPolicy.
- [ ] Register domain in composition/registry.
- [ ] Add domain to automation resolver mapping.
- [ ] Add unit tests for evidence/urgency/risk rules.
- [ ] Add at least one end-to-end test through `TriageEngine.execute`.
- [ ] No `if domain == ...` in core engine; use ports/registry.

## Reference
- Ports: `src/case_core/ports/domain.py`, `src/case_core/ports/automation.py`
- Registry: `src/case_core/domain/registry.py`
- Composition: `src/case_core/composition.py`
- Example domains: `real_estate_policy.py`, `seismic_policy.py`, `logistics_policy.py`
- Extensibility proof: `tests/unit/test_domain_pack_extensibility.py`

## Design rules
- Core remains domain/provider agnostic.
- Domain-specific logic lives in the domain pack, not in engine/API.
- Contracts are Pydantic/typed; outputs auditable.
- New domains should default to conservative/risk-aware automation.
