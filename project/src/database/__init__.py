"""Database package for the telemetry system."""

from .models import (
    Base,
    TelemetryLog,
    PromptVersion,
    ModelMetrics,
    Alert,
    OptimizationRun,
    EvaluationResult,
    TemperatureExperiment,
    CostRoutingLog,
)
from .connection import (
    DatabaseManager,
    db_manager,
    init_database,
    get_db
)

__all__ = [
    "Base",
    "TelemetryLog",
    "PromptVersion",
    "ModelMetrics",
    "Alert",
    "OptimizationRun",
    "EvaluationResult",
    "TemperatureExperiment",
    "CostRoutingLog",
    "DatabaseManager",
    "db_manager",
    "init_database",
    "get_db",
]
