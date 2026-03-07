"""
Database Models for Telemetry System

This module defines the database schema using SQLAlchemy ORM.
It stores all telemetry data, prompt versions, and optimization results.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, ForeignKey, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class TelemetryLog(Base):
    """
    Stores telemetry data for each LLM API call.
    
    This table captures comprehensive metrics about every model invocation,
    including timing, tokens, costs, and outcomes.
    """
    __tablename__ = "telemetry_logs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Request Information
    request_id = Column(String(100), unique=True, index=True)
    model_name = Column(String(100), index=True)
    provider = Column(String(50), index=True)  # openai, anthropic, etc.
    
    # Prompt Information
    prompt_id = Column(String(100), ForeignKey("prompt_versions.prompt_id"), index=True)
    prompt_version = Column(Integer)
    prompt_text = Column(Text)
    
    # Token Usage
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # Performance Metrics
    latency_ms = Column(Float)  # Response time in milliseconds
    cost_usd = Column(Float)  # Cost in USD
    
    # Response Information
    response_text = Column(Text)
    response_length = Column(Integer)
    
    # Quality Metrics
    quality_score = Column(Float, nullable=True)  # 0-1 score
    user_feedback = Column(String(20), nullable=True)  # positive, negative, neutral
    
    # Error Tracking
    is_error = Column(Boolean, default=False, index=True)
    error_type = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Additional Metadata
    extra_metadata = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)  # For categorization
    
    # Relationships
    prompt = relationship("PromptVersion", back_populates="telemetry_logs")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_model', 'timestamp', 'model_name'),
        Index('idx_prompt_timestamp', 'prompt_id', 'timestamp'),
    )


class PromptVersion(Base):
    """
    Stores different versions of prompts for A/B testing and optimization.
    
    Each prompt can have multiple versions, allowing us to compare
    performance and automatically select the best-performing variant.
    """
    __tablename__ = "prompt_versions"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Prompt Identification
    prompt_id = Column(String(100), index=True)  # Unique identifier for a prompt
    version = Column(Integer)  # Version number
    
    # Prompt Content
    template = Column(Text)  # The actual prompt template
    variables = Column(JSON, nullable=True)  # Template variables/placeholders
    
    # Metadata
    name = Column(String(200))
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    is_default = Column(Boolean, default=False)
    
    # Performance Metrics (aggregated)
    total_calls = Column(Integer, default=0)
    avg_latency_ms = Column(Float, nullable=True)
    avg_cost_usd = Column(Float, nullable=True)
    avg_quality_score = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True)
    
    # A/B Testing
    ab_test_group = Column(String(50), nullable=True)  # e.g., 'control', 'variant_a'
    traffic_weight = Column(Float, default=1.0)  # For traffic splitting
    
    # Relationships
    telemetry_logs = relationship("TelemetryLog", back_populates="prompt")
    
    # Unique constraint
    __table_args__ = (
        Index('idx_prompt_version', 'prompt_id', 'version', unique=True),
    )


class ModelMetrics(Base):
    """
    Aggregated metrics per model for monitoring and alerting.
    
    This table stores hourly/daily aggregations to enable
    efficient querying of historical trends and anomaly detection.
    """
    __tablename__ = "model_metrics"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Time Window
    timestamp = Column(DateTime, index=True)
    window_size = Column(String(20))  # 'hourly', 'daily', 'weekly'
    
    # Model Information
    model_name = Column(String(100), index=True)
    provider = Column(String(50))
    
    # Aggregated Metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    
    # Performance Stats
    avg_latency_ms = Column(Float)
    p50_latency_ms = Column(Float)
    p95_latency_ms = Column(Float)
    p99_latency_ms = Column(Float)
    
    # Token Usage
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    avg_tokens_per_request = Column(Float)
    
    # Costs
    total_cost_usd = Column(Float)
    avg_cost_per_request = Column(Float)
    
    # Quality Metrics
    avg_quality_score = Column(Float, nullable=True)
    positive_feedback_count = Column(Integer, default=0)
    negative_feedback_count = Column(Integer, default=0)
    
    # Unique constraint
    __table_args__ = (
        Index('idx_metrics_time_model', 'timestamp', 'window_size', 'model_name', unique=True),
    )


class Alert(Base):
    """
    Stores alerts triggered by threshold violations or anomalies.
    
    Alerts help identify issues in production, such as high latency,
    increased error rates, or unexpected cost spikes.
    """
    __tablename__ = "alerts"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Alert Information
    alert_type = Column(String(50), index=True)  # latency, error_rate, cost, drift
    severity = Column(String(20), index=True)  # low, medium, high, critical
    
    # Timestamps
    triggered_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Context
    model_name = Column(String(100), nullable=True)
    prompt_id = Column(String(100), nullable=True)
    
    # Alert Details
    message = Column(Text)
    threshold_value = Column(Float, nullable=True)
    actual_value = Column(Float, nullable=True)
    
    # Status
    is_resolved = Column(Boolean, default=False, index=True)
    
    # Additional Data
    extra_metadata = Column(JSON, nullable=True)


class OptimizationRun(Base):
    """
    Tracks prompt optimization experiments and their results.
    
    This table logs all automatic optimization attempts, making it
    possible to audit changes and understand optimization history.
    """
    __tablename__ = "optimization_runs"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Run Information
    run_id = Column(String(100), unique=True, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Optimization Target
    prompt_id = Column(String(100), index=True)
    optimization_goal = Column(String(50))  # latency, cost, quality, balanced
    
    # Results
    baseline_version = Column(Integer)
    optimized_version = Column(Integer, nullable=True)
    
    # Metrics Improvement
    baseline_score = Column(Float)
    optimized_score = Column(Float, nullable=True)
    improvement_percentage = Column(Float, nullable=True)
    
    # Status
    status = Column(String(20), index=True)  # running, completed, failed
    
    # Details
    strategy_used = Column(String(100))  # What optimization strategy was used
    details = Column(JSON, nullable=True)


class EvaluationResult(Base):
    """
    Stores LLM-as-Judge evaluation results.
    
    Each row is an automated quality assessment of one LLM response.
    This is the key data that closes the feedback loop.
    """
    __tablename__ = "evaluation_results"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to the original request
    request_id = Column(String(100), index=True)
    prompt_id = Column(String(100), index=True, nullable=True)
    prompt_version = Column(Integer, nullable=True)
    model_name = Column(String(100), index=True)
    
    # Evaluation scores (0.0 - 1.0)
    relevance = Column(Float)
    accuracy = Column(Float)
    completeness = Column(Float)
    format_compliance = Column(Float)
    safety = Column(Float)
    composite_score = Column(Float, index=True)
    
    # Judge metadata
    reasoning = Column(Text, nullable=True)
    judge_model = Column(String(100))
    judge_latency_ms = Column(Float, nullable=True)
    judge_cost_usd = Column(Float, nullable=True)
    
    # Timestamps
    evaluated_at = Column(DateTime, default=datetime.utcnow, index=True)


class TemperatureExperiment(Base):
    """
    Records temperature optimization experiments.
    
    Each row is a complete experiment testing multiple temperature
    values for a specific prompt.
    """
    __tablename__ = "temperature_experiments"

    id = Column(Integer, primary_key=True, index=True)
    
    experiment_id = Column(String(100), unique=True, index=True)
    prompt_id = Column(String(100), index=True)
    model_name = Column(String(100))
    
    # Results
    best_temperature = Column(Float)
    best_quality_score = Column(Float)
    total_trials = Column(Integer)
    total_cost_usd = Column(Float)
    
    # Detailed results per temperature (JSON)
    results_json = Column(JSON, nullable=True)
    
    # Timestamps & status
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), index=True)  # running, completed, failed


class CostRoutingLog(Base):
    """
    Logs cost-aware routing decisions.
    
    Tracks when requests were downgraded to cheaper models
    and the quality/cost outcomes.
    """
    __tablename__ = "cost_routing_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    routing_id = Column(String(100), unique=True, index=True)
    prompt_id = Column(String(100), index=True, nullable=True)
    
    # Routing decision
    original_model = Column(String(100))
    routed_model = Column(String(100))
    tier_used = Column(String(50))
    
    # Outcome
    quality_score = Column(Float, nullable=True)
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text, nullable=True)
    cost_saved_usd = Column(Float, default=0.0)
    latency_ms = Column(Float, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
