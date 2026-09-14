# CASE Capability Audit Matrix

> Audit of all isolated capabilities. Last verified: 2026-09-14.
> Purpose: Determine integration priority for post-v1.0 evolution.

---

## Legend

| Field | Description |
|-------|-------------|
| **DECISION** | KEEP ISOLATED / INTEGRATE / REFACTOR BEFORE INTEGRATING / DEFER / REMOVE |
| **VALUE** | How much value integration adds to the core pipeline |
| **COMPLEXITY** | Integration effort (LOW / MEDIUM / HIGH) |
| **RISK** | Risk of breaking existing baseline (LOW / MEDIUM / HIGH) |

---

## 1. Logistics Intelligence

### 1.1 ShipmentUnderstanding

| Field | Value |
|-------|-------|
| **CAPABILITY** | ShipmentUnderstanding |
| **PURPOSE** | Transform raw shipment text into structured ShipmentProfile |
| **CURRENT LOCATION** | `domain/logistics_understanding.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `ShipmentProfile` (Pydantic BaseModel) |
| **DEPENDENCIES** | `logistics_contracts.py` (CargoType, ShipmentPriority, SpecialHandling) |
| **CURRENT TESTS** | test_real_estate_domain.py (indirect), test_domain.py (indirect) |
| **CURRENT TEST COUNT** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | HIGH — Complements general CASE understanding. Could pre-process logistics cases before LLM. |
| **COMPLEXITY** | LOW — Standalone regex-based parser. No external dependencies. |
| **RISK** | LOW — Pure function, no side effects. |
| **EVIDENCE** | 145 lines, deterministic keyword extraction, well-structured contracts |
| **INTEGRATION PROPOSAL** | Register as optional pre-processor for logistics domain. Called before TriageEngine if domain is "logistics". |
| **DECISION** | **INTEGRATE** — High value, low complexity, low risk. |

### 1.2 ShipmentClassification

| Field | Value |
|-------|-------|
| **CAPABILITY** | ShipmentClassification |
| **PURPOSE** | Classify shipments by type, risk, complexity, handling category |
| **CURRENT LOCATION** | `domain/logistics_classification.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `ShipmentProfile` → `dict[str, str \| float]` |
| **DEPENDENCIES** | `logistics_contracts.py` |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | MEDIUM — Deterministic classification useful for specialist model baseline. |
| **COMPLEXITY** | LOW — Pure function, no side effects. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 106 lines, rule-based classification, well-defined risk scoring |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED for now. Useful as baseline for future specialist model comparison. |
| **DECISION** | **KEEP ISOLATED** — Good baseline, not critical for pipeline. |

### 1.3 CarrierMatching

| Field | Value |
|-------|-------|
| **CAPABILITY** | CarrierMatching |
| **PURPOSE** | Match shipments to capable carriers based on constraints |
| **CURRENT LOCATION** | `domain/logistics_carrier_matching.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `ShipmentProfile`, `Carrier` → `list[dict]` |
| **DEPENDENCIES** | `logistics_contracts.py` |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | MEDIUM — Scoring algorithm useful for logistics decisions. |
| **COMPLEXITY** | LOW — Pure function, no side effects. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 140 lines, deterministic scoring, capacity/SLA/cost matching |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Could be used by JointRecommendation if integrated. |
| **DECISION** | **KEEP ISOLATED** — Useful but not critical for core pipeline. |

### 1.4 RouteRecommendation

| Field | Value |
|-------|-------|
| **CAPABILITY** | RouteRecommendation |
| **PURPOSE** | Generate and score candidate routes using Haversine distance |
| **CURRENT LOCATION** | `domain/logistics_route_recommendation.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `ShipmentProfile`, `Route`, `RouteSegment` → `list[dict]` |
| **DEPENDENCIES** | `logistics_contracts.py`, `math`, `random` |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | MEDIUM — Mathematical routing logic. Good portfolio signal. |
| **COMPLEXITY** | LOW — Pure math, no external dependencies. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 231 lines, Haversine formula, route scoring, cost estimation |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Mathematical logic should stay separate from LLM pipeline. |
| **DECISION** | **KEEP ISOLATED** — Good mathematical foundation, not needed in core. |

### 1.5 JointRecommendation

