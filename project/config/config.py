"""
PROMPT-OPS Configuration Module

Centralised settings read from environment variables / .env file.
Uses pydantic-settings for validation and type coercion.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings
from pydantic import Field


# ── Project root ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # ── OpenRouter API ──────────────────────────────────────
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_default_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        alias="OPENROUTER_DEFAULT_MODEL",
    )
    openrouter_judge_model: str = Field(
        default="meta-llama/llama-3.3-70b-instruct:free",
        alias="OPENROUTER_JUDGE_MODEL",
    )

    # ── Database ────────────────────────────────────────────
    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT / 'data' / 'prompt_ops.db'}",
        alias="DATABASE_URL",
    )

    # ── Telemetry ───────────────────────────────────────────
    enable_telemetry: bool = Field(default=True, alias="ENABLE_TELEMETRY")

    # ── Alert thresholds ────────────────────────────────────
    latency_threshold_ms: float = Field(default=5000.0, alias="LATENCY_THRESHOLD_MS")
    error_rate_threshold: float = Field(default=0.10, alias="ERROR_RATE_THRESHOLD")
    cost_threshold_usd: float = Field(default=1.0, alias="COST_THRESHOLD_USD")

    # ── Optimisation ────────────────────────────────────────
    auto_optimize_enabled: bool = Field(default=True, alias="AUTO_OPTIMIZE_ENABLED")
    min_samples_for_optimization: int = Field(default=5, alias="MIN_SAMPLES_FOR_OPTIMIZATION")

    # ── Temperature optimisation ────────────────────────────
    temperature_min: float = Field(default=0.0, alias="TEMPERATURE_MIN")
    temperature_max: float = Field(default=1.5, alias="TEMPERATURE_MAX")
    temperature_step: float = Field(default=0.5, alias="TEMPERATURE_STEP")
    temperature_trials_per_step: int = Field(default=2, alias="TEMPERATURE_TRIALS_PER_STEP")

    # ── Cost routing ────────────────────────────────────────
    cost_routing_enabled: bool = Field(default=True, alias="COST_ROUTING_ENABLED")
    quality_threshold_for_downgrade: float = Field(
        default=0.6, alias="QUALITY_THRESHOLD_FOR_DOWNGRADE"
    )

    # ── Evaluation ──────────────────────────────────────────
    auto_evaluate: bool = Field(default=True, alias="AUTO_EVALUATE")
    evaluation_sample_rate: float = Field(default=1.0, alias="EVALUATION_SAMPLE_RATE")

    # ── Feedback loop ───────────────────────────────────────
    feedback_loop_enabled: bool = Field(default=True, alias="FEEDBACK_LOOP_ENABLED")
    auto_promote_threshold: float = Field(default=0.15, alias="AUTO_PROMOTE_THRESHOLD")
    auto_retire_threshold: float = Field(default=0.20, alias="AUTO_RETIRE_THRESHOLD")

    # ── Logging ─────────────────────────────────────────────
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }


# ── Singleton settings instance ─────────────────────────────
settings = Settings()


# ── Free models available on OpenRouter ─────────────────────
FREE_MODELS = [
    "google/gemma-3-4b-it:free",                          # Tier 1 – small/fast
    "meta-llama/llama-3.2-3b-instruct:free",              # Tier 1 – small/fast
    "meta-llama/llama-3.3-70b-instruct:free",             # Tier 2 – mid (default)
    "mistralai/mistral-small-3.1-24b-instruct:free",      # Tier 2 – mid
    "qwen/qwen3-4b:free",                                 # Tier 3 – larger
    "nvidia/nemotron-nano-9b-v2:free",                    # Tier 3 – larger
    "google/gemma-3-12b-it:free",                         # Tier 4 – strongest free
    "google/gemma-3-27b-it:free",                         # Tier 4 – strongest free
]


# ── Model tiers for cost-aware routing ──────────────────────
MODEL_TIERS = {
    "tier_1": [
        "google/gemma-3-4b-it:free",
        "meta-llama/llama-3.2-3b-instruct:free",
    ],
    "tier_2": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",
    ],
    "tier_3": [
        "qwen/qwen3-4b:free",
        "nvidia/nemotron-nano-9b-v2:free",
    ],
    "tier_4": [
        "google/gemma-3-12b-it:free",
        "google/gemma-3-27b-it:free",
    ],
    "premium": [
        "openai/gpt-4o",
        "anthropic/claude-sonnet-4",
        "google/gemini-2.5-pro-preview",
    ],
}


# ── Model pricing (per 1 000 tokens) ───────────────────────
# Free models all cost $0.  Premium models have real prices.
MODEL_PRICING = {
    # Free tier – $0
    "google/gemma-3-4b-it:free":                          {"input": 0.0, "output": 0.0},
    "meta-llama/llama-3.2-3b-instruct:free":              {"input": 0.0, "output": 0.0},
    "meta-llama/llama-3.3-70b-instruct:free":             {"input": 0.0, "output": 0.0},
    "mistralai/mistral-small-3.1-24b-instruct:free":      {"input": 0.0, "output": 0.0},
    "qwen/qwen3-4b:free":                                 {"input": 0.0, "output": 0.0},
    "nvidia/nemotron-nano-9b-v2:free":                    {"input": 0.0, "output": 0.0},
    "google/gemma-3-12b-it:free":                         {"input": 0.0, "output": 0.0},
    "google/gemma-3-27b-it:free":                         {"input": 0.0, "output": 0.0},
    # Premium tier – approximate $/1k tokens
    "openai/gpt-4o":                                      {"input": 0.005,  "output": 0.015},
    "openai/gpt-4o-mini":                                 {"input": 0.00015,"output": 0.0006},
    "anthropic/claude-sonnet-4":                          {"input": 0.003,  "output": 0.015},
    "google/gemini-2.0-flash-001":                        {"input": 0.0001, "output": 0.0004},
    "google/gemini-2.5-pro-preview":                      {"input": 0.00125,"output": 0.01},
}


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of an LLM call.

    Args:
        model: Model identifier (e.g. "openai/gpt-4o")
        input_tokens: Number of prompt tokens
        output_tokens: Number of completion tokens

    Returns:
        Estimated cost in USD
    """
    pricing = MODEL_PRICING.get(model, {"input": 0.001, "output": 0.002})
    cost = (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
    return round(cost, 8)
