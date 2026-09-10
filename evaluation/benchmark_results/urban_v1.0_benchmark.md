==============================================================================
CASE MODEL BENCHMARK — urban_v1.0
==============================================================================

ENVIRONMENT
- OS: Windows (win32)
- Python: 3.x (via opencode)
- Ollama version: 0.32.15
- RAM: 25.4 GB
- GPU: Intel Iris Xe Graphics (2 GB VRAM) — CPU inference
- VRAM: 2 GB (insufficient for GPU offload)

MODELS
- llama3.2:latest (3.2B, Q4_K_M, 2.0 GB)
- qwen3:8b (8.2B, Q4_K_M, 5.2 GB)
- deepseek-r1:8b (8.2B, Q4_K_M, 5.2 GB)

DATASET
- version: urban_v1.0
- case count: 3
- type: synthetic
- PII: none

EXPERIMENT
- runs: 1 per model
- prompt_version: TIER1_SYSTEM + TIER3_DEVELOPER (v1.0)
- decoding: temperature=0.0, max_tokens=512
- validation_retries: 3
- transient_retries: 2
- backoff: 1s, 2s, 4s
- jitter: OFF
- reproducibility: deterministic (temperature=0.0)

RESULTS

Metric                         Llama3.2           Qwen3-8B           DeepSeek-R1-8B    
------------------------------------------------------------------------------
valid_json_rate                100.00%            100.00%            100.00%           
schema_compliance              100.00%            100.00%            100.00%           
repair_success_rate            0.00%              0.00%              0.00%             
classification_accuracy        66.67%             66.67%             0.00%             
urgency_accuracy               66.67%             66.67%             0.00%             
routing_accuracy               66.67%             66.67%             0.00%             
success_rate                   100.00%            100.00%            33.33%            
failure_rate                   0.00%              0.00%              66.67%            
retry_rate                     0.00%              0.00%              0.00%             
generation_P50                 16133ms            141778ms           586731ms          
generation_P95                 27409ms            148366ms           586731ms          
generation_P99                 27409ms            148366ms           586731ms          
total_P50                      16133ms            141778ms           600311ms          
total_P95                      27409ms            148366ms           600392ms          
total_P99                      27409ms            148366ms           600392ms          
input_tokens                   1196               1932               382               
output_tokens                  274                291                1570              
thinking_tokens                0                  874                1693              
total_tokens                   1470               3097               3645              

MODEL-SPECIFIC FINDINGS

  llama3.2:
    - cases with thinking tokens: 0/3
    - avg input tokens/case: 399
    - avg output tokens/case: 91

  qwen3:8b:
    - cases with thinking tokens: 3/3
    - avg input tokens/case: 644
    - avg output tokens/case: 97
    - total thinking tokens: 874

  deepseek-r1:8b:
    - cases with thinking tokens: 1/3
    - avg input tokens/case: 127
    - avg output tokens/case: 523
    - total thinking tokens: 1693

QUALITY ANALYSIS

  Best classification accuracy: llama3.2 (66.67%)
  Best urgency accuracy: llama3.2 (66.67%)

RELIABILITY ANALYSIS

  Best success rate: llama3.2 (100.00%)

LATENCY ANALYSIS

  Fastest avg total latency: llama3.2
    llama3.2: 19146ms avg
    qwen3:8b: 131061ms avg
    deepseek-r1:8b: 595812ms avg

TOKEN ANALYSIS

  llama3.2: input=1196, output=274, thinking=0
  qwen3:8b: input=1932, output=291, thinking=874
  deepseek-r1:8b: input=382, output=1570, thinking=1693

DECISION

  Composite score (quality 30% + reliability 20% + latency 25% + structure 15% + efficiency 10%):
    llama3.2: 0.8866
    qwen3:8b: 0.7536
    deepseek-r1:8b: 0.2702

  RECOMMENDED: llama3.2

RATIONALE

  llama3.2:
    Classification: 66.67%
    Success rate: 100.00%
    Avg latency: 19146ms
    JSON compliance: 100.00%

  qwen3:8b:
    Classification: 66.67%
    Success rate: 100.00%
    Avg latency: 131061ms
    JSON compliance: 100.00%

  deepseek-r1:8b:
    Classification: 0.00%
    Success rate: 33.33%
    Avg latency: 595812ms
    JSON compliance: 100.00%

LIMITATIONS
- Single run per model (no statistical significance)
- CPU-only inference (latency not representative of GPU deployment)
- 3 cases only (urban_v1.0 normal subset)
- temperature=0.0 may not reflect production settings
- deepseek-r1:8b thinking tokens consume budget but may improve quality

GATE 2.2 — Real Provider
  PASS — All 3 models executed through OllamaProvider

GATE 2.3 — Benchmark
  PASS — Real results exist for all 3 models

NEXT CORRECT STEP
- Security evaluation (injection cases)
- Bias evaluation (paired cases)
- Consider additional cases if 3-case baseline is insufficient

==============================================================================