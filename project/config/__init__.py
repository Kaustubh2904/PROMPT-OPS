"""
Configuration package for PROMPT-OPS.

Exports:
    settings      — Pydantic Settings instance (reads .env)
    FREE_MODELS   — List of free OpenRouter models
    MODEL_TIERS   — Tier→model mapping for cost routing
    MODEL_PRICING — Per-model cost info
    PROJECT_ROOT  — Absolute path to the project root
    get_model_cost— Helper to estimate cost given model + tokens
"""

from .config import (
    settings,
    FREE_MODELS,
    MODEL_TIERS,
    MODEL_PRICING,
    PROJECT_ROOT,
    get_model_cost,
)

__all__ = [
    "settings",
    "FREE_MODELS",
    "MODEL_TIERS",
    "MODEL_PRICING",
    "PROJECT_ROOT",
    "get_model_cost",
]
