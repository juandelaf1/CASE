import httpx, json, time

SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
        "reason": {"type": "string"},
        "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
        "confidence": {"type": "number"},
        "evidence_summary": {"type": "string"}
    },
    "required": ["decision", "reason", "urgency", "confidence", "evidence_summary"]
}

for model in ["phi4-mini", "gemma3:4b"]:
    print(f"\n=== {model} ===")
    start = time.time()
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post("http://localhost:11434/api/chat", json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are CASE. Respond with valid JSON only."},
                    {"role": "user", "content": "Analyze: street light broken on Main St. Return decision as JSON."}
                ],
                "stream": False,
                "format": SCHEMA,
                "options": {"temperature": 0.0, "num_predict": 512}
            })
            data = resp.json()
        elapsed = time.time() - start
        content = data.get("message", {}).get("content", "")
        thinking = data.get("message", {}).get("thinking", "")
        print(f"  Elapsed: {elapsed:.1f}s")
        print(f"  Done: {data.get('done')}")
        print(f"  Eval count: {data.get('eval_count')}")
        print(f"  Prompt eval: {data.get('prompt_eval_count')}")
        print(f"  Content length: {len(content)}")
        print(f"  Content: {content[:400]}")
        print(f"  Thinking length: {len(thinking)}")
        try:
            parsed = json.loads(content) if content else None
            print(f"  JSON valid: {parsed is not None}")
            if parsed:
                print(f"  Decision: {parsed.get('decision')}")
        except:
            print(f"  JSON valid: False")
    except Exception as e:
        elapsed = time.time() - start
        print(f"  FAILED after {elapsed:.1f}s: {type(e).__name__}: {str(e)[:100]}")
