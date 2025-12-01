"""
Configuration Management Module

This module handles all configuration settings for the telemetry system.
It uses pydantic for validation and python-dotenv for environment variables.
"""

from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from pathlib import Path


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    This class uses Pydantic's BaseSettings to automatically load
    configuration from .env files and environment variables.
    """
    
    # API Keys
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(None, env="ANTHROPIC_API_KEY")
    
    # Database
    database_url: str = Field(
        "sqlite:///./telemetry.db",
        env="DATABASE_URL",
        description="Database connection string"
    )
    
    # Telemetry Settings
    enable_telemetry: bool = Field(True, env="ENABLE_TELEMETRY")
    enable_prometheus: bool = Field(False, env="ENABLE_PROMETHEUS")
    prometheus_port: int = Field(8000, env="PROMETHEUS_PORT")
    
    # Alert Thresholds
    latency_threshold_ms: float = Field(2000.0, env="LATENCY_THRESHOLD_MS")
    error_rate_threshold: float = Field(0.05, env="ERROR_RATE_THRESHOLD")
    cost_threshold_usd: float = Field(10.0, env="COST_THRESHOLD_USD")
    
    # Prompt Optimization
    auto_optimize_enabled: bool = Field(True, env="AUTO_OPTIMIZE_ENABLED")
    min_samples_for_optimization: int = Field(10, env="MIN_SAMPLES_FOR_OPTIMIZATION")
    optimization_interval_hours: int = Field(24, env="OPTIMIZATION_INTERVAL_HOURS")
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    log_file: str = Field("logs/telemetry.log", env="LOG_FILE")
    
    # Directories
    data_dir: Path = Field(Path("data"), description="Directory for storing data")
    logs_dir: Path = Field(Path("logs"), description="Directory for log files")
    
    @validator("log_level")
    def validate_log_level(cls, v):
        """Validate log level is a valid option."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("error_rate_threshold")
    def validate_error_rate(cls, v):
        """Validate error rate is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Error rate threshold must be between 0 and 1")
        return v
    
    def create_directories(self):
        """Create necessary directories if they don't exist."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
settings.create_directories()


# Model pricing configuration (cost per 1K tokens)
MODEL_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
}


def get_model_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate the cost of a model call based on token usage.
    
    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        
    Returns:
        Total cost in USD
    """
    pricing = MODEL_PRICING.get(model, {"input": 0.0, "output": 0.0})
    input_cost = (input_tokens / 1000) * pricing["input"]
    output_cost = (output_tokens / 1000) * pricing["output"]
    return input_cost + output_cost
