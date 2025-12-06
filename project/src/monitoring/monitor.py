"""
Model Monitoring and Analytics Module

This module provides real-time monitoring, metrics aggregation,
and anomaly detection for LLM models.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import statistics

from sqlalchemy import func, and_
from loguru import logger

from src.database import db_manager, TelemetryLog, ModelMetrics, Alert
from config import settings


class ModelMonitor:
    """
    Monitors model performance and detects anomalies.
    
    This class aggregates telemetry data and generates alerts
    when metrics exceed configured thresholds.
    """
    
    def __init__(self):
        """Initialize the model monitor."""
        self.latency_threshold = settings.latency_threshold_ms
        self.error_rate_threshold = settings.error_rate_threshold
        self.cost_threshold = settings.cost_threshold_usd
    
    def get_model_stats(
        self,
        model_name: str,
        time_window_hours: int = 24
    ) -> Dict[str, any]:
        """
        Get comprehensive statistics for a model.
        
        Args:
            model_name: Name of the model
            time_window_hours: Time window to analyze (hours)
            
        Returns:
            Dictionary containing model statistics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        with db_manager.session_scope() as session:
            # Query telemetry logs
            logs = session.query(TelemetryLog).filter(
                and_(
                    TelemetryLog.model_name == model_name,
                    TelemetryLog.timestamp >= cutoff_time
                )
            ).all()
            
            if not logs:
                return self._empty_stats(model_name)
            
            # Calculate statistics
            stats = self._calculate_stats(logs, model_name)
            
            # Check for threshold violations
            self._check_thresholds(stats, model_name)
            
            return stats
    
    def get_all_models_summary(
        self,
        time_window_hours: int = 24
    ) -> List[Dict[str, any]]:
        """
        Get summary statistics for all models.
        
        Args:
            time_window_hours: Time window to analyze (hours)
            
        Returns:
            List of dictionaries containing model summaries
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        with db_manager.session_scope() as session:
            # Get unique model names
            models = session.query(TelemetryLog.model_name).filter(
                TelemetryLog.timestamp >= cutoff_time
            ).distinct().all()
            
            summaries = []
            for (model_name,) in models:
                stats = self.get_model_stats(model_name, time_window_hours)
                summaries.append(stats)
            
            return summaries
    
    def _calculate_stats(
        self,
        logs: List[TelemetryLog],
        model_name: str
    ) -> Dict[str, any]:
        """Calculate statistics from telemetry logs."""
        total_requests = len(logs)
        successful_requests = sum(1 for log in logs if not log.is_error)
        failed_requests = total_requests - successful_requests
        
        # Latency statistics
        latencies = [log.latency_ms for log in logs if log.latency_ms is not None]
        
        # Token statistics
        input_tokens = [log.input_tokens for log in logs if log.input_tokens is not None]
        output_tokens = [log.output_tokens for log in logs if log.output_tokens is not None]
        
        # Cost statistics
        costs = [log.cost_usd for log in logs if log.cost_usd is not None]
        
        # Quality statistics
        quality_scores = [log.quality_score for log in logs if log.quality_score is not None]
        
        # Feedback statistics
        positive_feedback = sum(1 for log in logs if log.user_feedback == "positive")
        negative_feedback = sum(1 for log in logs if log.user_feedback == "negative")
        
        return {
            "model_name": model_name,
            "time_window": "24h",
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": failed_requests,
            "success_rate": successful_requests / total_requests if total_requests > 0 else 0,
            "error_rate": failed_requests / total_requests if total_requests > 0 else 0,
            
            # Latency metrics
            "avg_latency_ms": statistics.mean(latencies) if latencies else None,
            "median_latency_ms": statistics.median(latencies) if latencies else None,
            "p95_latency_ms": self._percentile(latencies, 0.95) if latencies else None,
            "p99_latency_ms": self._percentile(latencies, 0.99) if latencies else None,
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
            
            # Token metrics
            "total_input_tokens": sum(input_tokens) if input_tokens else 0,
            "total_output_tokens": sum(output_tokens) if output_tokens else 0,
            "avg_input_tokens": statistics.mean(input_tokens) if input_tokens else None,
            "avg_output_tokens": statistics.mean(output_tokens) if output_tokens else None,
            
            # Cost metrics
            "total_cost_usd": sum(costs) if costs else 0,
            "avg_cost_per_request": statistics.mean(costs) if costs else None,
            
            # Quality metrics
            "avg_quality_score": statistics.mean(quality_scores) if quality_scores else None,
            "positive_feedback_count": positive_feedback,
            "negative_feedback_count": negative_feedback,
            "feedback_ratio": positive_feedback / (positive_feedback + negative_feedback) 
                             if (positive_feedback + negative_feedback) > 0 else None,
        }
    
    def _empty_stats(self, model_name: str) -> Dict[str, any]:
        """Return empty statistics structure."""
        return {
            "model_name": model_name,
            "total_requests": 0,
            "message": "No data available for the specified time window"
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile value."""
        if not values:
            return None
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _check_thresholds(self, stats: Dict[str, any], model_name: str):
        """Check if any metrics exceed thresholds and create alerts."""
        alerts_to_create = []
        
        # Check latency
        if stats.get("avg_latency_ms") and stats["avg_latency_ms"] > self.latency_threshold:
            alerts_to_create.append({
                "alert_type": "high_latency",
                "severity": "medium",
                "model_name": model_name,
                "message": f"Average latency ({stats['avg_latency_ms']:.2f}ms) exceeds threshold ({self.latency_threshold}ms)",
                "threshold_value": self.latency_threshold,
                "actual_value": stats["avg_latency_ms"]
            })
        
        # Check error rate
        if stats.get("error_rate") and stats["error_rate"] > self.error_rate_threshold:
            alerts_to_create.append({
                "alert_type": "high_error_rate",
                "severity": "high",
                "model_name": model_name,
                "message": f"Error rate ({stats['error_rate']:.2%}) exceeds threshold ({self.error_rate_threshold:.2%})",
                "threshold_value": self.error_rate_threshold,
                "actual_value": stats["error_rate"]
            })
        
        # Check cost
        if stats.get("total_cost_usd") and stats["total_cost_usd"] > self.cost_threshold:
            alerts_to_create.append({
                "alert_type": "high_cost",
                "severity": "medium",
                "model_name": model_name,
                "message": f"Total cost (${stats['total_cost_usd']:.2f}) exceeds threshold (${self.cost_threshold})",
                "threshold_value": self.cost_threshold,
                "actual_value": stats["total_cost_usd"]
            })
        
        # Create alerts
        if alerts_to_create:
            self._create_alerts(alerts_to_create)
    
    def _create_alerts(self, alerts_data: List[Dict[str, any]]):
        """Create alert records in the database."""
        try:
            with db_manager.session_scope() as session:
                for alert_data in alerts_data:
                    alert = Alert(**alert_data)
                    session.add(alert)
                    logger.warning(f"Alert created: {alert_data['message']}")
        except Exception as e:
            logger.error(f"Failed to create alerts: {e}")
    
    def get_active_alerts(self, model_name: Optional[str] = None) -> List[Alert]:
        """
        Get active (unresolved) alerts.
        
        Args:
            model_name: Optional filter by model name
            
        Returns:
            List of active Alert objects
        """
        with db_manager.session_scope() as session:
            query = session.query(Alert).filter(Alert.is_resolved == False)
            
            if model_name:
                query = query.filter(Alert.model_name == model_name)
            
            alerts = query.order_by(Alert.triggered_at.desc()).all()
            
            # Eagerly load all attributes to avoid DetachedInstanceError
            for alert in alerts:
                # Access all attributes to load them before session closes
                _ = (alert.id, alert.alert_type, alert.severity, alert.triggered_at,
                     alert.resolved_at, alert.model_name, alert.prompt_id, alert.message,
                     alert.threshold_value, alert.actual_value, alert.is_resolved,
                     alert.extra_metadata)
                # Expunge from session to make it independent
                session.expunge(alert)
            
            return alerts
    
    def resolve_alert(self, alert_id: int):
        """
        Mark an alert as resolved.
        
        Args:
            alert_id: ID of the alert to resolve
        """
        try:
            with db_manager.session_scope() as session:
                alert = session.query(Alert).filter(Alert.id == alert_id).first()
                if alert:
                    alert.is_resolved = True
                    alert.resolved_at = datetime.utcnow()
                    logger.info(f"Alert {alert_id} resolved")
        except Exception as e:
            logger.error(f"Failed to resolve alert {alert_id}: {e}")
    
    def aggregate_hourly_metrics(self, hours_back: int = 24):
        """
        Aggregate telemetry data into hourly metrics.
        
        This is useful for creating time-series visualizations
        and reducing database query load.
        
        Args:
            hours_back: Number of hours to aggregate
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        with db_manager.session_scope() as session:
            # Get unique models and hours
            logs = session.query(TelemetryLog).filter(
                TelemetryLog.timestamp >= cutoff_time
            ).all()
            
            # Group by model and hour
            grouped = defaultdict(lambda: defaultdict(list))
            for log in logs:
                hour_key = log.timestamp.replace(minute=0, second=0, microsecond=0)
                grouped[log.model_name][hour_key].append(log)
            
            # Create metric records
            for model_name, hours_data in grouped.items():
                for hour, hour_logs in hours_data.items():
                    stats = self._calculate_stats(hour_logs, model_name)
                    
                    # Check if metric already exists
                    existing = session.query(ModelMetrics).filter(
                        and_(
                            ModelMetrics.model_name == model_name,
                            ModelMetrics.timestamp == hour,
                            ModelMetrics.window_size == "hourly"
                        )
                    ).first()
                    
                    if not existing:
                        metric = ModelMetrics(
                            timestamp=hour,
                            window_size="hourly",
                            model_name=model_name,
                            provider=hour_logs[0].provider if hour_logs else "unknown",
                            total_requests=stats["total_requests"],
                            successful_requests=stats["successful_requests"],
                            failed_requests=stats["failed_requests"],
                            avg_latency_ms=stats["avg_latency_ms"],
                            p50_latency_ms=stats["median_latency_ms"],
                            p95_latency_ms=stats["p95_latency_ms"],
                            p99_latency_ms=stats["p99_latency_ms"],
                            total_input_tokens=stats["total_input_tokens"],
                            total_output_tokens=stats["total_output_tokens"],
                            total_cost_usd=stats["total_cost_usd"],
                            avg_cost_per_request=stats["avg_cost_per_request"],
                            avg_quality_score=stats["avg_quality_score"],
                            positive_feedback_count=stats["positive_feedback_count"],
                            negative_feedback_count=stats["negative_feedback_count"],
                        )
                        session.add(metric)
            
            logger.info(f"Aggregated metrics for {len(grouped)} models")
    
    def detect_anomalies(
        self,
        model_name: str,
        metric: str = "latency_ms",
        sensitivity: float = 2.0
    ) -> List[Dict[str, any]]:
        """
        Detect anomalies using statistical methods (Z-score).
        
        Args:
            model_name: Name of the model to analyze
            metric: Metric to check for anomalies
            sensitivity: Number of standard deviations for anomaly threshold
            
        Returns:
            List of anomalous data points
        """
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        with db_manager.session_scope() as session:
            logs = session.query(TelemetryLog).filter(
                and_(
                    TelemetryLog.model_name == model_name,
                    TelemetryLog.timestamp >= cutoff_time,
                    TelemetryLog.is_error == False
                )
            ).all()
            
            if len(logs) < 10:
                return []
            
            # Get metric values
            values = []
            for log in logs:
                if metric == "latency_ms" and log.latency_ms:
                    values.append((log.timestamp, log.latency_ms, log.request_id))
                elif metric == "cost_usd" and log.cost_usd:
                    values.append((log.timestamp, log.cost_usd, log.request_id))
                elif metric == "total_tokens" and log.total_tokens:
                    values.append((log.timestamp, log.total_tokens, log.request_id))
            
            if len(values) < 10:
                return []
            
            # Calculate mean and std
            metric_values = [v[1] for v in values]
            mean = statistics.mean(metric_values)
            std = statistics.stdev(metric_values)
            
            # Find anomalies
            anomalies = []
            for timestamp, value, request_id in values:
                z_score = abs((value - mean) / std) if std > 0 else 0
                if z_score > sensitivity:
                    anomalies.append({
                        "timestamp": timestamp,
                        "metric": metric,
                        "value": value,
                        "mean": mean,
                        "z_score": z_score,
                        "request_id": request_id
                    })
            
            return anomalies


# Global monitor instance
monitor = ModelMonitor()
