"""
Prompt Optimization and Versioning Module

This module handles prompt versioning, A/B testing, and automatic
optimization based on telemetry data.
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from sqlalchemy import and_, func
from loguru import logger

from src.database import db_manager, PromptVersion, TelemetryLog, OptimizationRun
from config import settings


class OptimizationGoal(Enum):
    """Optimization objectives."""
    LATENCY = "latency"  # Minimize latency
    COST = "cost"  # Minimize cost
    QUALITY = "quality"  # Maximize quality
    BALANCED = "balanced"  # Balance all metrics


class PromptManager:
    """
    Manages prompt versions and facilitates A/B testing.
    
    This class provides functionality for:
    - Creating and managing prompt versions
    - Selecting prompts for A/B testing
    - Tracking prompt performance
    """
    
    def create_prompt_version(
        self,
        prompt_id: str,
        template: str,
        name: str,
        description: Optional[str] = None,
        variables: Optional[Dict] = None,
        is_default: bool = False,
        ab_test_group: Optional[str] = None,
        traffic_weight: float = 1.0
    ) -> PromptVersion:
        """
        Create a new prompt version.
        
        Args:
            prompt_id: Unique identifier for the prompt
            template: The prompt template text
            name: Human-readable name
            description: Optional description
            variables: Template variables/placeholders
            is_default: Whether this is the default version
            ab_test_group: A/B test group identifier
            traffic_weight: Traffic allocation weight (for A/B testing)
            
        Returns:
            Created PromptVersion object
        """
        with db_manager.session_scope() as session:
            # Get next version number
            max_version = session.query(func.max(PromptVersion.version)).filter(
                PromptVersion.prompt_id == prompt_id
            ).scalar() or 0
            
            next_version = max_version + 1
            
            # If this is default, unset other defaults
            if is_default:
                session.query(PromptVersion).filter(
                    and_(
                        PromptVersion.prompt_id == prompt_id,
                        PromptVersion.is_default == True
                    )
                ).update({"is_default": False})
            
            # Create new version
            prompt_version = PromptVersion(
                prompt_id=prompt_id,
                version=next_version,
                template=template,
                name=name,
                description=description,
                variables=variables or {},
                is_default=is_default,
                ab_test_group=ab_test_group,
                traffic_weight=traffic_weight
            )
            
            session.add(prompt_version)
            session.flush()
            
            logger.info(f"Created prompt version: {prompt_id} v{next_version}")
            return prompt_version
    
    def get_prompt_for_request(
        self,
        prompt_id: str,
        ab_testing: bool = True
    ) -> Optional[PromptVersion]:
        """
        Get a prompt version for a request.
        
        This method implements traffic splitting for A/B testing.
        
        Args:
            prompt_id: Prompt identifier
            ab_testing: Whether to use A/B testing (random selection)
            
        Returns:
            Selected PromptVersion or None
        """
        with db_manager.session_scope() as session:
            # Get active versions
            versions = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.prompt_id == prompt_id,
                    PromptVersion.is_active == True
                )
            ).all()
            
            if not versions:
                return None
            
            # If not A/B testing, return default or first version
            if not ab_testing:
                default = next((v for v in versions if v.is_default), None)
                return default or versions[0]
            
            # A/B testing: weighted random selection
            total_weight = sum(v.traffic_weight for v in versions)
            rand_value = random.uniform(0, total_weight)
            
            cumulative_weight = 0
            for version in versions:
                cumulative_weight += version.traffic_weight
                if rand_value <= cumulative_weight:
                    return version
            
            return versions[0]  # Fallback
    
    def get_prompt_versions(
        self,
        prompt_id: str,
        active_only: bool = False
    ) -> List[PromptVersion]:
        """
        Get all versions of a prompt.
        
        Args:
            prompt_id: Prompt identifier
            active_only: Whether to return only active versions
            
        Returns:
            List of PromptVersion objects
        """
        with db_manager.session_scope() as session:
            query = session.query(PromptVersion).filter(
                PromptVersion.prompt_id == prompt_id
            )
            
            if active_only:
                query = query.filter(PromptVersion.is_active == True)
            
            return query.order_by(PromptVersion.version.desc()).all()
    
    def update_prompt_metrics(self, prompt_id: str, version: int):
        """
        Update aggregated metrics for a prompt version.
        
        Args:
            prompt_id: Prompt identifier
            version: Version number
        """
        with db_manager.session_scope() as session:
            # Get all telemetry for this version
            logs = session.query(TelemetryLog).filter(
                and_(
                    TelemetryLog.prompt_id == prompt_id,
                    TelemetryLog.prompt_version == version
                )
            ).all()
            
            if not logs:
                return
            
            # Calculate metrics
            total_calls = len(logs)
            successful_calls = sum(1 for log in logs if not log.is_error)
            
            latencies = [log.latency_ms for log in logs if log.latency_ms is not None]
            costs = [log.cost_usd for log in logs if log.cost_usd is not None]
            quality_scores = [log.quality_score for log in logs if log.quality_score is not None]
            
            # Update prompt version
            prompt_version = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.prompt_id == prompt_id,
                    PromptVersion.version == version
                )
            ).first()
            
            if prompt_version:
                prompt_version.total_calls = total_calls
                prompt_version.avg_latency_ms = sum(latencies) / len(latencies) if latencies else None
                prompt_version.avg_cost_usd = sum(costs) / len(costs) if costs else None
                prompt_version.avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else None
                prompt_version.success_rate = successful_calls / total_calls if total_calls > 0 else 0
                
                logger.debug(f"Updated metrics for {prompt_id} v{version}")
    
    def deactivate_version(self, prompt_id: str, version: int):
        """Deactivate a prompt version."""
        with db_manager.session_scope() as session:
            prompt_version = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.prompt_id == prompt_id,
                    PromptVersion.version == version
                )
            ).first()
            
            if prompt_version:
                prompt_version.is_active = False
                logger.info(f"Deactivated {prompt_id} v{version}")


class PromptOptimizer:
    """
    Automatic prompt optimization based on telemetry data.
    
    This class analyzes performance data and suggests or creates
    optimized prompt versions.
    """
    
    def __init__(self):
        """Initialize the optimizer."""
        self.min_samples = settings.min_samples_for_optimization
        self.prompt_manager = PromptManager()
    
    def analyze_prompt_performance(
        self,
        prompt_id: str,
        time_window_hours: int = 24
    ) -> Dict[str, any]:
        """
        Analyze performance of all versions of a prompt.
        
        Args:
            prompt_id: Prompt identifier
            time_window_hours: Time window for analysis
            
        Returns:
            Performance analysis results
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
        
        with db_manager.session_scope() as session:
            # Get all versions
            versions = session.query(PromptVersion).filter(
                PromptVersion.prompt_id == prompt_id
            ).all()
            
            results = {
                "prompt_id": prompt_id,
                "versions": [],
                "recommendation": None
            }
            
            for version in versions:
                # Get telemetry logs
                logs = session.query(TelemetryLog).filter(
                    and_(
                        TelemetryLog.prompt_id == prompt_id,
                        TelemetryLog.prompt_version == version.version,
                        TelemetryLog.timestamp >= cutoff_time
                    )
                ).all()
                
                if not logs:
                    continue
                
                # Calculate metrics
                version_stats = self._calculate_version_stats(logs, version)
                results["versions"].append(version_stats)
            
            # Determine best version
            if results["versions"]:
                results["recommendation"] = self._recommend_best_version(
                    results["versions"]
                )
            
            return results
    
    def _calculate_version_stats(
        self,
        logs: List[TelemetryLog],
        version: PromptVersion
    ) -> Dict[str, any]:
        """Calculate statistics for a prompt version."""
        total_calls = len(logs)
        successful_calls = sum(1 for log in logs if not log.is_error)
        
        latencies = [log.latency_ms for log in logs if log.latency_ms is not None]
        costs = [log.cost_usd for log in logs if log.cost_usd is not None]
        quality_scores = [log.quality_score for log in logs if log.quality_score is not None]
        
        return {
            "version": version.version,
            "name": version.name,
            "total_calls": total_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else None,
            "avg_cost_usd": sum(costs) / len(costs) if costs else None,
            "avg_quality_score": sum(quality_scores) / len(quality_scores) if quality_scores else None,
            "is_active": version.is_active,
            "is_default": version.is_default,
        }
    
    def _recommend_best_version(
        self,
        versions: List[Dict[str, any]],
        goal: OptimizationGoal = OptimizationGoal.BALANCED
    ) -> Dict[str, any]:
        """
        Recommend the best version based on optimization goal.
        
        Args:
            versions: List of version statistics
            goal: Optimization objective
            
        Returns:
            Recommendation dictionary
        """
        # Filter versions with enough data
        valid_versions = [
            v for v in versions 
            if v["total_calls"] >= self.min_samples
        ]
        
        if not valid_versions:
            return {
                "status": "insufficient_data",
                "message": f"Need at least {self.min_samples} samples per version"
            }
        
        # Score versions based on goal
        best_version = None
        best_score = float('-inf')
        
        for version in valid_versions:
            score = self._calculate_score(version, goal)
            if score > best_score:
                best_score = score
                best_version = version
        
        return {
            "status": "recommendation_available",
            "recommended_version": best_version["version"],
            "version_name": best_version["name"],
            "score": best_score,
            "metrics": best_version,
            "goal": goal.value
        }
    
    def _calculate_score(
        self,
        version: Dict[str, any],
        goal: OptimizationGoal
    ) -> float:
        """Calculate a score for a version based on the optimization goal."""
        if goal == OptimizationGoal.LATENCY:
            # Lower is better
            return -version["avg_latency_ms"] if version["avg_latency_ms"] else float('-inf')
        
        elif goal == OptimizationGoal.COST:
            # Lower is better
            return -version["avg_cost_usd"] if version["avg_cost_usd"] else float('-inf')
        
        elif goal == OptimizationGoal.QUALITY:
            # Higher is better
            return version["avg_quality_score"] if version["avg_quality_score"] else float('-inf')
        
        elif goal == OptimizationGoal.BALANCED:
            # Normalize and combine metrics
            # (This is a simple approach; you can use more sophisticated methods)
            components = []
            
            if version["avg_latency_ms"]:
                # Normalize latency (assume 2000ms is baseline)
                normalized_latency = max(0, 1 - version["avg_latency_ms"] / 2000)
                components.append(normalized_latency)
            
            if version["avg_cost_usd"]:
                # Normalize cost (assume $0.01 is baseline)
                normalized_cost = max(0, 1 - version["avg_cost_usd"] / 0.01)
                components.append(normalized_cost)
            
            if version["avg_quality_score"]:
                components.append(version["avg_quality_score"])
            
            # Include success rate
            components.append(version["success_rate"])
            
            return sum(components) / len(components) if components else float('-inf')
        
        return 0.0
    
    def run_optimization(
        self,
        prompt_id: str,
        goal: OptimizationGoal = OptimizationGoal.BALANCED
    ) -> Dict[str, any]:
        """
        Run automatic optimization for a prompt.
        
        Args:
            prompt_id: Prompt to optimize
            goal: Optimization objective
            
        Returns:
            Optimization results
        """
        run_id = f"opt_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{prompt_id}"
        
        # Create optimization run record
        with db_manager.session_scope() as session:
            opt_run = OptimizationRun(
                run_id=run_id,
                prompt_id=prompt_id,
                optimization_goal=goal.value,
                status="running",
                strategy_used="comparative_analysis"
            )
            session.add(opt_run)
            session.flush()
            
            run_record_id = opt_run.id
        
        try:
            # Analyze current performance
            analysis = self.analyze_prompt_performance(prompt_id)
            
            if not analysis.get("recommendation"):
                return {
                    "status": "no_recommendation",
                    "message": "Insufficient data for optimization"
                }
            
            recommendation = analysis["recommendation"]
            
            if recommendation["status"] != "recommendation_available":
                return recommendation
            
            # Update optimization run
            with db_manager.session_scope() as session:
                opt_run = session.query(OptimizationRun).filter(
                    OptimizationRun.id == run_record_id
                ).first()
                
                if opt_run:
                    opt_run.status = "completed"
                    opt_run.completed_at = datetime.utcnow()
                    opt_run.optimized_version = recommendation["recommended_version"]
                    opt_run.optimized_score = recommendation["score"]
                    opt_run.details = analysis
            
            logger.info(f"Optimization completed for {prompt_id}: {recommendation}")
            
            return {
                "status": "success",
                "run_id": run_id,
                "recommendation": recommendation,
                "full_analysis": analysis
            }
            
        except Exception as e:
            # Mark run as failed
            with db_manager.session_scope() as session:
                opt_run = session.query(OptimizationRun).filter(
                    OptimizationRun.id == run_record_id
                ).first()
                
                if opt_run:
                    opt_run.status = "failed"
                    opt_run.completed_at = datetime.utcnow()
            
            logger.error(f"Optimization failed for {prompt_id}: {e}")
            raise


# Global instances
prompt_manager = PromptManager()
prompt_optimizer = PromptOptimizer()
