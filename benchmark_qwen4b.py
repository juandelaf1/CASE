"""
Qwen3 4B Mini Benchmark — 5 cases, incremental persistence.
"""
import asyncio
import json
import re
import statistics
import time
from pathlib import Path

import httpx

OLLAMA_BASE_URL = "http://localhost:11434"
API_TIMEOUT = 300
MAX_RETRIES = 3
BACKOFF_BASE = 1

DECISION_FIELDS = {"decision", "reason", "urgency", "confidence", "evidence_summary"}
VALID_DECISIONS = {"approve", "reject", "escalate"}
VALID_URGENCIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}

TIER1_SYSTEM = """You are CASE, an AI Decision Platform for operational case triage.
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

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
        "reason": {"type": "string"},
        "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "confidence": {"type": "number"},
        "evidence_summary": {"type": "string"},
    },
    "required": ["decision", "reason", "urgency", "confidence", "evidence_summary"],
}

# 5 cases: 2 normal, 1 edge, 1 failure/repair, 1 multi-evidence
MINI_CASES = [
    {
        "case_id": "MINI-001",
        "report_text": "Street light damaged on Main Street, near intersection with Oak Avenue.",
        "domain": "urban_operations",
        "urgency": "MEDIUM",
        "evidence": [{"id": "ev-1", "type": "text", "content": "Citizen report: street light broken", "source": "citizen_311", "confidence": 0.9}],
        "expected_decision": "approve",
        "expected_urgency": "MEDIUM"
    },
    {
        "case_id": "MINI-002",
        "report_text": "Pothole on Highway 101 southbound lane, causing traffic slowdown.",
        "domain": "urban_operations",
        "urgency": "HIGH",
        "evidence": [{"id": "ev-2", "type": "text", "content": "Traffic report: pothole on highway", "source": "traffic_dept", "confidence": 0.95}],
        "expected_decision": "escalate",
        "expected_urgency": "HIGH"
    },
    {
        "case_id": "MINI-003",
        "report_text": "Missing manhole cover on Elm Street near school zone. Open hole in roadway.",
        "domain": "urban_operations",
        "urgency": "CRITICAL",
        "evidence": [{"id": "ev-3", "type": "text", "content": "Police report: missing manhole cover, hazard cones placed", "source": "police_dispatch", "confidence": 0.99}],
        "expected_decision": "escalate",
        "expected_urgency": "CRITICAL"
    },
    {
        "case_id": "MINI-004",
        "report_text": "Overflowing public trash can near bus stop. Litter scattered.",
        "domain": "urban_operations",
        "urgency": "LOW",
        "evidence": [{"id": "ev-4", "type": "text", "content": "Bus driver: trash can full, overflow on sidewalk", "source": "transit_dept", "confidence": 0.87}],
        "expected_decision": "approve",
        "expected_urgency": "LOW"
    },
    {
        "case_id": "MINI-005",
        "report_text": "Traffic signal malfunction at Main and 1st intersection. Light stuck on yellow.",
        "domain": "urban_operations",
        "urgency": "CRITICAL",
        "evidence": [
            {"id": "ev-5a", "type": "text", "content": "Multiple driver reports: signal malfunction", "source": "citizen_311", "confidence": 0.94},
            {"id": "ev-5b", "type": "text", "content": "Traffic engineering: signal controller failure confirmed", "source": "traffic_dept", "confidence": 0.97}
        ],
        "expected_decision": "escalate",
        "expected_urgency": "CRITICAL"
    },
]

RESULTS_PATH = Path(r"C:\Users\JUAN\Desktop\Proyectos\CASE\evaluation\benchmark_results\qwen3_4b_mini.json")


def build_user_content(case):
    evidence_lines = []
    for i, ev in enumerate(case.get("evidence", []), 1):
        evidence_lines.append(f"  {i}. [{ev.get('type', 'text')}] {ev.get('content', '')} (source: {ev.get('source', 'dataset')}, confidence: {ev.get('confidence', 0.9)})")
    evidence_text = "\n".join(evidence_lines) if evidence_lines else "No evidence provided."
    return f"""Domain: urban_operations
Valid evidence types: text, image, file, metric, rule

Case ID: {case['case_id']}
Report: {case['report_text']}

Evidence:
{evidence_text}

