# CASE — AI Decision Platform

> Domain-agnostic, provider-agnostic AI Decision Platform for operational case triage with human oversight.

---

## What is CASE?

CASE (Case Assessment and Structured Evaluation) is an orchestration layer that transforms unstructured operational cases into structured, validated, evidence-backed decisions. It does **not** make autonomous decisions — it proposes, validates, assesses risk, and routes to human review when needed.

**What CASE is:**
- An orchestration layer between raw LLM output and business decisions
- A validation pipeline that never trusts raw LLM output
- A risk-based automation system with human oversight (HITL)
- A domain-agnostic framework supporting multiple operational domains

**What CASE is NOT:**
- Not a fine-tuned model
- Not a RAG system
- Not an agent framework
- Not a real-time production system
- Not an autonomous decision-maker

---

## Problem CASE Solves

Operational teams receive unstructured cases (reports, incidents, requests) that need structured evaluation: What should we do? How urgent is it? What evidence supports the decision? Is this safe to automate, or should a human review it?

CASE provides:
1. **Structured output** from unstructured input via LLM
2. **Multi-stage validation** (schema, semantic, domain, security)
3. **Risk-based automation** — safe cases auto-approved, risky cases to humans
4. **Full audit trail** — every decision is traceable
5. **Human-in-the-loop** — humans can approve, reject, modify, or escalate

---

## Architecture

```text
Streamlit (display only)
   ↓
FastAPI (HTTP adapter)
   ↓
Composition Root (dependency wiring)
   ↓
TriageEngine (application layer orchestrator)
   ↓
DomainRegistry → DomainPolicy (domain resolution)
   ↓
PromptBuilder → LLMProvider (via port)
   ↓
ReliabilityPipeline (parse → schema → semantic → domain → retry → repair)
   ↓
AutomationEvaluator (risk assessment → AUTO_APPROVE / HUMAN_REVIEW / ESCALATE)
   ↓
DecisionRepositoryPort (persistence)
   ↓
AuditPort (audit trail)
```

### Key Components

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **Contracts** | Pydantic v2 schemas | Type-safe data models for all domain objects |
| **Ports** | ABC interfaces | LLMProvider, DomainPolicy, AuditPort, RepositoryPort, AutomationPolicy |
| **Domain** | DomainRegistry + DomainPacks | Domain-specific validation, urgency classification, routing |
| **Providers** | Mock, Ollama, Cloud | LLM provider implementations behind LLMProvider port |
| **Reliability** | ReliabilityPipeline | JSON parse → schema validate → semantic validate → domain validate → retry → repair |
| **Automation** | AutomationEvaluator | Risk assessment, conservative automation with HITL fallback |
| **Application** | TriageEngine | Orchestrates the full triage flow |
| **API** | FastAPI endpoints | HTTP interface, delegates to TriageEngine |
| **Persistence** | SQLite adapters | Decision storage, audit trail, HITL queue |

---

## Decision Flow

```text
Case arrives
  → LLM proposes decision (approve/reject/escalate)
  → ReliabilityPipeline validates output
     → JSON parse check
     → Schema validation (required fields, enums, confidence range)
     → Semantic validation (reason length, evidence quality)
     → Domain validation (policy-specific evidence requirements)
     → Retry on transient failures (max 2 retries)
     → Retry on validation failures (max 3 retries)
     → Terminal failure if exhausted
  → AutomationEvaluator assesses risk
     → Risk signals: confidence, evidence quality, policy violations, domain complexity
     → Effective urgency: max(LLM urgency, case urgency) — prevents downgrade
  → Decision produced
     → AUTO_APPROVE: low risk, sufficient evidence, valid schema
     → HUMAN_REVIEW: ambiguous, medium risk, or insufficient evidence
     → ESCALATE: critical risk, policy violation, or schema failure
  → Persisted to database
  → Audit event logged
```

---

## Automation — Risk-Based Decision Routing

CASE uses **risk-based automation**, not full autonomy. The system classifies each case into one of three outcomes:

### AUTO_APPROVE

Case is safe to automate:
- Decision schema is valid
- Confidence is high
- Evidence quality is sufficient
- No policy violations
- Risk assessment is LOW

### HUMAN_REVIEW

Case requires human judgment:
- Medium risk level
- Ambiguous evidence
- Confidence below threshold
- Domain-specific concerns
- Default for Urban and Infrastructure domains

### ESCALATE

Case is critical and must go to a supervisor:
- Critical risk level
- Policy violation detected
- Schema validation failed after retries
- Evidence quality critically low

**Conservative by design:** When in doubt, CASE routes to humans. The system is designed to err on the side of human review rather than automated action.

---

## Supported Domains

