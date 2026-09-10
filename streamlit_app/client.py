import os
from typing import Any

import httpx


class CASEClient:
    def __init__(self, base_url: str | None = None, timeout_seconds: float = 30.0) -> None:
        self._base_url = (
            base_url or os.environ.get("CASE_API_BASE_URL", "http://localhost:8000")
        ).rstrip("/")
        self._timeout = timeout_seconds

    @property
    def base_url(self) -> str:
        return self._base_url

    async def health(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/health")
            response.raise_for_status()
            return response.json()

    async def list_domains(self) -> list[str]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(f"{self._base_url}/domains")
            response.raise_for_status()
            data = response.json()
            return data.get("domains", [])

    async def triage(
        self,
        case_id: str,
        report_text: str,
        domain: str,
        urgency: str = "MEDIUM",
        evidence: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "case_id": case_id,
            "report_text": report_text,
            "domain": domain,
            "urgency": urgency,
            "evidence": evidence or [],
            "metadata": metadata or {},
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/triage",
                json=payload,
            )
            if response.status_code == 422:
                detail = response.json().get("detail", {})
                return {"error": True, "detail": detail}
            response.raise_for_status()
            return {"error": False, "data": response.json()}

    async def get_audit_events(self, case_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/audit/{case_id}",
            )
            if response.status_code == 404:
                return {"events": [], "count": 0}
            response.raise_for_status()
            return response.json()

    def health_sync(self) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(f"{self._base_url}/health")
            response.raise_for_status()
            return response.json()

    def list_domains_sync(self) -> list[str]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(f"{self._base_url}/domains")
            response.raise_for_status()
            data = response.json()
            return data.get("domains", [])

    def triage_sync(
        self,
        case_id: str,
        report_text: str,
        domain: str,
        urgency: str = "MEDIUM",
        evidence: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "case_id": case_id,
            "report_text": report_text,
            "domain": domain,
            "urgency": urgency,
            "evidence": evidence or [],
            "metadata": metadata or {},
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/triage",
                json=payload,
            )
            if response.status_code == 422:
                detail = response.json().get("detail", {})
                return {"error": True, "detail": detail}
            response.raise_for_status()
            return {"error": False, "data": response.json()}

    def get_audit_events_sync(self, case_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/api/v1/audit/{case_id}",
            )
            if response.status_code == 404:
                return {"events": [], "count": 0}
            response.raise_for_status()
            return response.json()

    async def list_pending_review(self, limit: int = 100) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/hitl/pending",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

    async def get_decision(self, decision_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/api/v1/hitl/{decision_id}",
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def approve_decision(self, decision_id: str, actor: str = "human", notes: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/approve",
                json={"actor": actor, "notes": notes},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def reject_decision(self, decision_id: str, actor: str = "human", notes: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/reject",
                json={"actor": actor, "notes": notes},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def modify_decision(
        self,
        decision_id: str,
        action: str,
        reason: str,
        urgency: str,
        confidence: float,
        evidence_summary: str,
        actor: str = "human",
        notes: str = "",
        justification: str = "",
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/modify",
                json={
                    "action": action,
                    "reason": reason,
                    "urgency": urgency,
                    "confidence": confidence,
                    "evidence_summary": evidence_summary,
                    "actor": actor,
                    "notes": notes,
                    "justification": justification,
                },
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def start_review(self, decision_id: str, actor: str = "human", justification: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/under-review",
                json={"actor": actor, "justification": justification},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def escalate_decision(self, decision_id: str, actor: str = "human", justification: str = "", escalate_to: str = "supervisor") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/escalate",
                json={"actor": actor, "justification": justification, "escalate_to": escalate_to},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def list_pending_review_sync(self, limit: int = 100) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/api/v1/hitl/pending",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

    def get_decision_sync(self, decision_id: str) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.get(
                f"{self._base_url}/api/v1/hitl/{decision_id}",
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def approve_decision_sync(self, decision_id: str, actor: str = "human", notes: str = "", justification: str = "") -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/approve",
                json={"actor": actor, "notes": notes, "justification": justification},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def reject_decision_sync(self, decision_id: str, actor: str = "human", notes: str = "", justification: str = "") -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/reject",
                json={"actor": actor, "notes": notes, "justification": justification},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def escalate_decision_sync(self, decision_id: str, actor: str = "human", justification: str = "", escalate_to: str = "supervisor") -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/escalate",
                json={"actor": actor, "justification": justification, "escalate_to": escalate_to},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def modify_decision_sync(
        self,
        decision_id: str,
        action: str,
        reason: str,
        urgency: str,
        confidence: float,
        evidence_summary: str,
        actor: str = "human",
        notes: str = "",
        justification: str = "",
    ) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/modify",
                json={
                    "action": action,
                    "reason": reason,
                    "urgency": urgency,
                    "confidence": confidence,
                    "evidence_summary": evidence_summary,
                    "actor": actor,
                    "notes": notes,
                    "justification": justification,
                },
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    async def start_review(self, decision_id: str, actor: str = "human", justification: str = "") -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/under-review",
                json={"actor": actor, "justification": justification},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()

    def start_review_sync(self, decision_id: str, actor: str = "human", justification: str = "") -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(
                f"{self._base_url}/api/v1/hitl/{decision_id}/under-review",
                json={"actor": actor, "justification": justification},
            )
            if response.status_code == 404:
                return {"error": True, "detail": "Decision not found"}
            response.raise_for_status()
            return response.json()