Analyze this case and provide your decision."""


def extract_json(text):
    if not text:
        return ""
    # Try direct parse
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    # Try code fence
    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            json.loads(match.group(1).strip())
            return match.group(1).strip()
        except json.JSONDecodeError:
            pass
    # Try first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass
    return ""


def validate(data):
    missing = DECISION_FIELDS - set(data.keys())
    if missing:
        return False, f"SCHEMA: Missing {missing}"
    if data.get("decision") not in VALID_DECISIONS:
        return False, f"SCHEMA: Invalid decision: {data.get('decision')}"
    if data.get("urgency") not in VALID_URGENCIES:
        return False, f"SCHEMA: Invalid urgency: {data.get('urgency')}"
    if not isinstance(data.get("confidence"), (int, float)):
        return False, "SCHEMA: Confidence not a number"
    if not (0.0 <= data["confidence"] <= 1.0):
        return False, f"SCHEMA: Confidence out of range"
    if not data.get("reason") or len(data["reason"].strip()) < 10:
        return False, "SEMANTIC: Reason too short"
    if not data.get("evidence_summary") or len(data["evidence_summary"].strip()) < 5:
        return False, "SEMANTIC: Evidence summary too short"
    return True, ""


def save_result(result):
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            existing = json.load(f)
    existing.append(result)
    with open(RESULTS_PATH, "w") as f:
        json.dump(existing, f, indent=2)


async def run_case(model, case):
    result = {
        "model": model,
        "case_id": case["case_id"],
        "expected_decision": case["expected_decision"],
        "expected_urgency": case["expected_urgency"],
    }

    user_content = build_user_content(case)
    messages = [
        {"role": "system", "content": TIER1_SYSTEM},
        {"role": "user", "content": user_content},
    ]

    total_start = time.time()
    attempt = 0
    success = False

    while attempt <= MAX_RETRIES and not success:
        attempt += 1
        gen_start = time.time()
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "format": RESPONSE_SCHEMA,
                "options": {"temperature": 0.0, "num_predict": 2048},
            }
            async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
                resp = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
                resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            result["final_status"] = "provider_error"
            result["error"] = str(e)[:200]
            result["total_latency_ms"] = (time.time() - total_start) * 1000
            save_result(result)
            return result

        gen_latency = (time.time() - gen_start) * 1000
        content = data.get("message", {}).get("content", "")
        thinking = data.get("message", {}).get("thinking", "")

        # Try to extract JSON
        json_str = extract_json(content)
        if not json_str and thinking:
            json_str = extract_json(thinking)

        if json_str:
            try:
                parsed = json.loads(json_str)
                ok, err = validate(parsed)
                if ok:
                    result["actual_decision"] = parsed["decision"]
                    result["actual_urgency"] = parsed["urgency"]
                    result["confidence"] = parsed["confidence"]
                    result["correct_decision"] = parsed["decision"] == case["expected_decision"]
                    result["correct_urgency"] = parsed["urgency"] == case["expected_urgency"]
                    result["final_status"] = "success"
                    result["parse_error"] = ""
                    success = True
                else:
                    result["parse_error"] = err
            except json.JSONDecodeError as e:
                result["parse_error"] = f"PARSE: {e}"
        else:
            result["parse_error"] = "PARSE: No JSON found in response"

        result["thinking_tokens"] = len(thinking) // 4 if thinking else 0
        result["input_tokens"] = data.get("prompt_eval_count", 0)
        result["output_tokens"] = data.get("eval_count", 0)
        result["generation_latency_ms"] = gen_latency

        if not success and attempt <= MAX_RETRIES:
            await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))

    result["total_latency_ms"] = (time.time() - total_start) * 1000
    result["retry_count"] = attempt - 1
    if not success:
        result["final_status"] = "validation_failed"
    save_result(result)
    return result


async def main():
    model = "qwen3:4b"

    # Clear previous results
    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()

    print(f"Qwen3 4B Mini Benchmark — {len(MINI_CASES)} cases")
    print("=" * 60)

    results = []
    for case in MINI_CASES:
        print(f"  [{model}] {case['case_id']}...", end=" ", flush=True)
        r = await run_case(model, case)
        results.append(r)
        print(f"{r['final_status']} ({r['total_latency_ms']:.0f}ms)")

    # Compute metrics
    total = len(results)
    successes = sum(1 for r in results if r["final_status"] == "success")
    correct_dec = sum(1 for r in results if r.get("correct_decision"))
    correct_urg = sum(1 for r in results if r.get("correct_urgency"))
    json_valid = sum(1 for r in results if not r.get("parse_error"))
    latencies = [r["total_latency_ms"] for r in results if r["total_latency_ms"] > 0]

    print(f"\nResults:")
    print(f"  Classification accuracy: {correct_dec}/{total} = {correct_dec/total:.2%}")
    print(f"  Urgency accuracy: {correct_urg}/{total} = {correct_urg/total:.2%}")
    print(f"  Success rate: {successes}/{total} = {successes/total:.2%}")
    print(f"  JSON validity: {json_valid}/{total} = {json_valid/total:.2%}")
    print(f"  Avg latency: {statistics.mean(latencies):.0f}ms")
    print(f"  P50 latency: {statistics.median(latencies):.0f}ms")
    print(f"  Results saved to: {RESULTS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