| Domain | Policy | Routing | Automation | Bias Pairs |
|--------|--------|---------|------------|------------|
| **Logistics** | Full | 6 incident types | LogisticsAutomationPolicy (5 departments) | 10 pairs |
| **Urban Operations** | Partial | Generic | DefaultAutomationPolicy (conservative) | 0 |
| **Infrastructure** | Partial | Generic | DefaultAutomationPolicy (conservative) | 0 |

### Logistics Domain Pack

- **Incident Types:** delivery_delay, delivery_failure, stock_issue, warehouse_delay, damaged_goods, transport_disruption
- **Departments:** logistics, warehouse, fleet, operations, customer_service
- **Recommended Actions:** Per incident type, per department
- **Automation:** Full risk-based automation with domain-specific rules

### Urban Operations

- Evidence validation: requires 1 text evidence
- Urgency classification: keyword-based
- Automation: DefaultAutomationPolicy (conservative, HUMAN_REVIEW default)

### Infrastructure

- Evidence validation: requires non-empty evidence
- Urgency classification: keyword-based
- Automation: DefaultAutomationPolicy (conservative, HUMAN_REVIEW default)

---

## Providers

| Provider | Type | Use Case |
|----------|------|----------|
| **MockProvider** | Deterministic | Testing, demo, evaluation |
| **OllamaProvider** | Local LLM | Development, offline evaluation |
| **CloudProvider** | API-based | Production (requires API key) |

All providers implement the `LLMProvider` port. Swapping providers requires zero changes to core logic.

---

## Installation

### Prerequisites

- Python 3.11+
- pip or conda

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd CASE

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests
pytest tests/ -v

# Check code quality
ruff check src tests
mypy src
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OPENAI_API_KEY` | — | Cloud provider API key |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Cloud provider base URL |
| `CASE_DB_PATH` | `case.db` | SQLite database path |

### Switching Providers

In `src/case_core/composition.py`:

```python
# Default: MockProvider (for testing/demo)
provider: LLMProvider = MockProvider()

# For Ollama:
from case_core.providers.ollama import OllamaProvider
provider = OllamaProvider(model="llama3.2")

# For Cloud (OpenAI-compatible):
from case_core.providers.cloud import CloudProvider
provider = CloudProvider(api_key="your-key")
```

---

## Running

### API Server

```bash
uvicorn case_api.api.v1.app:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Streamlit UI

```bash
cd streamlit_app
streamlit run app.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/domains` | GET | List registered domains |
| `/api/v1/triage` | POST | Submit a case for triage |
| `/api/v1/audit/{case_id}` | GET | Get audit events for a case |
| `/api/v1/hitl/pending` | GET | List decisions pending human review |
| `/api/v1/hitl/{decision_id}` | GET | Get a specific decision |
| `/api/v1/hitl/{decision_id}/under-review` | POST | Start human review |
| `/api/v1/hitl/{decision_id}/approve` | POST | Approve a decision |
| `/api/v1/hitl/{decision_id}/reject` | POST | Reject a decision |
| `/api/v1/hitl/{decision_id}/escalate` | POST | Escalate a decision |
| `/api/v1/hitl/{decision_id}/modify` | POST | Modify a decision |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/unit/test_behavioral.py -v
pytest tests/integration/test_api.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Test Summary

| Suite | Tests | Description |
|-------|-------|-------------|
| Behavioral | 79 | End-to-end behavioral scenarios (BS001-BS030) |
| Contracts | 23 | Pydantic schema validation |
| Domain | 38 | Domain policy, registry, urgency |
| Reliability | 26 | Pipeline validation, retry, timeout |
| Security | 31 | Prompt injection, schema manipulation |
| Bias | 14 | Decision invariance across counterfactuals |
| Regression | 15 | Normal, edge, failure, injection cases |
| Mock Provider | 30 | MockProvider scenarios and contracts |
| Ollama Provider | 13 | Ollama contract and error mapping |
| Cloud Provider | 28 | Cloud provider contract and errors |
| API | 11 | Integration tests for all endpoints |
| Triage Engine | 25 | Engine orchestration and automation |
| Ports/Prompts/SQLite | 45 | Interface, prompt, persistence tests |
| Governance | 28 | Security, compliance (isolated) |
| Production | 28 | Circuit breaker, rate limiter (isolated) |
| Hybrid Decision | 18 | Decision engine (isolated) |
| Specialist Models | 21 | Keyword-based specialists (isolated) |
| ML Adaptation | 26 | Training abstractions (isolated) |
| Real Estate | 28 | Domain policy (isolated) |
| Streamlit | 2 | Boundary tests |

**Total: 526 passed, 7 skipped (Ollama integration), 0 failed**

---

## Evaluation

CASE includes an evaluation framework for measuring decision quality:

