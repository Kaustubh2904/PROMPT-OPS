# PROMPT-OPS — Complete Project Knowledge

## What It Is

**PROMPT-OPS** is a **closed-loop, telemetry-aware LLM prompt optimization system** built as a Final Year Project (2025–26). It solves the core problem that most LLM apps are *open-loop* — you send a prompt, get a response, and have no systematic way to know if it was good. PROMPT-OPS wraps every LLM call with:

1. **Automatic quality evaluation** (LLM-as-Judge)
2. **Prompt A/B testing** with weighted traffic splitting
3. **Temperature optimization** via controlled experiments
4. **Cost-aware model routing** (cheapest model that passes quality gate)
5. **Full telemetry** stored in SQLite, visualized via Streamlit dashboard

---

## Project Layout

```
project/
├── .env                        ← API key + all configuration
├── run.py                      ← Demo entry point
├── dashboard.py                ← Streamlit dashboard (standalone)
├── config/
│   ├── __init__.py
│   └── config.py               ← Pydantic Settings + MODEL_TIERS + MODEL_PRICING
├── src/
│   ├── pipeline/orchestrator.py   ← THE closed-loop engine (pipeline.run())
│   ├── llm/client.py              ← OpenRouter HTTP client (httpx + tenacity)
│   ├── evaluation/evaluator.py    ← LLM-as-Judge (5 dimensions)
│   ├── optimization/
│   │   ├── optimizer.py           ← PromptManager, PromptOptimizer (A/B testing)
│   │   ├── temperature_optimizer.py ← Temperature sweep experiments
│   │   └── cost_router.py         ← Tier cascade with quality gates + EMA cache
│   ├── telemetry/tracker.py       ← Request-level telemetry logging
│   ├── monitoring/monitor.py      ← Stats, anomaly detection (Z-score), alerts
│   └── database/
│       ├── models.py              ← 8 SQLAlchemy tables
│       └── connection.py          ← Session management
├── data/prompt_ops.db             ← SQLite database (auto-created)
└── examples/
    ├── demo.py                    ← Simulated demo (no API key)
    └── real_demo.py               ← Live OpenRouter demo
```

---

## Architecture — The Closed Loop

```
User Input
    │
    ▼
[Pipeline Orchestrator — orchestrator.py]
    │
    ├─ Step 1: Prompt Selection
    │     PromptManager.get_prompt_for_request()
    │     → Weighted random A/B test traffic split
    │
    ├─ Step 2: Temperature Selection
    │     TemperatureOptimizer.get_recommended_temperature()
    │     → Uses experimentally determined optimal temp (or 0.7 default)
    │
    ├─ Step 3: LLM Call
    │     ├─ (cost routing ON) CostAwareRouter.route_request()
    │     │     → Tries tier_1 → tier_2 → tier_3 → tier_4 → premium
    │     │     → Each tier: call model, evaluate quality, accept if ≥ threshold
    │     └─ (cost routing OFF) LLMClient.chat()
    │           → httpx POST to OpenRouter /chat/completions
    │           → 3-attempt retry with exponential backoff
    │
    ├─ Step 4: Telemetry Recording
    │     → Saves TelemetryLog row (latency, tokens, cost, model, prompt version…)
    │
    ├─ Step 5: Auto-Evaluation (LLM-as-Judge)
    │     ResponseEvaluator.evaluate()
    │     → Sends judge prompt to judge model (low temp=0.1)
    │     → Parses JSON with 5 dimension scores
    │     → Saves EvaluationResult row + updates TelemetryLog.quality_score
    │
    └─ Step 6: Update Prompt Metrics
          PromptManager.update_prompt_metrics()
          → Recalculates avg latency / cost / quality / success_rate for version
```

