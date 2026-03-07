# ⚡ PROMPT-OPS# 🎯 PROMPT-OPS: Closed-Loop Telemetry-Aware Prompt Optimization System



**Closed-loop telemetry-aware prompt optimisation for LLM applications.**A production-grade system that monitors, evaluates, and automatically optimizes LLM (Large Language Model) prompts through a **closed feedback loop** — combining real-time telemetry, automated quality evaluation (LLM-as-Judge), temperature optimization, and cost-aware model routing.



> Most LLM apps are *open-loop* — you send a prompt, get a response, and hope it's good.  ![Python](https://img.shields.io/badge/python-3.9+-blue.svg)

> PROMPT-OPS **closes the loop**: every response is automatically evaluated for quality,  ![License](https://img.shields.io/badge/license-MIT-green.svg)

> and the system uses that data to pick better prompts, temperatures, and models next time.![Status](https://img.shields.io/badge/status-Production--Ready-brightgreen.svg)

![Models](https://img.shields.io/badge/LLM_Models-200+-purple.svg)

---

## 🔥 What Makes This Special

## The Problem

Most LLM monitoring tools only track **operational metrics** (latency, cost, errors). This system goes further by:

You're building an app that calls an LLM. You have questions:

1. **Automatically evaluating response quality** using LLM-as-Judge

- "Is prompt A or prompt B actually better?" → **You don't know** because you only see the response, not its quality.2. **Feeding quality scores back** into prompt optimization decisions

- "Should temperature be 0.3 or 0.7 for this task?" → **You guess** because there's no data.3. **Finding the optimal temperature** for each prompt through experiments

- "Can I use a cheaper model for simple questions?" → **You can't tell** which questions are simple without measuring quality.4. **Routing to cheaper models** when quality allows, saving 40-80% on API costs

5. **Auto-promoting winning prompts** based on real performance data

## The Solution

**This is a closed loop** — not just monitoring, but learning and improving:

PROMPT-OPS adds a **closed feedback loop** around your LLM calls:

```

``` ┌──────────────┐     ┌──────────┐     ┌────────────────┐

Your prompt ──→ LLM call ──→ Response │ Prompt       │────▶│ LLM Call │────▶│ Telemetry      │

                                │ │ Selection    │     │ (OpenRouter)   │ Recording      │

                    ┌───────────┘ │ (A/B Test)   │     └──────────┘     └───────┬────────┘

                    ▼ └──────▲───────┘                              │

            Auto-evaluate quality        ← LLM-as-Judge scores 5 dimensions        │                                      ▼

                    │ ┌──────┴───────┐     ┌──────────────┐  ┌────────────────┐

                    ▼ │ Optimization │◀────│ Feedback     │◀─│ LLM-as-Judge   │

            Store scores + telemetry     ← Every call logged to database │ Decision     │     │ Analysis     │  │ Evaluation     │

                    │ └──────────────┘     └──────────────┘  └────────────────┘

                    ▼```

            System LEARNS:

              • Which prompt version is best        (A/B testing)## 🎯 Project Overview

              • Which temperature is optimal         (experiments)

              • Which model tier is sufficient       (cost routing)This system provides **end-to-end prompt lifecycle management** for any LLM-powered application:

                    │

                    ▼| Capability | What It Does | Key Technology |

            Next request uses better settings  ← LOOP CLOSED|------------|-------------|----------------|

```| **Telemetry** | Tracks every LLM call (latency, tokens, cost, errors) | Context managers, SQLAlchemy |

| **Evaluation** | Auto-scores response quality on 5 dimensions | LLM-as-Judge pattern |

**Result:** Quality goes up, costs go down, and you have data to prove it.| **Prompt Versioning** | A/B tests multiple prompt versions with traffic splitting | Weighted random selection |

| **Temperature Optimization** | Finds optimal temperature per prompt via experiments | Controlled trials + quality scoring |

---| **Cost Routing** | Routes to cheapest model that meets quality bar | Tiered cascade with fallback |

| **Monitoring** | Aggregates metrics, detects anomalies, fires alerts | Z-score anomaly detection |

## Quick Start| **Dashboard** | 8-page Streamlit UI for visualization and management | Plotly interactive charts |



### 1. Install dependencies### Key Features



```bash- **🔄 Closed-Loop Feedback**: Evaluation results automatically feed back into optimization

cd project- **🤖 200+ Models via OpenRouter**: GPT-4o, Claude, Gemini, Llama, Mistral, DeepSeek, and more

pip install -r requirements.txt- **📊 LLM-as-Judge Evaluation**: 5 quality dimensions (relevance, accuracy, completeness, format, safety)

```- **🌡️ Temperature Optimization**: Systematic experiments to find optimal creativity level

- **� Cost-Aware Routing**: Automatic model downgrading when cheaper models meet quality bar

### 2. Set your API key- **📈 Real-Time Dashboard**: 8-page Streamlit web interface

- **🚨 Alerting & Anomaly Detection**: Z-score based anomaly detection with configurable thresholds

The `.env` file is already configured. If you need to change the key:- **🧪 A/B Testing**: Traffic-split prompt versions with statistical comparison



```bash## 🏗️ System Architecture

# .env

OPENROUTER_API_KEY=sk-or-v1-your-key-here```

```┌─────────────────────────────────────────────────────────────────────┐

│                       Application Layer                             │

Get a free key at [openrouter.ai/keys](https://openrouter.ai/keys). All models used are **free** — $0 cost.│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────────┐│

│  │   Your App   │  │  Streamlit   │  │  examples/real_demo.py    ││

### 3. Run the system│  │              │  │  Dashboard   │  │  (Live OpenRouter calls)  ││

│  └──────┬───────┘  └──────┬───────┘  └──────────┬────────────────┘│

```bash└─────────┼──────────────────┼────────────────────┼─────────────────┘

python run.py          │                  │                    │

```          └──────────────────┼────────────────────┘

                             │

This will:                    ┌────────▼────────┐

- Initialise the database in `data/prompt_ops.db`                    │   Pipeline      │ ← Single entry point

- Create sample prompt versions for A/B testing                    │   Orchestrator  │   pipeline.run("your input")

- Make real LLM calls through OpenRouter (free models)                    └────┬───┬───┬────┘

- Auto-evaluate every response with LLM-as-Judge                         │   │   │

- Run a temperature optimisation experiment          ┌──────────────┘   │   └──────────────┐

- Test cost-aware model routing          ▼                  ▼                   ▼

- Show monitoring stats and optimisation recommendations┌─────────────────┐ ┌──────────────┐  ┌─────────────────┐

│ Prompt Manager  │ │  LLM Client  │  │ Cost Router     │

### 4. Open the dashboard│ • Versioning    │ │  (OpenRouter) │  │ • Tier cascade  │

│ • A/B Testing   │ │  • 200+ models│  │ • Quality gate  │

```bash│ • Traffic split │ │  • Retry logic│  │ • $ savings     │

streamlit run dashboard/app.py└────────┬────────┘ └──────┬───────┘  └────────┬────────┘

```         │                 │                    │

         └─────────────────┼────────────────────┘

The dashboard shows everything at a glance — plus a **live playground** where you can type a prompt and see before/after optimisation side-by-side.                           │

               ┌───────────▼───────────┐

---               │   Telemetry Tracker   │

               │  • Latency, tokens    │

## What Each Component Does               │  • Cost, errors       │

               │  • Quality scores     │

### Pipeline (`src/pipeline/orchestrator.py`)               └───────────┬───────────┘

The single entry point. Call `pipeline.run("your prompt")` and it:                           │

1. Picks the best prompt version (A/B test)              ┌────────────┼────────────┐

2. Selects optimal temperature (from experiments)              ▼            ▼            ▼

3. Optionally routes to a cheaper model (cost routing)   ┌──────────────┐ ┌──────────┐ ┌──────────────┐

4. Makes the LLM call via OpenRouter   │ LLM-as-Judge │ │ Monitor  │ │   Database   │

5. Records telemetry to database   │ (Evaluator)  │ │ Anomaly  │ │  SQLAlchemy  │

6. Auto-evaluates response quality   │ 5 dimensions │ │ Detection│ │  8 tables    │

7. Updates prompt version metrics   └──────┬───────┘ │ Alerts   │ └──────────────┘

          │         └──────────┘

### LLM Client (`src/llm/client.py`)          ▼

Makes HTTP calls to OpenRouter's API. Handles retries with exponential backoff, timeout management, and token counting. Works with any of OpenRouter's 200+ models.   ┌──────────────┐     ┌──────────────────┐

   │ Temperature  │     │   Feedback Loop  │

### Evaluator (`src/evaluation/evaluator.py`)   │ Optimizer    │     │   (Auto-promote  │

**This is the key piece that closes the loop.** Uses a judge LLM to score every response on 5 dimensions:   │ (Experiments)│     │    best prompts) │

   └──────────────┘     └──────────────────┘

| Dimension | What it measures |```

|-----------|-----------------|

| Relevance | Does the response answer what was asked? |## 📦 Installation & Setup

| Accuracy | Is the information correct? |

| Completeness | Are the key points covered? |### Prerequisites

| Format Compliance | Does it follow instructions? |- Python 3.9+

| Safety | Free from harmful content? |- An OpenRouter API key (free tier available at https://openrouter.ai/keys)



Each scored 0.0–1.0, combined into a weighted composite score.### Step 1: Clone & Install



### Temperature Optimizer (`src/optimization/temperature_optimizer.py`)```powershell

Runs controlled experiments: for each temperature value, it makes N calls, evaluates quality, and measures consistency. Picks the temperature with the best quality × consistency score.# Navigate to the project

cd "d:\extra-work\New folder\PROMPT-OPS\project"

### Cost Router (`src/optimization/cost_router.py`)

Splits models into tiers by capability. For each request, starts with the weakest model. If quality is below threshold, escalates to the next tier. Learns over time which prompts work on cheap models.# Create virtual environment

python -m venv venv

### Prompt Manager & Optimizer (`src/optimization/optimizer.py`).\venv\Scripts\Activate.ps1

Manages prompt versions, handles A/B test traffic splitting, and recommends the best-performing version based on accumulated quality data.

# Install dependencies

### Telemetry Tracker (`src/telemetry/tracker.py`)pip install -r requirements.txt

Records every LLM call — latency, tokens, cost, model, prompt version, and quality score.```



### Monitor (`src/monitoring/monitor.py`)### Step 2: Configure API Key

Aggregates telemetry into statistics, detects anomalies via z-score analysis, creates alerts when thresholds are exceeded.

```powershell

### Database (`src/database/`)# Copy the example .env file

8 SQLAlchemy tables:Copy-Item .env.example .env



| Table | Purpose |# Edit .env and add your OpenRouter API key

|-------|---------|# OPENROUTER_API_KEY=sk-or-v1-your-key-here

| `telemetry_logs` | Every LLM call |```

| `prompt_versions` | Prompt templates + A/B test config |

| `model_metrics` | Hourly aggregations |### Step 3: Run the Demo (Real LLM Calls!)

| `alerts` | Threshold violations |

| `optimization_runs` | Optimisation history |```powershell

| `evaluation_results` | LLM-as-Judge scores |python examples\real_demo.py

| `temperature_experiments` | Temp sweep results |```

| `cost_routing_logs` | Routing decisions |

This runs 6 live demonstrations:

---1. ✅ Basic pipeline call with auto-evaluation

2. ✅ A/B testing between prompt versions

## The Dashboard3. ✅ Temperature optimization experiment

4. ✅ Cost-aware model routing

The dashboard is a single Streamlit page with these sections:5. ✅ Monitoring and alerting

6. ✅ Automatic prompt optimization

1. **Hero metrics** — total requests, average quality, active prompts, experiments run

2. **Live Playground** — type a prompt, see before/after optimisation side-by-side with radar charts### Step 4: Launch the Dashboard

3. **Quality Evaluations** — score distribution and per-dimension breakdown

4. **Prompt A/B Testing** — version comparison tables with quality bar charts```powershell

5. **Temperature Experiments** — quality & consistency vs temperature line chartsstreamlit run dashboard\app.py

6. **Cost Routing** — tier distribution pie chart and routing decision log```

7. **Activity Log** — recent pipeline requests

8. **Explainer** — "What is this system?" for anyone viewing the dashboardOpens at `http://localhost:8501` with 8 pages:

- 📊 Dashboard Overview — KPIs, requests, costs

---- 📈 Model Monitoring — Latency, tokens, anomalies

- 🔄 Prompt Management — Create, test, optimize prompts

## Project Structure- ⭐ Quality Evaluations — LLM-as-Judge scores

- 🌡️ Temperature Experiments — Optimal temperature results

```- 💰 Cost Routing — Savings from smart routing

project/- 🚨 Alerts & Anomalies — Threshold violations

├── .env                        ← API key + all configuration- ⚙️ Settings — Configuration management

├── run.py                      ← Single entry point — runs the full demo

├── requirements.txt            ← Dependencies (10 packages)## 🚀 Usage — The Pipeline API

├── config/

│   ├── __init__.pyThe pipeline is the **single entry point** for the entire system:

│   └── config.py               ← Settings, free models, model tiers

├── src/```python

│   ├── pipeline/from src.pipeline import pipeline

│   │   └── orchestrator.py     ← THE closed-loop enginefrom src.database import init_database

│   ├── llm/

│   │   └── client.py           ← OpenRouter HTTP clientinit_database()

│   ├── evaluation/

│   │   └── evaluator.py        ← LLM-as-Judge (5 dimensions)# Simple call — telemetry + evaluation happen automatically

│   ├── optimization/response = pipeline.run("Explain quantum computing simply")

│   │   ├── optimizer.py        ← A/B testing + prompt optimisationprint(response.content)

│   │   ├── temperature_optimizer.py  ← Temperature experimentsprint(f"Quality: {response.quality_score}")  # Auto-scored by LLM-as-Judge!

│   │   └── cost_router.py      ← Tier-based model routing```

│   ├── telemetry/

│   │   └── tracker.py          ← Request-level logging### With Prompt Versioning & A/B Testing

│   ├── monitoring/

│   │   └── monitor.py          ← Stats, anomaly detection, alerts```python

│   └── database/# Create prompt versions first

│       ├── models.py           ← 8 SQLAlchemy tablesfrom src.optimization import prompt_manager

│       └── connection.py       ← Session management

├── dashboard/prompt_manager.create_prompt_version(

│   └── app.py                  ← Streamlit dashboard    prompt_id="summarize",

└── data/    template="Summarize this:\n\n{input}",

    └── prompt_ops.db           ← SQLite database (auto-created)    name="Basic", is_default=True, traffic_weight=0.5

```)

prompt_manager.create_prompt_version(

---    prompt_id="summarize",

    template="You are an expert analyst. Summarize in 3 bullet points:\n\n{input}",

## Free Models Used    name="Enhanced", traffic_weight=0.5

)

All models are free on OpenRouter — $0 cost:

# Now the pipeline automatically A/B tests between versions

| Model | Tier | Capability |response = pipeline.run(

|-------|------|------------|    "The AI market grew 35% in 2025...",

| `google/gemma-3-4b-it:free` | Tier 1 | Small, fast |    prompt_id="summarize",

| `qwen/qwen3-8b:free` | Tier 2 | Mid-range |    ab_testing=True,

| `meta-llama/llama-3.3-8b-instruct:free` | Tier 2 | Mid-range (default) |)

| `mistralai/mistral-small-3.1-24b-instruct:free` | Tier 3 | Larger |print(f"Used version: v{response.prompt_version}")

| `deepseek/deepseek-chat-v3-0324:free` | Tier 3 | Larger |print(f"Quality: {response.quality_score}")

| `microsoft/phi-4-reasoning:free` | Tier 4 | Strongest reasoning |```



---### With Cost-Aware Routing



## Troubleshooting```python

# Request an expensive model, but let the router try cheaper ones first

**"OPENROUTER_API_KEY is not set"**  response = pipeline.run(

Edit `.env` and paste your key from [openrouter.ai/keys](https://openrouter.ai/keys).    "What is the capital of France?",

    model="openai/gpt-4o",           # Expensive

**Import errors**      enable_cost_routing=True,          # May use a cheaper model

Make sure you're in the `project/` directory and your virtual environment is active:)

```bashprint(f"Used model: {response.model}")       # Might be a free model!

cd projectprint(f"Cost saved: ${response.cost_saved_usd}")

pip install -r requirements.txt```

```

### Temperature Optimization

**Database errors after code changes**  

Delete and recreate:```python

```bashfrom src.optimization import temperature_optimizer

del data\prompt_ops.db

python run.py# Automatically find the best temperature

```result = temperature_optimizer.run_experiment(

    prompt_id="summarize",

**Rate limiting from OpenRouter**      prompt_text="Summarize this article: ...",

Free models have rate limits. The system has built-in retry logic with exponential backoff. If it persists, wait a minute or check [openrouter.ai/settings/limits](https://openrouter.ai/settings/limits).    temp_min=0.0, temp_max=1.0, temp_step=0.3,

    trials_per_step=3,

---)

print(f"Best temperature: {result.best_temperature}")

## Tech Stack

# Future pipeline calls will use this optimal temperature automatically!

- **Python 3.10+**```

- **OpenRouter** — LLM gateway (200+ models, free tier available)

- **SQLAlchemy** — ORM with SQLite (PostgreSQL-ready)## 📊 What Gets Measured

- **Streamlit + Plotly** — Interactive dashboard

- **httpx + tenacity** — HTTP client with retry logic### Telemetry (Every Request)

- **pydantic-settings** — Configuration management

- **loguru** — Structured logging| Metric | Source | Purpose |

|--------|--------|---------|

---| Latency (ms) | Automatic | Response time monitoring |

| Input/Output Tokens | API response | Usage tracking |

*Built for Final Year Project 2025–26*| Cost (USD) | Calculated | Budget management |

| Success/Error | HTTP status | Reliability monitoring |
| Model Used | Request config | Routing analysis |
| Prompt Version | A/B test | Version comparison |

### Quality Evaluation (LLM-as-Judge)

| Dimension | What It Measures | Range |
|-----------|-----------------|-------|
| **Relevance** | Does the response answer the question? | 0.0 – 1.0 |
| **Accuracy** | Is the information factually correct? | 0.0 – 1.0 |
| **Completeness** | Are key points covered? | 0.0 – 1.0 |
| **Format Compliance** | Does it follow instructions? | 0.0 – 1.0 |
| **Safety** | Free from harmful content? | 0.0 – 1.0 |
| **Composite Score** | Weighted average of all dimensions | 0.0 – 1.0 |

### Monitoring & Alerting

| Alert Type | Default Threshold | Severity |
|------------|-------------------|----------|
| High Latency | > 2000ms avg | Warning |
| High Error Rate | > 5% | High |
| Cost Exceeded | > $10/day | Medium |
| Anomaly Detected | Z-score > 2.0 | Info |

## 🔧 Technical Deep Dives

### The Closed Feedback Loop

The key innovation of this system is the **closed loop**:

```
1. User request arrives
2. Pipeline selects prompt version (A/B testing)
3. Pipeline selects optimal temperature (from experiments)  
4. Pipeline optionally routes to cheaper model (cost optimization)
5. LLM call is made via OpenRouter
6. Full telemetry is recorded to database
7. LLM-as-Judge evaluates response quality (5 dimensions)
8. Quality score is written back to telemetry record
9. Prompt version metrics are updated with new quality data
10. Optimizer can now recommend the best version WITH quality data
11. Next request uses this improved knowledge → loop continues
```

**Without the loop:** You only know latency + cost. You're blind to quality.  
**With the loop:** Every request makes the system smarter about what works.

### Temperature Optimization Algorithm

```
For each temperature in [0.0, 0.1, 0.2, ..., 1.5]:
    Run N trials with the same prompt
    Evaluate each response with LLM-as-Judge
    Calculate:
        avg_quality  = mean(quality_scores)
        consistency  = 1 - std(quality_scores)
        composite    = avg_quality × (0.7 + 0.3 × consistency)
    
Best temperature = argmax(composite)
```

**Why consistency matters:** Temperature 1.0 might produce amazing responses 50% of the time and terrible ones the other 50%. Temperature 0.5 might be slightly lower quality but consistent. For production, consistency wins.

### Cost Routing Cascade

```
Request for "openai/gpt-4o" ($$$):
  │
  ├─ Try FREE tier (llama-3.3-8b) → Evaluate quality
  │   Quality ≥ 0.7? → ✅ Use it! Save $$$
  │   Quality < 0.7? → ↓ Escalate
  │
  ├─ Try CHEAP tier (gemini-flash) → Evaluate quality
  │   Quality ≥ 0.7? → ✅ Use it! Save $$
  │   Quality < 0.7? → ↓ Escalate
  │
  ├─ Try MID tier (claude-haiku) → Evaluate quality
  │   Quality ≥ 0.7? → ✅ Use it! Save $
  │   Quality < 0.7? → ↓ Escalate
  │
  └─ Use PREMIUM (gpt-4o) → Full price, guaranteed quality
```

### Database Schema (8 Tables)

| Table | Records | Purpose |
|-------|---------|---------|
| `telemetry_logs` | Every LLM API call | Core data |
| `prompt_versions` | Prompt templates + versions | A/B testing |
| `model_metrics` | Hourly/daily aggregations | Trend analysis |
| `alerts` | Threshold violations | Incident management |
| `optimization_runs` | Optimization experiments | Audit trail |
| `evaluation_results` | LLM-as-Judge scores | Quality tracking |
| `temperature_experiments` | Temp optimization results | Tuning data |
| `cost_routing_logs` | Routing decisions | Cost analysis |

## ⚙️ Configuration

### Environment Variables (`.env`)

```bash
# ─── OpenRouter (Required) ───
OPENROUTER_API_KEY=sk-or-v1-your-key-here
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_DEFAULT_MODEL=openai/gpt-4o-mini
OPENROUTER_JUDGE_MODEL=google/gemini-2.0-flash-001

# ─── Database ───
DATABASE_URL=sqlite:///./prompt_ops.db

# ─── Telemetry ───
ENABLE_TELEMETRY=true

# ─── Alert Thresholds ───
LATENCY_THRESHOLD_MS=2000
ERROR_RATE_THRESHOLD=0.05
COST_THRESHOLD_USD=10.0

# ─── Temperature Optimization ───
TEMPERATURE_MIN=0.0
TEMPERATURE_MAX=1.5
TEMPERATURE_STEP=0.1
TEMPERATURE_TRIALS=3

# ─── Cost Routing ───
COST_ROUTING_ENABLED=true
QUALITY_THRESHOLD_FOR_DOWNGRADE=0.7

# ─── Evaluation ───
AUTO_EVALUATE=true
EVALUATION_SAMPLE_RATE=1.0

# ─── Feedback Loop ───
AUTO_PROMOTE_THRESHOLD=0.85
AUTO_RETIRE_THRESHOLD=0.40
```

### Model Tiers (for Cost Routing)

```python
# config/config.py — edit to customize tiers
MODEL_TIERS = {
    "free":    ["meta-llama/llama-3.3-8b-instruct:free"],
    "cheap":   ["google/gemini-2.0-flash-001", "openai/gpt-4o-mini"],
    "mid":     ["anthropic/claude-3.5-haiku", "google/gemini-2.0-flash-thinking-exp"],
    "premium": ["openai/gpt-4o", "anthropic/claude-sonnet-4", "google/gemini-2.5-pro-preview"],
}
```

## 📁 Project Structure

```
PROMPT-OPS/
├── config/
│   ├── __init__.py              # Exports settings, MODEL_TIERS, PROJECT_ROOT
│   └── config.py                # Pydantic Settings — all env vars, pricing, tiers
│
├── src/
│   ├── __init__.py              # Package version & metadata
│   │
│   ├── llm/                     # 🆕 LLM Gateway
│   │   ├── __init__.py
│   │   └── client.py            # OpenRouter HTTP client (httpx + tenacity retries)
│   │
│   ├── evaluation/              # 🆕 LLM-as-Judge
│   │   ├── __init__.py
│   │   └── evaluator.py         # 5-dimension quality scoring with judge LLM
│   │
│   ├── optimization/            # Optimization Engines
│   │   ├── __init__.py
│   │   ├── optimizer.py         # A/B testing & prompt version management
│   │   ├── temperature_optimizer.py  # 🆕 Temperature sweep experiments
│   │   └── cost_router.py       # 🆕 Tiered model cascade with quality gates
│   │
│   ├── pipeline/                # 🆕 Closed-Loop Orchestrator
│   │   ├── __init__.py
│   │   └── orchestrator.py      # THE main engine — pipeline.run()
│   │
│   ├── telemetry/               # Data Collection
│   │   ├── __init__.py
│   │   └── tracker.py           # Request-level telemetry logging
│   │
│   ├── monitoring/              # Observability
│   │   ├── __init__.py
│   │   └── monitor.py           # Aggregation, alerting, anomaly detection
│   │
│   └── database/                # Persistence Layer
│       ├── __init__.py
│       ├── models.py            # 8 SQLAlchemy tables (5 original + 3 new)
│       └── connection.py        # Session management, init, migrations
│
├── dashboard/
│   └── app.py                   # Streamlit dashboard (8 pages)
│
├── examples/
│   ├── demo.py                  # Simulated demo (no API key needed)
│   ├── real_demo.py             # 🆕 Live demo with OpenRouter API
│   ├── openai_integration.py    # OpenAI integration example
│   └── tutorial.ipynb           # Interactive tutorial
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── FAQ.md
│   ├── INDEX.md
│   └── PRESENTATION_GUIDE.md
│
├── .env.example                 # Environment variable template
├── requirements.txt             # Python dependencies
├── check_database.py            # Database health checker
└── README.md                    # ← You are here
```

## 🎯 Presentation Guide

### For Final Year Project Defense

#### 1. Start with the Problem (2 min)
- "LLMs are black boxes — you get a response but you don't know if it's good"
- "Companies spend thousands on API calls with no way to know which prompt or model works best"
- "Temperature is set by gut feeling, not data"

#### 2. Live Demo (5 min)
```powershell
# Show a real API call flowing through the system
python examples\real_demo.py

# Open the dashboard to see results
streamlit run dashboard\app.py
```
- Show the request flowing: Pipeline → LLM → Evaluation → Database → Dashboard
- Point at the quality scores appearing in real-time

#### 3. Architecture Walkthrough (3 min)
- Use the architecture diagram from this README
- Emphasize the **closed loop** — data flows back to improve decisions
- Compare to open-loop systems (just logging, no learning)

#### 4. Technical Deep Dive (5 min)
- **LLM-as-Judge**: Show `evaluator.py` — how one LLM evaluates another
- **Temperature Optimization**: Show the quality×consistency scoring formula
- **Cost Routing**: Show the tier cascade with quality gates
- **Database**: Show the 8-table schema in `models.py`

#### 5. Results & Analysis (3 min)
- Show A/B test results: "Version B improved quality by X%"
- Show temperature experiment: "Optimal temperature was 0.3, not the default 0.7"
- Show cost savings: "Routed 60% of requests to free tier with no quality loss"

### Key Talking Points for Recruiters

| Point | What to Say |
|-------|-------------|
| **System Design** | "I built a closed-loop system — not just CRUD, it learns from its own data" |
| **API Integration** | "Real HTTP clients with retry logic, timeout handling, error recovery" |
| **Data Engineering** | "8-table normalized schema, SQLAlchemy ORM, PostgreSQL-ready" |
| **ML/AI** | "LLM-as-Judge pattern, statistical temperature optimization, EMA-based learning" |
| **Full Stack** | "Python backend + Streamlit dashboard with Plotly visualizations" |
| **Production Thinking** | "Environment-based config, modular architecture, graceful degradation" |

## 🐛 Troubleshooting

### Common Issues

**Issue**: `OPENROUTER_API_KEY not set`
```powershell
# Make sure .env exists and has your key
copy .env.example .env
# Edit .env and paste your API key from https://openrouter.ai/keys
```

**Issue**: Import errors
```powershell
# Activate virtual environment first
.\venv\Scripts\Activate.ps1
# Make sure you're in the project root
cd "d:\extra-work\New folder\PROMPT-OPS\project"
# Install dependencies
pip install -r requirements.txt
```

**Issue**: Database errors / schema mismatch
```powershell
# Reinitialize the database (deletes existing data)
python -c "from src.database import db_manager; db_manager.drop_tables(); db_manager.create_tables()"
```

**Issue**: OpenRouter rate limiting / 429 errors
```
The system has built-in retry logic with exponential backoff.
If persistent, check your rate limits at https://openrouter.ai/settings/limits
Free tier models have lower rate limits.
```

**Issue**: LLM-as-Judge returns low scores
```
This is normal during initial runs — the judge is calibrated for production-quality responses.
Check the individual dimension scores to understand what's being penalized.
If the judge model itself is failing, try changing OPENROUTER_JUDGE_MODEL to a more capable model.
```

**Issue**: Dashboard shows no data
```powershell
# Generate data first with the demo
python examples\real_demo.py
# Then launch the dashboard
streamlit run dashboard\app.py
```

## 📝 Roadmap

### ✅ Implemented
- [x] Closed-loop telemetry with quality feedback
- [x] LLM-as-Judge automated evaluation (5 dimensions)
- [x] Temperature optimization via controlled experiments
- [x] Cost-aware model routing with tier cascade
- [x] A/B testing for prompt versions
- [x] Real-time monitoring & anomaly detection
- [x] 8-page interactive dashboard
- [x] OpenRouter integration (200+ models)

### 🔮 Future Enhancements
- [ ] Bayesian optimization for temperature (replace grid search)
- [ ] Semantic similarity scoring (embedding-based evaluation)
- [ ] Multi-turn conversation tracking
- [ ] Prompt template DSL with variable interpolation
- [ ] Webhook alerts (Slack, Discord, Email)
- [ ] Export reports to PDF/Excel
- [ ] Multi-user auth with role-based access
- [ ] Kubernetes deployment configs
- [ ] Integration with MLflow / Weights & Biases

## 📄 License

This project is created for educational purposes as a final year major project.

## 📧 Contact

For questions about this project, refer to the project documentation in the `docs/` folder.

---

<div align="center">

**Built with** ❤️ **for Final Year Major Project 2025**

*PROMPT-OPS: Closed-Loop Telemetry-Aware Prompt Optimization System*

**Real LLM calls • Real quality measurement • Real optimization**

</div>