```python
from case_core.evaluation.runner import EvaluationRunner

runner = EvaluationRunner(provider=MockProvider())
results = runner.run_dataset("logistics_normal_cases")
```

### Metrics

- Decision accuracy
- Urgency accuracy
- Average confidence
- Processing time
- Error rate
- Pair consistency rate (bias)
- Decision invariance rate (bias)
- Routing invariance rate (bias)

### Bias Evaluation

10 counterfactual pairs testing whether irrelevant attribute changes (supplier name, customer name, wording, etc.) alter decision outcomes. Currently covers Logistics domain only.

---

## Examples

See `examples/` directory:

- `demo_auto_approve.py` — Low-risk case → AUTO_APPROVE
- `demo_human_review.py` — Ambiguous case → HUMAN_REVIEW
- `demo_escalate.py` — Critical case → ESCALATE
- `demo_invalid_output.py` — Invalid LLM output → validation failure
- `demo_hitl_lifecycle.py` — Full HITL workflow
- `demo_all_domains.py` — Cases across all three domains

Run any example:

```bash
python examples/demo_auto_approve.py
```

---

## Limitations

### Scope Limitations

| Limitation | Status | Impact |
|------------|--------|--------|
| MockProvider primary evidence source | Active | All evaluations use synthetic responses |
| Ollama integration not always available | Active | Local LLM requires Ollama running |
| Real LLM behavior not fully validated | Active | Security/bias tested only with MockProvider |
| No production deployment | By design | Academic/portfolio project |
| No authentication/authorization | By design | Not needed for demo |
| No rate limiting | By design | Not needed for demo |
| No performance/load testing | By design | Not needed for demo |

### Domain Limitations

| Limitation | Status | Impact |
|------------|--------|--------|
| Bias pairs logistics-only | Active | 0 pairs for Urban/Infrastructure |
| No Urban/Infrastructure routing | Active | Uses generic classify_urgency only |
| Generic automation for Urban/Infrastructure | Active | DefaultAutomationPolicy, not domain-specific |
| No Urban/Infrastructure bias evaluation | Active | Cannot measure invariance for these domains |

### Technical Limitations

| Limitation | Status | Impact |
|------------|--------|--------|
| SQLite only | Active | No concurrent production use |
| No multi-tenant support | By design | Single-tenant demo |
| No streaming responses | By design | Synchronous triage only |
| No monitoring/observability | By design | Audit trail only |
| OperationalTelemetry/LLMTelemetry unused | Active | Prepared for future observability |

### Isolated Modules

The following modules are implemented and tested but NOT connected to the running pipeline:

| Module | Description |
|--------|-------------|
| Logistics Intelligence | Shipment classification, routing, carrier matching |
| ML Adaptation | Training abstractions, dataset pipeline |
| Specialist Models | Keyword-based classification/risk/routing |
| Hybrid Decision Engine | Multi-source decision combination |
| Real Estate Domain | Domain policy (not registered) |
| Governance | Security, compliance, access control |
| Production | Circuit breaker, rate limiter, health checks |

These demonstrate the architecture's extensibility. Wiring them requires explicit decision.

---

## Project Structure

```text
CASE/
├── src/
│   ├── case_core/
│   │   ├── application/     # TriageEngine
│   │   ├── contracts/       # Pydantic v2 schemas (9 files)
│   │   ├── domain/          # DomainRegistry, DomainPacks
│   │   ├── evaluation/      # Runner, metrics, reports, scenarios
│   │   ├── ports/           # ABC interfaces (6 ports)
│   │   ├── prompts/         # PromptBuilder
│   │   ├── providers/       # Mock, Ollama, Cloud
│   │   ├── reliability/     # Validation pipeline, automation evaluator
│   │   └── composition.py   # Dependency wiring
│   ├── case_api/
│   │   └── api/v1/          # FastAPI endpoints
│   └── case_infra/
│       └── persistence/     # SQLite adapters
├── tests/
│   ├── unit/                # 18 test files
│   └── integration/         # 2 test files
├── examples/                # Demo scripts
├── streamlit_app/           # Streamlit UI
├── docs/                    # Documentation
├── pyproject.toml           # Project configuration
└── README.md                # This file
```

---

## Development

### Code Quality

```bash
# Linting
ruff check src tests

# Type checking
mypy src

# Formatting
ruff format src tests
```

### Quality Gates

After any code change, all of the following must pass:

```bash
pytest tests/ -q           # 0 failures
ruff check src tests       # 0 errors
mypy src                   # 0 errors
```

---

## License

MIT — See [LICENSE](LICENSE) for details.

---

## Credits

CASE is an academic/portfolio project demonstrating:
- Domain-agnostic AI decision orchestration
- Risk-based automation with human oversight
- Multi-stage LLM output validation
- Security-aware prompt engineering
- Bias evaluation through counterfactual analysis
