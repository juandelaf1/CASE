import httpx, json, time

TIER1_SYSTEM = """/no_think
You are CASE, an AI Decision Platform for operational case triage.
Your task is to analyze the provided case and evidence, then return a structured decision.
You MUST respond with a valid JSON object matching this schema:
{
    "decision": "approve" | "reject" | "escalate",
    "reason": "string explaining the decision",
    "urgency": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "confidence": float between 0.0 and 1.0,
    "evidence_summary": "string summarizing evidence analysis"
}
Do NOT include any text outside the JSON object."""

user_content = """Domain: urban_operations
Valid evidence types: text, image, file, metric, rule

Case ID: URB-001
Report: Street light damaged on Main Street, near intersection with Oak Avenue.

Evidence:
  1. [text] Citizen report: street light broken (source: citizen_311, confidence: 0.9)

Analyze this case and provide your decision."""

start = time.time()
payload = {
    "model": "qwen3:4b",
    "messages": [
        {"role": "system", "content": TIER1_SYSTEM},
        {"role": "user", "content": user_content}
    ],
    "stream": False,
    "format": {
        "type": "object",
        "properties": {
            "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
            "reason": {"type": "string"},
            "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
            "confidence": {"type": "number"},
            "evidence_summary": {"type": "string"}
        },
        "required": ["decision", "reason", "urgency", "confidence", "evidence_summary"]
    },
    "options": {"temperature": 0.0, "num_predict": 2048}
}

with httpx.Client(timeout=300.0) as client:
    resp = client.post("http://localhost:11434/api/chat", json=payload)
    data = resp.json()

elapsed = time.time() - start
content = data.get("message", {}).get("content", "")
thinking = data.get("message", {}).get("thinking", "")
print(f"Elapsed: {elapsed:.1f}s")
print(f"Content length: {len(content)}")
print(f"Content: {content[:800]}")
print(f"Thinking length: {len(thinking)}")
print(f"Done: {data.get('done')}")
print(f"Eval count: {data.get('eval_count')}")
print(f"Prompt eval: {data.get('prompt_eval_count')}")
