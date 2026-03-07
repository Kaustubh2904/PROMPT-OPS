"""
Temperature Optimizer Module

Systematically finds the optimal temperature for each prompt by running
controlled experiments across the temperature range.

Temperature controls the randomness/creativity of LLM outputs:
  - 0.0 → Deterministic, always picks the most likely token
  - 0.7 → Balanced creativity and consistency (common default)
  - 1.5 → Very creative/random, may produce unexpected output

Different prompts need different temperatures:
  - Factual Q&A → Low temp (0.0–0.3)
  - Summarization → Medium temp (0.3–0.7)
  - Creative writing → High temp (0.7–1.2)

This module runs experiments to PROVE which temperature is best
rather than guessing.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from loguru import logger

from config import settings
from src.database import db_manager


@dataclass
class TemperatureTrialResult:
    """Result of a single trial at a specific temperature."""
    temperature: float
    quality_score: float
    latency_ms: float
    cost_usd: float
    output_length: int
    content: str = ""
    error: Optional[str] = None


@dataclass
class TemperatureExperimentResult:
    """Aggregated result of a full temperature experiment."""
    experiment_id: str
    prompt_id: str
    model: str
    best_temperature: float
    best_quality_score: float
    results_by_temp: Dict[float, Dict[str, Any]] = field(default_factory=dict)
    total_trials: int = 0
    total_cost_usd: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: str = "running"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "prompt_id": self.prompt_id,
            "model": self.model,
            "best_temperature": self.best_temperature,
            "best_quality_score": self.best_quality_score,
            "results_by_temp": self.results_by_temp,
            "total_trials": self.total_trials,
            "total_cost_usd": self.total_cost_usd,
            "status": self.status,
        }


class TemperatureOptimizer:
    """
    Finds the optimal temperature for a given prompt through experimentation.

    Algorithm:
    1. For each temperature in [min, max] with step:
       a. Run N trials with the same prompt
       b. Evaluate quality of each response (via LLM-as-Judge)
       c. Record avg quality, latency, cost, consistency
    2. Score each temperature point:
       Score = α×quality + β×consistency − γ×cost
    3. Recommend the temperature with the highest score

    Usage:
        optimizer = TemperatureOptimizer()
        result = optimizer.run_experiment(
            prompt_id="summarize",
            prompt_text="Summarize this article: ...",
            model="google/gemini-2.0-flash-001"
        )
        print(f"Best temp: {result.best_temperature}")
    """

    def __init__(self):
        self.temp_min = settings.temperature_min
        self.temp_max = settings.temperature_max
        self.temp_step = settings.temperature_step
        self.trials_per_step = settings.temperature_trials_per_step

    def run_experiment(
        self,
        prompt_id: str,
        prompt_text: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temp_min: Optional[float] = None,
        temp_max: Optional[float] = None,
        temp_step: Optional[float] = None,
        trials_per_step: Optional[int] = None,
    ) -> TemperatureExperimentResult:
        """
        Run a full temperature optimization experiment.

        Args:
            prompt_id: Identifier for the prompt being tested
            prompt_text: The actual prompt to send
            model: LLM model to test with
            system_prompt: Optional system message
            temp_min: Override minimum temperature
            temp_max: Override maximum temperature
            temp_step: Override temperature step size
            trials_per_step: Override number of trials per temperature

        Returns:
            TemperatureExperimentResult with best temperature and all data
        """
        from src.llm.client import LLMClient
        from src.evaluation.evaluator import ResponseEvaluator

        model = model or settings.openrouter_default_model
        t_min = temp_min or self.temp_min
        t_max = temp_max or self.temp_max
        t_step = temp_step or self.temp_step
        n_trials = trials_per_step or self.trials_per_step

        experiment_id = f"temp_exp_{uuid.uuid4().hex[:10]}"

        result = TemperatureExperimentResult(
            experiment_id=experiment_id,
            prompt_id=prompt_id,
            model=model,
            best_temperature=0.7,
            best_quality_score=0.0,
        )

        client = LLMClient()
        eval_judge = ResponseEvaluator()

        # Generate temperature values to test
        temperatures = []
        temp = t_min
        while temp <= t_max + 0.001:
            temperatures.append(round(temp, 2))
            temp += t_step

        logger.info(
            f"Starting temperature experiment {experiment_id}: "
            f"{len(temperatures)} temperatures × {n_trials} trials"
        )

        best_score = -1.0
        best_temp = 0.7

        for temperature in temperatures:
            trials: List[TemperatureTrialResult] = []

            for trial_num in range(n_trials):
                try:
                    # Make the LLM call
                    response = client.chat(
                        prompt=prompt_text,
                        model=model,
                        temperature=temperature,
                        system_prompt=system_prompt,
                    )

                    if not response.success:
                        trials.append(TemperatureTrialResult(
                            temperature=temperature,
                            quality_score=0.0,
                            latency_ms=response.latency_ms,
                            cost_usd=response.cost_usd,
                            output_length=0,
                            error=response.error,
                        ))
                        continue

                    # Evaluate the response
                    eval_score = eval_judge.evaluate(
                        original_prompt=prompt_text,
                        response=response.content,
                    )

                    trials.append(TemperatureTrialResult(
                        temperature=temperature,
                        quality_score=eval_score.composite_score,
                        latency_ms=response.latency_ms,
                        cost_usd=response.cost_usd + eval_score.judge_cost_usd,
                        output_length=len(response.content),
                        content=response.content[:200],  # Truncate for storage
                    ))

                except Exception as e:
                    logger.error(f"Trial failed at temp={temperature}: {e}")
                    trials.append(TemperatureTrialResult(
                        temperature=temperature,
                        quality_score=0.0,
                        latency_ms=0.0,
                        cost_usd=0.0,
                        output_length=0,
                        error=str(e),
                    ))

            # Aggregate results for this temperature
            successful_trials = [t for t in trials if t.error is None]
            if successful_trials:
                avg_quality = sum(t.quality_score for t in successful_trials) / len(successful_trials)
                avg_latency = sum(t.latency_ms for t in successful_trials) / len(successful_trials)
                total_cost = sum(t.cost_usd for t in trials)
                avg_length = sum(t.output_length for t in successful_trials) / len(successful_trials)

                # Consistency: lower std dev = more consistent
                if len(successful_trials) > 1:
                    quality_values = [t.quality_score for t in successful_trials]
                    mean_q = sum(quality_values) / len(quality_values)
                    variance = sum((q - mean_q) ** 2 for q in quality_values) / len(quality_values)
                    consistency = 1.0 - min(1.0, variance ** 0.5)  # 1.0 = perfectly consistent
                else:
                    consistency = 0.5

                temp_summary = {
                    "avg_quality": round(avg_quality, 4),
                    "avg_latency_ms": round(avg_latency, 1),
                    "total_cost_usd": round(total_cost, 6),
                    "avg_output_length": round(avg_length, 0),
                    "consistency": round(consistency, 4),
                    "successful_trials": len(successful_trials),
                    "failed_trials": len(trials) - len(successful_trials),
                }

                result.results_by_temp[temperature] = temp_summary
                result.total_cost_usd += total_cost
                result.total_trials += len(trials)

                # Composite score: quality × consistency (penalize inconsistent outputs)
                composite = avg_quality * (0.7 + 0.3 * consistency)
                if composite > best_score:
                    best_score = composite
                    best_temp = temperature

                logger.info(
                    f"  Temp {temperature:.1f}: quality={avg_quality:.3f}, "
                    f"consistency={consistency:.3f}, composite={composite:.3f}"
                )

        result.best_temperature = best_temp
        result.best_quality_score = best_score
        result.completed_at = datetime.utcnow()
        result.status = "completed"

        # Save to database
        self._save_experiment(result)

        logger.info(
            f"Experiment {experiment_id} complete: "
            f"best_temp={best_temp}, score={best_score:.3f}, "
            f"cost=${result.total_cost_usd:.4f}"
        )

        return result

    def _save_experiment(self, result: TemperatureExperimentResult):
        """Save experiment results to the database."""
        try:
            from src.database.models import TemperatureExperiment

            with db_manager.session_scope() as session:
                record = TemperatureExperiment(
                    experiment_id=result.experiment_id,
                    prompt_id=result.prompt_id,
                    model_name=result.model,
                    best_temperature=result.best_temperature,
                    best_quality_score=result.best_quality_score,
                    total_trials=result.total_trials,
                    total_cost_usd=result.total_cost_usd,
                    results_json=result.results_by_temp,
                    started_at=result.started_at,
                    completed_at=result.completed_at,
                    status=result.status,
                )
                session.add(record)

        except Exception as e:
            logger.error(f"Failed to save experiment: {e}")

    def get_recommended_temperature(
        self, prompt_id: str, model: Optional[str] = None
    ) -> Optional[float]:
        """
        Get the recommended temperature for a prompt based on past experiments.

        Returns None if no experiment has been run for this prompt.
        """
        try:
            from src.database.models import TemperatureExperiment

            with db_manager.session_scope() as session:
                query = session.query(TemperatureExperiment).filter(
                    TemperatureExperiment.prompt_id == prompt_id,
                    TemperatureExperiment.status == "completed",
                )
                if model:
                    query = query.filter(TemperatureExperiment.model_name == model)

                latest = query.order_by(
                    TemperatureExperiment.completed_at.desc()
                ).first()

                if latest:
                    return latest.best_temperature
                return None

        except Exception as e:
            logger.error(f"Failed to get recommended temperature: {e}")
            return None


# Global instance
temperature_optimizer = TemperatureOptimizer()
