# CASE Streamlit UI

Streamlit is an MVP dashboard/UI layer, **not part of the CASE decision engine**.

## Architecture

```
Streamlit UI
     ↓ HTTP / JSON
FastAPI API  (port 8000)
     ↓
Application
     ↓
Domain
     ↓
Ports
     ↓
Infrastructure
```

Streamlit communicates exclusively via HTTP. It never imports core, domain, providers, or infrastructure directly.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `CASE_API_BASE_URL` | `http://localhost:8000` | FastAPI backend URL |

## Running

```bash
# 1. Start FastAPI backend
uvicorn case_api.api.v1.app:app --host 0.0.0.0 --port 8000

# 2. Start Streamlit UI
cd streamlit_app
streamlit run app.py
```

## API Dependency

The UI requires these FastAPI endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | System status check |
| `/domains` | GET | List available domains |
| `/api/v1/triage` | POST | Submit case for decision |
| `/api/v1/audit/{case_id}` | GET | Retrieve audit events |

## UI States

| State | Visual | When |
|-------|--------|------|
| Loading | Spinner | Processing request |
| Success | Green metrics + decision card | Valid decision received |
| Error | Red alert | API error / validation failure |
| Manual Review | Yellow warning | requires_manual_review=True |
| Empty | Info message | No data available |
| API Down | Red error | Cannot connect to backend |

## Features

- **Decision Center**: Submit cases and view decisions
- **System Status**: Health check and domain listing
- **Audit Trail**: View audit events per case
- **Error Handling**: All error states visible, no stack traces

## Limitations

- No user authentication
- No conversation/chat interface
- No HITL action endpoints (display only)
- No real-time updates (polling only)
- Single-user MVP

## Future Extensions

When backend exposes HITL endpoints:
- APPROVE / REJECT / MODIFY actions
- Decision review workflow
- Multi-case batch review
