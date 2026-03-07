"""
PROMPT-OPS: Closed-Loop Telemetry-Aware Prompt Optimization System

Source package providing:
- llm/         → Real LLM API calls via OpenRouter
- telemetry/   → Request tracking and metrics collection
- database/    → ORM models and persistence
- monitoring/  → Metrics aggregation, anomaly detection, alerting
- evaluation/  → LLM-as-Judge automated quality scoring
- optimization/→ Prompt versioning, A/B testing, temperature & cost optimization
- pipeline/    → The closed-loop orchestrator tying everything together
"""

__version__ = "1.0.0"