**Return:** [PipelineResponse](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/pipeline/orchestrator.py#39-89) dataclass with content, quality_score, latency_ms, cost_usd, was_cost_routed, cost_saved_usd, etc.

---

## Module Deep Dives

### [config/config.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/config/config.py) — Settings
- Uses **pydantic-settings** `BaseSettings` with [.env](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/.env) file loading
- Key settings: `openrouter_api_key`, `openrouter_default_model`, `openrouter_judge_model`, `database_url`, alert thresholds, temperature sweep params, quality threshold for downgrade
- Defines `MODEL_TIERS` dict (`tier_1` → `tier_4` + `premium`) — all free models currently
- Defines `MODEL_PRICING` dict (free models = $0.0, premium models have real $/1k token prices)
- Helper [get_model_cost(model, input_tokens, output_tokens)](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/config/config.py#152-167) → float USD

### [src/llm/client.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py) — LLM Client
- [LLMResponse](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#27-46) dataclass: content, model, input/output/total tokens, latency_ms, cost_usd, request_id, temperature, finish_reason, error
- [LLMClient](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#48-210) class with [chat()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#81-171) method:
  - Builds OpenAI-compatible messages list (system + user)
  - [_call_api()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#172-183) uses `@retry(stop=3, wait=exponential)` via **tenacity**
  - Calculates cost via [get_model_cost()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/config/config.py#152-167)
  - Returns structured [LLMResponse](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#27-46)
- Also has [list_available_models()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#184-194), [estimate_cost()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/llm/client.py#195-200), context manager support

### [src/evaluation/evaluator.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/evaluation/evaluator.py) — LLM-as-Judge
- [EvaluationScore](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/evaluation/evaluator.py#29-88) dataclass: relevance, accuracy, completeness, format_compliance, safety (all 0.0–1.0), reasoning, composite_score
- `composite_score` = weighted average: relevance×0.30 + accuracy×0.25 + completeness×0.20 + format_compliance×0.15 + safety×0.10
- `ResponseEvaluator.evaluate()`:
  - Formats `JUDGE_PROMPT_TEMPLATE` with original prompt + response
  - Calls judge LLM at **temperature=0.1** (for consistency)
  - Parses JSON response, handles markdown code blocks
  - Falls back to heuristic (length-based) if judge fails
- [should_evaluate()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/evaluation/evaluator.py#138-143) uses configurable `evaluation_sample_rate` (default 1.0 = 100%)

### [src/optimization/optimizer.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py) — A/B Testing + Prompt Management
- [PromptManager](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#28-273):
  - [create_prompt_version()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#38-111) — auto-increments version, stores template + traffic_weight
  - [get_prompt_for_request()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#112-176) — **weighted random selection** across active versions for A/B testing
  - [update_prompt_metrics()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#215-259) — recalculates avg latency/cost/quality/success_rate from raw telemetry
  - [deactivate_version()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#260-273) — soft-delete
- [PromptOptimizer](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#275-537):
  - [analyze_prompt_performance()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#288-341) — computes stats per version over time window
  - [_recommend_best_version()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#367-412) — scores versions by [OptimizationGoal](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#20-26) (LATENCY/COST/QUALITY/BALANCED)
  - [run_optimization()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#456-537) — creates [OptimizationRun](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py#217-253) record, runs analysis, stores recommendation

### [src/optimization/cost_router.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/cost_router.py) — Cost-Aware Router
- [CostAwareRouter](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/cost_router.py#44-365) with **quality cache** (`_quality_cache`: prompt_id → tier → EMA quality score)
- [route_request()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/cost_router.py#70-219):
  - Determines tiers to try via [_get_tiers_to_try()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/cost_router.py#220-248) (skips historically poor tiers via cache)
  - For each tier model: call → evaluate quality with [ResponseEvaluator](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/evaluation/evaluator.py#111-295)
  - If quality ≥ threshold → accept, calculate cost_saved vs. preferred model
  - If quality < threshold → escalate to next tier
  - All tiers fail → fall back to `preferred_model`
- Cache uses **Exponential Moving Average**: `0.7 * old + 0.3 * new_quality`
- Saves [CostRoutingLog](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py#320-348) records with routing decisions
- [get_routing_stats()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/cost_router.py#332-365) returns downgrade/escalation rates and total savings

### [src/monitoring/monitor.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py) — Monitoring & Alerting
- [ModelMonitor](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py#20-403) computes per-model stats from [TelemetryLog](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py#20-79):
  - avg/median/p95/p99 latency, error rate, token totals, cost totals, avg quality
- [_check_thresholds()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py#177-217) creates [Alert](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py#181-215) DB records for: high_latency, high_error_rate, high_cost
- [detect_anomalies()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py#339-403) — **Z-score** based: `|value - mean| / std > sensitivity` (default 2.0σ)
  - Works on latency_ms, cost_usd, or total_tokens
- [aggregate_hourly_metrics()](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py#276-338) — rolls up raw telemetry into [ModelMetrics](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py#130-179) hourly rows

### [src/database/models.py](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/database/models.py) — 8-Table Schema

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `telemetry_logs` | Every LLM call | request_id, model_name, prompt_id, prompt_version, input/output tokens, latency_ms, cost_usd, quality_score, is_error |
| [prompt_versions](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/optimization/optimizer.py#177-214) | Prompt templates | prompt_id, version, template, traffic_weight, is_default, avg_quality_score, total_calls |
| `model_metrics` | Hourly aggregations | model_name, window_size, avg_latency_ms, p50/p95/p99, total_cost_usd |
| [alerts](file:///D:/Documents/Final_Yr_Project/PROMPT-OPS/project/src/monitoring/monitor.py#218-228) | Threshold violations | alert_type, severity, model_name, message, threshold_value, actual_value, is_resolved |
| `optimization_runs` | Optimization experiments | prompt_id, optimization_goal, baseline_version, optimized_version, improvement_% |
| `evaluation_results` | LLM-as-Judge scores | request_id, relevance, accuracy, completeness, format_compliance, safety, composite_score |
| `temperature_experiments` | Temp sweep results | prompt_id, best_temperature, best_quality_score, results_json |
| `cost_routing_logs` | Routing decisions | original_model, routed_model, tier_used, quality_score, escalated, cost_saved_usd |

---

## Configuration Reference

| Setting | Default | Purpose |
|---------|---------|---------|
| `OPENROUTER_API_KEY` | (required) | OpenRouter API key |
| `OPENROUTER_DEFAULT_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | Primary model |
| `OPENROUTER_JUDGE_MODEL` | `meta-llama/llama-3.3-70b-instruct:free` | Judge for evaluations |
| `DATABASE_URL` | `sqlite:///./data/prompt_ops.db` | SQLite path |
| `LATENCY_THRESHOLD_MS` | 5000 | Alert trigger |
| `ERROR_RATE_THRESHOLD` | 0.10 | Alert trigger |
| `COST_THRESHOLD_USD` | 1.0 | Alert trigger |
| `TEMPERATURE_MIN/MAX/STEP` | 0.0/1.5/0.5 | Temp sweep range |
| `TEMPERATURE_TRIALS_PER_STEP` | 2 | Trials per temp value |
| `COST_ROUTING_ENABLED` | true | Enable tier cascade |
| `QUALITY_THRESHOLD_FOR_DOWNGRADE` | 0.6 | Min quality to accept cheaper model |
| `AUTO_EVALUATE` | true | Run LLM-as-Judge on every response |
| `EVALUATION_SAMPLE_RATE` | 1.0 | Fraction of calls to evaluate |
| `MIN_SAMPLES_FOR_OPTIMIZATION` | 5 | Samples needed before recommending |

---

## Model Tiers (Cost Routing)

| Tier | Models | Cost |
|------|--------|------|
| tier_1 | gemma-3-4b-it:free, llama-3.2-3b-instruct:free | $0 |
| tier_2 | llama-3.3-70b-instruct:free, mistral-small-3.1-24b:free | $0 |
| tier_3 | qwen3-4b:free, nemotron-nano-9b:free | $0 |
| tier_4 | gemma-3-12b-it:free, gemma-3-27b-it:free | $0 |
| premium | gpt-4o, claude-sonnet-4, gemini-2.5-pro-preview | $$$ |

---

## How to Run

```powershell
# 1. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 2. Run demo (makes real API calls via OpenRouter)
python run.py
# OR
python examples\real_demo.py

# 3. Launch dashboard
streamlit run dashboard.py
# Opens at http://localhost:8501
```

---

## Dashboard (dashboard.py / Streamlit)

8 pages accessible from sidebar:
1. **📊 Overview** — KPIs, total requests, avg quality, costs
2. **📈 Model Monitoring** — Latency, tokens, anomaly detection
3. **🔄 Prompt Management** — Create/edit prompt versions, A/B test config
4. **⭐ Quality Evaluations** — Score distributions, per-dimension breakdown
5. **🌡️ Temperature Experiments** — Optimal temperature results
6. **💰 Cost Routing** — Tier distribution, cost savings
7. **🚨 Alerts & Anomalies** — Active alerts, resolve actions
8. **⚙️ Settings** — Configuration management + Live Playground

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **All-free models in tiers** | Zero cost during development/demo |
| **EMA quality cache in router** | Learns routing patterns without DB lookup overhead |
| **Heuristic fallback in evaluator** | Graceful degradation when judge model fails |
| **Eager attribute loading + expunge** | Avoids SQLAlchemy `DetachedInstanceError` across session boundaries |
| **Lazy initialization in Pipeline** | Avoids import cycle issues at startup |
| **Z-score for anomaly detection** | Simple, no ML library needed, works on limited data |
| **pydantic-settings** | Type-safe config with .env support and field aliases |
| **httpx over requests** | Better timeout control, async-ready |
| **tenacity for retries** | Declarative retry with exponential backoff |