| Field | Value |
|-------|-------|
| **CAPABILITY** | JointRecommendation |
| **PURPOSE** | Combine carrier + route into explainable recommendation |
| **CURRENT LOCATION** | `domain/logistics_joint_recommendation.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `CarrierRouteRecommendation` (Pydantic BaseModel) |
| **DEPENDENCIES** | `CarrierMatching`, `RouteRecommendation`, `logistics_contracts` |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | MEDIUM — Explainability layer. Could feed into Decision Engine. |
| **COMPLEXITY** | MEDIUM — Depends on CarrierMatching + RouteRecommendation. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 179 lines, confidence scoring, HITL routing, structured explanation |
| **INTEGRATION PROPOSAL** | DEFER. Could be integrated after Decision Engine is connected. |
| **DECISION** | **DEFER** — Depends on other integrations first. |

### 1.6 LogisticsRiskManager

| Field | Value |
|-------|-------|
| **CAPABILITY** | LogisticsRiskManager |
| **PURPOSE** | Risk assessment, HITL routing, audit trail for logistics |
| **CURRENT LOCATION** | `domain/logistics_risk_automation.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `ShipmentProfile` → `dict[str, Any]` |
| **DEPENDENCIES** | `ShipmentClassification`, `logistics_contracts` |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Duplicates existing AutomationEvaluator functionality. |
| **COMPLEXITY** | LOW — Standalone module. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 195 lines, risk assessment, HITL routing, audit trail |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Duplicates AutomationEvaluator. Risk assessment already in pipeline. |
| **DECISION** | **KEEP ISOLATED** — Redundant with existing pipeline. |

### 1.7 LogisticsEvaluation

