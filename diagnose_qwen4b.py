import httpx, json, time, traceback

print("=== QWEN3:4B DIAGNOSTIC ===\n")

# 1. Check model
import subprocess
r = subprocess.run(["ollama", "list"], capture_output=True, text=True)
print("1. ollama list:")
for line in r.stdout.split("\n"):
    if "qwen" in line.lower():
        print(f"   {line}")
print()

# 2. Minimal API call with full error capture
print("2. Minimal API call (system=short, num_predict=100):")
start = time.time()
try:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post("http://localhost:11434/api/chat", json={
            "model": "qwen3:4b",
            "messages": [{"role": "user", "content": "Say hello in JSON: {\"msg\": \"hello\"}"}],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 100}
        })
        data = resp.json()
    elapsed = time.time() - start
    print(f"   Elapsed: {elapsed:.1f}s")
    print(f"   Done: {data.get('done')}")
    print(f"   Eval count: {data.get('eval_count')}")
    print(f"   Prompt eval: {data.get('prompt_eval_count')}")
    print(f"   Total duration: {data.get('total_duration', 0)/1e9:.1f}s")
    print(f"   Content: {data.get('message', {}).get('content', '')[:200]}")
    print(f"   Thinking: {data.get('message', {}).get('thinking', '')[:100]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"   FAILED after {elapsed:.1f}s")
    print(f"   Exception type: {type(e).__name__}")
    print(f"   Exception msg: {repr(str(e))}")
    print(f"   Full traceback:")
    traceback.print_exc()
print()

# 3. CASE prompt with /no_think
print("3. CASE prompt with /no_think (num_predict=512):")
TIER1 = """/no_think
You are CASE. Respond with valid JSON only.
{"decision": "approve", "reason": "...", "urgency": "LOW", "confidence": 0.5, "evidence_summary": "..."}"""
start = time.time()
try:
    with httpx.Client(timeout=120.0) as client:
        resp = client.post("http://localhost:11434/api/chat", json={
            "model": "qwen3:4b",
            "messages": [
                {"role": "system", "content": TIER1},
                {"role": "user", "content": "Analyze: street light broken. Return decision."}
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
            "options": {"temperature": 0.0, "num_predict": 512}
        })
        data = resp.json()
    elapsed = time.time() - start
    content = data.get("message", {}).get("content", "")
    thinking = data.get("message", {}).get("thinking", "")
    print(f"   Elapsed: {elapsed:.1f}s")
    print(f"   Done: {data.get('done')}")
    print(f"   Eval count: {data.get('eval_count')}")
    print(f"   Prompt eval: {data.get('prompt_eval_count')}")
    print(f"   Content length: {len(content)}")
    print(f"   Content: {content[:500]}")
    print(f"   Thinking length: {len(thinking)}")
    # Try parse
    try:
        parsed = json.loads(content) if content else None
        print(f"   JSON valid: {parsed is not None}")
        if parsed:
            print(f"   Decision: {parsed.get('decision')}")
            print(f"   Urgency: {parsed.get('urgency')}")
    except:
        print(f"   JSON valid: False")
except Exception as e:
    elapsed = time.time() - start
    print(f"   FAILED after {elapsed:.1f}s")
    print(f"   Exception type: {type(e).__name__}")
    print(f"   Exception msg: {repr(str(e))}")
    traceback.print_exc()
print()

# 4. Same call with thinking=true, num_predict=2048
print("4. CASE prompt thinking ON (num_predict=2048):")
start = time.time()
try:
    with httpx.Client(timeout=300.0) as client:
        resp = client.post("http://localhost:11434/api/chat", json={
            "model": "qwen3:4b",
            "messages": [
                {"role": "system", "content": "You are CASE. Respond with valid JSON only."},
                {"role": "user", "content": "Analyze: street light broken. Return decision as JSON."}
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
        })
        data = resp.json()
    elapsed = time.time() - start
    content = data.get("message", {}).get("content", "")
    thinking = data.get("message", {}).get("thinking", "")
    print(f"   Elapsed: {elapsed:.1f}s")
    print(f"   Done: {data.get('done')}")
    print(f"   Eval count: {data.get('eval_count')}")
    print(f"   Prompt eval: {data.get('prompt_eval_count')}")
    print(f"   Content length: {len(content)}")
    print(f"   Content: {content[:500]}")
    print(f"   Thinking length: {len(thinking)}")
    try:
        parsed = json.loads(content) if content else None
        print(f"   JSON valid: {parsed is not None}")
    except:
        print(f"   JSON valid: False")
except Exception as e:
    elapsed = time.time() - start
    print(f"   FAILED after {elapsed:.1f}s")
    print(f"   Exception type: {type(e).__name__}")
    print(f"   Exception msg: {repr(str(e))}")
    traceback.print_exc()
print()

print("=== DIAGNOSIS COMPLETE ===")
