import httpx, json, time

start = time.time()
payload = {
    "model": "deepseek-r1:8b",
    "messages": [
        {"role": "system", "content": "You are CASE. Respond with JSON only."},
        {"role": "user", "content": 'Return this JSON: {"decision": "approve", "reason": "test reason for approval", "urgency": "LOW", "confidence": 0.5, "evidence_summary": "test evidence"}'}
    ],
    "stream": False,
    "format": {"type": "object", "properties": {"decision": {"type": "string"}}, "required": ["decision"]},
    "options": {"temperature": 0.0, "num_predict": 3072}
}

with httpx.Client(timeout=600.0) as client:
    resp = client.post("http://localhost:11434/api/chat", json=payload)
    data = resp.json()

elapsed = time.time() - start
content = data.get("message", {}).get("content", "")
thinking = data.get("message", {}).get("thinking", "")
print(f"Elapsed: {elapsed:.1f}s")
print(f"Content length: {len(content)}")
print(f"Content: {content[:300]}")
print(f"Thinking length: {len(thinking)}")
print(f"Thinking preview: {thinking[:300]}")
print(f"Done: {data.get('done')}")
print(f"Eval count: {data.get('eval_count')}")
print(f"Prompt eval: {data.get('prompt_eval_count')}")