| Field | Value |
|-------|-------|
| **CAPABILITY** | LogisticsEvaluation |
| **PURPOSE** | Synthetic dataset generation and evaluation metrics |
| **CURRENT LOCATION** | `domain/logistics_evaluation.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | `LogisticsEvaluation` class |
| **DEPENDENCIES** | `random` (stdlib only) |
| **CURRENT TESTS** | 0 dedicated tests |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Evaluation infrastructure, not runtime. |
| **COMPLEXITY** | LOW — Standalone module. |
| **RISK** | LOW — Evaluation only, no runtime impact. |
| **EVIDENCE** | 144 lines, synthetic data generation, evaluation metrics |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Evaluation infrastructure should stay separate from runtime. |
| **DECISION** | **KEEP ISOLATED** — Evaluation infrastructure. |

---

## 2. ML Adaptation

### 2.1 Training Abstraction

| Field | Value |
|-------|-------|
| **CAPABILITY** | Training Abstraction |
| **PURPOSE** | Abstract interfaces for ModelAdapter, TrainingPipeline, InferenceEngine |
| **CURRENT LOCATION** | `ml/training_abstraction.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | ABCs: ModelAdapter, TrainingPipeline, InferenceEngine, EvaluationRunner |
| **DEPENDENCIES** | `abc` (stdlib only) |
| **CURRENT TESTS** | test_ml_adaptation.py (26 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Abstract interfaces only. No concrete implementations. |
| **COMPLEXITY** | LOW — Pure abstractions. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Abstract base classes, no concrete logic |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Useful as reference for future ML work. |
| **DECISION** | **KEEP ISOLATED** — Abstract only, no concrete value for pipeline. |

### 2.2 Dataset Contracts

| Field | Value |
|-------|-------|
| **CAPABILITY** | Dataset Contracts |
| **PURPOSE** | Pydantic models for TrainingExample, TrainingDataset, Provenance |
| **CURRENT LOCATION** | `ml/dataset_contracts.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | TrainingExample, TrainingDataset, Provenance, DatasetConfig |
| **DEPENDENCIES** | `pydantic` |
| **CURRENT TESTS** | test_ml_adaptation.py (26 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — ML-specific contracts. Not needed by core pipeline. |
| **COMPLEXITY** | LOW — Pure data models. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Pydantic models for ML data management |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. ML-specific, not needed by core. |
| **DECISION** | **KEEP ISOLATED** — ML-specific contracts. |

### 2.3 LoRA Config

| Field | Value |
|-------|-------|
| **CAPABILITY** | LoRA Config |
| **PURPOSE** | Configuration models for LoRA/QLoRA fine-tuning |
| **CURRENT LOCATION** | `ml/lora_config.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | LoRAConfig, TrainingConfig, AdapterMetadata |
| **DEPENDENCIES** | `pydantic` |
| **CURRENT TESTS** | test_ml_adaptation.py (26 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — ML-specific config. Not needed by core pipeline. |
| **COMPLEXITY** | LOW — Pure data models. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Pydantic models for LoRA configuration |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. ML-specific, not needed by core. |
| **DECISION** | **KEEP ISOLATED** — ML-specific config. |

### 2.4 Adapters (Mock)

| Field | Value |
|-------|-------|
| **CAPABILITY** | Mock Adapters |
| **PURPOSE** | Mock/null implementations for testing |
| **CURRENT LOCATION** | `ml/adapters.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | MockAdapter, NullAdapter, NullInferenceEngine |
| **DEPENDENCIES** | `ml/training_abstraction.py` |
| **CURRENT TESTS** | test_ml_adaptation.py (26 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Test doubles only. |
| **COMPLEXITY** | LOW — Simple mock implementations. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Mock/null implementations for testing |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Test infrastructure. |
| **DECISION** | **KEEP ISOLATED** — Test doubles. |

### 2.5 Evaluation Framework

| Field | Value |
|-------|-------|
| **CAPABILITY** | ML Evaluation Framework |
| **PURPOSE** | Deterministic evaluation runner for ML models |
| **CURRENT LOCATION** | `ml/evaluation.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | DeterministicEvaluationRunner |
| **DEPENDENCIES** | `ml/training_abstraction.py` |
| **CURRENT TESTS** | test_ml_adaptation.py (26 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Evaluation infrastructure only. |
| **COMPLEXITY** | LOW — Simple implementation. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Deterministic evaluation runner |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Evaluation infrastructure. |
| **DECISION** | **KEEP ISOLATED** — Evaluation infrastructure. |

---

## 3. Specialist Models

### 3.1 Specialist Interfaces

| Field | Value |
|-------|-------|
| **CAPABILITY** | Specialist Model Interfaces |
| **PURPOSE** | Abstract SpecialistModel ABC with predict, predict_batch, health_check |
| **CURRENT LOCATION** | `ml/specialist_models.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | SpecialistModel (ABC), SpecialistPrediction, ModelCapability |
| **DEPENDENCIES** | `ml/specialist_contracts.py` |
| **CURRENT TESTS** | test_specialist_models.py (21 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | MEDIUM — Well-defined interface for future specialist integration. |
| **COMPLEXITY** | LOW — Abstract interface. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | Clean ABC design, Pydantic contracts |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Interface is ready, but no real models to integrate yet. |
| **DECISION** | **KEEP ISOLATED** — Interface ready, no concrete models. |

### 3.2 Classification/Risk/Routing Specialists

| Field | Value |
|-------|-------|
| **CAPABILITY** | Keyword-based Specialist Models |
| **PURPOSE** | Simple keyword-based classification, risk, routing |
| **CURRENT LOCATION** | `ml/specialist_models.py` |
| **CURRENT LAYER** | ML (isolated) |
| **PUBLIC CONTRACTS** | ClassificationSpecialist, RiskSpecialist, RoutingSpecialist |
| **DEPENDENCIES** | `ml/specialist_models.py` (base class) |
| **CURRENT TESTS** | test_specialist_models.py (21 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Keyword-based, not real ML. No better than existing rules. |
| **COMPLEXITY** | LOW — Simple implementations. |
| **RISK** | LOW — No runtime impact. |
| **EVIDENCE** | 285 lines, keyword matching, no real ML |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Not better than existing deterministic rules. |
| **DECISION** | **KEEP ISOLATED** — Keyword-based, no real ML value. |

---

## 4. Hybrid Decision Engine

| Field | Value |
|-------|-------|
| **CAPABILITY** | HybridDecisionEngine |
| **PURPOSE** | Combine LLM + specialist + rules + evidence + risk into final decision |
| **CURRENT LOCATION** | `hybrid/decision_engine.py` |
| **CURRENT LAYER** | Hybrid (isolated) |
| **PUBLIC CONTRACTS** | HybridDecision, DecisionComponent, DecisionRule |
| **DEPENDENCIES** | `pydantic` |
| **CURRENT TESTS** | test_hybrid_decision.py (18 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | HIGH — Core architecture for future hybrid decisions. |
| **COMPLEXITY** | HIGH — Would replace/extend existing ReliabilityPipeline + AutomationEvaluator. |
| **RISK** | HIGH — Could break existing pipeline if integrated incorrectly. |
| **EVIDENCE** | 245 lines, multi-source reconciliation, HITL routing, audit trail |
| **INTEGRATION PROPOSAL** | DEFER. Architecture is sound but integration is high-risk. Needs careful design. |
| **DECISION** | **DEFER** — High value but high risk. Needs architectural decision. |

---

## 5. Real Estate Domain

| Field | Value |
|-------|-------|
| **CAPABILITY** | RealEstatePolicy |
| **PURPOSE** | Domain policy for real estate operations |
| **CURRENT LOCATION** | `domain/real_estate_policy.py` |
| **CURRENT LAYER** | Domain (isolated) |
| **PUBLIC CONTRACTS** | RealEstatePolicy (DomainPolicy), RealEstateAutomationPolicy (AutomationPolicy) |
| **DEPENDENCIES** | `ports/domain.py`, `ports/automation.py`, `contracts/` |
| **CURRENT TESTS** | test_real_estate_domain.py (28 tests) |
| **PIPELINE INTEGRATION** | NOT REGISTERED in DomainRegistry |
| **VALUE** | MEDIUM — Demonstrates domain-agnostic architecture. |
| **COMPLEXITY** | LOW — Just register in composition.py. |
| **RISK** | LOW — Additive, doesn't change existing domains. |
| **EVIDENCE** | 287 lines, proper DomainPolicy implementation, 28 tests |
| **INTEGRATION PROPOSAL** | INTEGRATE. Simple registration, demonstrates architecture extensibility. |
| **DECISION** | **INTEGRATE** — Low complexity, demonstrates domain-agnostic design. |

---

## 6. Governance Framework

| Field | Value |
|-------|-------|
| **CAPABILITY** | SecurityManager, ComplianceManager, GovernanceFramework |
| **PURPOSE** | Security event logging, compliance validation, RBAC |
| **CURRENT LOCATION** | `governance/__init__.py` |
| **CURRENT LAYER** | Governance (isolated) |
| **PUBLIC CONTRACTS** | SecurityManager, ComplianceManager, GovernanceFramework |
| **DEPENDENCIES** | `pydantic` |
| **CURRENT TESTS** | test_governance.py (28 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Standalone governance utilities. Not connected to pipeline. |
| **COMPLEXITY** | MEDIUM — Would need to be wired into API/pipeline. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 287 lines, security events, compliance validation, RBAC |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Useful as standalone utilities, not critical for pipeline. |
| **DECISION** | **KEEP ISOLATED** — Standalone utilities. |

---

## 7. Production Readiness

| Field | Value |
|-------|-------|
| **CAPABILITY** | CircuitBreaker, RateLimiter, LoadBalancer, HealthChecker |
| **PURPOSE** | Fault tolerance, rate limiting, health checks |
| **CURRENT LOCATION** | `production/__init__.py` |
| **CURRENT LAYER** | Production (isolated) |
| **PUBLIC CONTRACTS** | CircuitBreaker, RateLimiter, LoadBalancer, HealthChecker, ProductionReadiness |
| **DEPENDENCIES** | `pydantic` |
| **CURRENT TESTS** | test_production.py (28 tests) |
| **PIPELINE INTEGRATION** | NOT INTEGRATED |
| **VALUE** | LOW — Standalone utilities. Not connected to pipeline. |
| **COMPLEXITY** | MEDIUM — Would need to be wired into API layer. |
| **RISK** | LOW — Standalone module. |
| **EVIDENCE** | 287 lines, circuit breaker, rate limiter, health checks |
| **INTEGRATION PROPOSAL** | KEEP ISOLATED. Useful as standalone utilities, not critical for pipeline. |
| **DECISION** | **KEEP ISOLATED** — Standalone utilities. |

---

## Integration Priority Summary

| Priority | Capability | Decision | Rationale |
|----------|-----------|----------|-----------|
| **1** | ShipmentUnderstanding | INTEGRATE | High value, low complexity, low risk |
| **2** | RealEstatePolicy | INTEGRATE | Low complexity, demonstrates domain-agnostic design |
| **3** | HybridDecisionEngine | DEFER | High value but high risk, needs architectural decision |
| **4** | ShipmentClassification | KEEP ISOLATED | Good baseline for future specialist comparison |
| **5** | CarrierMatching | KEEP ISOLATED | Useful but not critical |
| **6** | RouteRecommendation | KEEP ISOLATED | Mathematical logic, stay separate |
| **7** | JointRecommendation | DEFER | Depends on other integrations |
| **8** | LogisticsRiskManager | KEEP ISOLATED | Redundant with existing pipeline |
| **9** | LogisticsEvaluation | KEEP ISOLATED | Evaluation infrastructure |
| **10** | ML Adaptation (all) | KEEP ISOLATED | Abstract interfaces, no concrete models |
| **11** | Specialist Models | KEEP ISOLATED | Keyword-based, no real ML |
| **12** | Governance | KEEP ISOLATED | Standalone utilities |
| **13** | Production | KEEP ISOLATED | Standalone utilities |

---

## Recommended First Integration

**ShipmentUnderstanding** — the first component to integrate.

**Why:**
- High value: Pre-processes logistics cases before LLM, improving decision quality
- Low complexity: Standalone regex parser, no external dependencies
- Low risk: Pure function, no side effects, doesn't change existing pipeline
- Demonstrates: How domain-specific understanding can complement general CASE pipeline

**How:**
1. Add `ShipmentUnderstanding` to composition.py
2. Call `understand()` before TriageEngine for logistics cases
3. Pass structured `ShipmentProfile` as metadata to TriageEngine
4. No changes to TriageEngine itself (metadata passthrough)

**Second Integration:**
RealEstatePolicy — just register in DomainRegistry. Demonstrates domain-agnostic architecture.
