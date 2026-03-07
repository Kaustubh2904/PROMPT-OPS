"""
Pipeline Orchestrator — The Closed-Loop Engine

This is the MAIN ENTRY POINT for the entire PROMPT-OPS system.
It connects every component into a single, clean pipeline:

    Prompt Selection → LLM Call → Telemetry Recording → Quality Evaluation
         ↑                                                     │
         │                                                     ▼
    Prompt Promotion ← Optimization Decision ← Feedback Analysis

One function call does EVERYTHING:
    response = pipeline.run("Summarize this article", prompt_id="summarize")

Behind the scenes it:
1. Selects the best prompt version (A/B testing)
2. Uses the optimal temperature (from experiments)
3. Optionally routes to a cheaper model (cost optimization)
4. Makes the actual LLM API call
5. Records full telemetry
6. Auto-evaluates response quality (LLM-as-Judge)
7. Stores evaluation results
8. Updates prompt version metrics
9. Triggers optimization if enough data is collected
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from loguru import logger

from config import settings
from src.database import db_manager, TelemetryLog, EvaluationResult


@dataclass
class PipelineResponse:
    """Complete response from the closed-loop pipeline."""
    # User-facing
    content: str
    success: bool

    # Identifiers
    request_id: str
    prompt_id: Optional[str] = None
    prompt_version: Optional[int] = None

    # Model info
    model: str = ""
    temperature: float = 0.7

    # Performance
    latency_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    # Quality (from LLM-as-Judge)
    quality_score: Optional[float] = None
    evaluation_details: Optional[Dict[str, Any]] = None

    # Cost routing
    was_cost_routed: bool = False
    original_model: Optional[str] = None
    cost_saved_usd: float = 0.0

    # Error
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content[:200] + "..." if len(self.content) > 200 else self.content,
            "success": self.success,
            "request_id": self.request_id,
            "prompt_id": self.prompt_id,
            "prompt_version": self.prompt_version,
            "model": self.model,
            "temperature": self.temperature,
            "latency_ms": round(self.latency_ms, 1),
            "tokens": self.input_tokens + self.output_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "quality_score": self.quality_score,
            "was_cost_routed": self.was_cost_routed,
            "cost_saved_usd": round(self.cost_saved_usd, 6),
        }


class PromptOpsPipeline:
    """
    The main closed-loop pipeline that orchestrates all components.

    This is the interface you show to recruiters/professors — one clean
    function that demonstrates the entire system working together.

    Usage:
        from src.pipeline import pipeline

        # Simple call
        response = pipeline.run("Explain quantum computing simply")

        # With prompt versioning + A/B testing
        response = pipeline.run(
            "Summarize this article: ...",
            prompt_id="summarize",
            model="google/gemini-2.0-flash-001"
        )

        # With cost-aware routing
        response = pipeline.run(
            "What is 2+2?",
            prompt_id="math",
            model="openai/gpt-4o",  # Expensive model
            enable_cost_routing=True,  # May route to cheaper model
        )
    """

    def __init__(self):
        self._initialized = False

    def _ensure_init(self):
        """Lazy initialization to avoid import issues."""
        if self._initialized:
            return
        from src.llm.client import LLMClient
        from src.evaluation.evaluator import ResponseEvaluator
        from src.telemetry.tracker import TelemetryTracker
        from src.optimization.optimizer import PromptManager, PromptOptimizer
        from src.optimization.temperature_optimizer import TemperatureOptimizer
        from src.optimization.cost_router import CostAwareRouter

        self.llm_client = LLMClient()
        self.evaluator = ResponseEvaluator()
        self.tracker = TelemetryTracker()
        self.prompt_manager = PromptManager()
        self.prompt_optimizer = PromptOptimizer()
        self.temp_optimizer = TemperatureOptimizer()
        self.cost_router = CostAwareRouter()
        self._initialized = True

    def run(
        self,
        user_input: str,
        prompt_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        enable_cost_routing: bool = False,
        enable_evaluation: bool = True,
        ab_testing: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> PipelineResponse:
        """
        Execute the full closed-loop pipeline.

        Args:
            user_input: The user's raw input text
            prompt_id: If set, uses versioned prompt template
            model: LLM model to use
            temperature: Override temperature (None = use optimal from experiments)
            system_prompt: Override system prompt
            max_tokens: Maximum response tokens
            enable_cost_routing: Try cheaper models first?
            enable_evaluation: Run LLM-as-Judge on the response?
            ab_testing: Use A/B test traffic splitting?
            metadata: Extra metadata to store
            tags: Tags for categorization

        Returns:
            PipelineResponse with content, metrics, and quality score
        """
        self._ensure_init()

        request_id = f"pipe_{uuid.uuid4().hex[:12]}"
        model = model or settings.openrouter_default_model
        start_time = time.time()

        # ── Step 1: Prompt Selection ──────────────────────────────
        prompt_text = user_input
        prompt_version_num = None
        selected_version = None

        if prompt_id:
            selected_version = self.prompt_manager.get_prompt_for_request(
                prompt_id, ab_testing=ab_testing
            )
            if selected_version:
                prompt_version_num = selected_version.version
                # Replace {input} or {text} placeholder with user input
                template = selected_version.template
                if "{input}" in template:
                    prompt_text = template.replace("{input}", user_input)
                elif "{text}" in template:
                    prompt_text = template.replace("{text}", user_input)
                else:
                    prompt_text = template + "\n\n" + user_input

                logger.debug(
                    f"Using prompt {prompt_id} v{prompt_version_num}"
                )

        # ── Step 2: Temperature Selection ─────────────────────────
        if temperature is None:
            # Check if we have an optimal temperature from experiments
            optimal_temp = self.temp_optimizer.get_recommended_temperature(
                prompt_id or "default", model
            )
            temperature = optimal_temp if optimal_temp is not None else 0.7

        # ── Step 3: LLM Call (with optional cost routing) ─────────
        response_content = ""
        was_cost_routed = False
        original_model = model
        cost_saved = 0.0
        llm_response = None

        try:
            if enable_cost_routing and settings.cost_routing_enabled:
                routing = self.cost_router.route_request(
                    prompt=prompt_text,
                    prompt_id=prompt_id,
                    preferred_model=model,
                    system_prompt=system_prompt,
                    temperature=temperature,
                )
                response_content = routing.content
                was_cost_routed = routing.routed_model != routing.original_model
                original_model = routing.original_model
                model = routing.routed_model
                cost_saved = routing.cost_saved_usd

                # Create a pseudo-LLMResponse for telemetry
                from src.llm.client import LLMResponse
                llm_response = LLMResponse(
                    content=response_content,
                    model=model,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    latency_ms=routing.latency_ms,
                    cost_usd=0.0,
                    request_id=request_id,
                    temperature=temperature,
                )
            else:
                llm_response = self.llm_client.chat(
                    prompt=prompt_text,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt,
                    max_tokens=max_tokens,
                )
                response_content = llm_response.content

        except Exception as e:
            logger.error(f"Pipeline LLM call failed: {e}")
            total_latency = (time.time() - start_time) * 1000
            return PipelineResponse(
                content="",
                success=False,
                request_id=request_id,
                prompt_id=prompt_id,
                prompt_version=prompt_version_num,
                model=model,
                temperature=temperature,
                latency_ms=total_latency,
                error=str(e),
            )

        # ── Step 4: Telemetry Recording ──────────────────────────
        total_latency = (time.time() - start_time) * 1000

        telemetry_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow(),
            "model_name": model,
            "provider": "openrouter",
            "prompt_text": prompt_text[:5000],
            "prompt_id": prompt_id,
            "prompt_version": prompt_version_num,
            "input_tokens": llm_response.input_tokens if llm_response else 0,
            "output_tokens": llm_response.output_tokens if llm_response else 0,
            "total_tokens": llm_response.total_tokens if llm_response else 0,
            "latency_ms": llm_response.latency_ms if llm_response else total_latency,
            "cost_usd": llm_response.cost_usd if llm_response else 0.0,
            "response_text": response_content[:5000],
            "response_length": len(response_content),
            "is_error": not llm_response.success if llm_response else True,
            "error_message": llm_response.error if llm_response else None,
            "extra_metadata": {
                **(metadata or {}),
                "temperature": temperature,
                "was_cost_routed": was_cost_routed,
                "original_model": original_model,
                "cost_saved_usd": cost_saved,
            },
            "tags": tags or [],
        }

        self._save_telemetry(telemetry_data)

        # ── Step 5: Auto-Evaluation (LLM-as-Judge) ──────────────
        quality_score = None
        evaluation_details = None

        if (
            enable_evaluation
            and settings.auto_evaluate
            and response_content
            and self.evaluator.should_evaluate()
        ):
            try:
                eval_score = self.evaluator.evaluate(
                    original_prompt=prompt_text,
                    response=response_content,
                )
                quality_score = eval_score.composite_score
                evaluation_details = eval_score.to_dict()

                # Save evaluation to DB
                self._save_evaluation(
                    request_id=request_id,
                    prompt_id=prompt_id,
                    prompt_version=prompt_version_num,
                    model_name=model,
                    eval_score=eval_score,
                )

                # Update telemetry with quality score
                self._update_telemetry_quality(request_id, quality_score)

                logger.debug(
                    f"Evaluation: quality={quality_score:.3f} "
                    f"(relevance={eval_score.relevance}, accuracy={eval_score.accuracy})"
                )

            except Exception as e:
                logger.warning(f"Evaluation failed: {e}")

        # ── Step 6: Update Prompt Metrics ─────────────────────────
        if prompt_id and prompt_version_num:
            try:
                self.prompt_manager.update_prompt_metrics(prompt_id, prompt_version_num)
            except Exception as e:
                logger.warning(f"Failed to update prompt metrics: {e}")

        # ── Build Response ────────────────────────────────────────
        return PipelineResponse(
            content=response_content,
            success=bool(response_content),
            request_id=request_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version_num,
            model=model,
            temperature=temperature,
            latency_ms=total_latency,
            input_tokens=llm_response.input_tokens if llm_response else 0,
            output_tokens=llm_response.output_tokens if llm_response else 0,
            cost_usd=llm_response.cost_usd if llm_response else 0.0,
            quality_score=quality_score,
            evaluation_details=evaluation_details,
            was_cost_routed=was_cost_routed,
            original_model=original_model if was_cost_routed else None,
            cost_saved_usd=cost_saved,
        )

    def _save_telemetry(self, data: Dict[str, Any]):
        """Save telemetry record."""
        try:
            with db_manager.session_scope() as session:
                log_entry = TelemetryLog(**data)
                session.add(log_entry)
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")

    def _save_evaluation(self, request_id, prompt_id, prompt_version, model_name, eval_score):
        """Save evaluation result."""
        try:
            with db_manager.session_scope() as session:
                record = EvaluationResult(
                    request_id=request_id,
                    prompt_id=prompt_id,
                    prompt_version=prompt_version,
                    model_name=model_name,
                    relevance=eval_score.relevance,
                    accuracy=eval_score.accuracy,
                    completeness=eval_score.completeness,
                    format_compliance=eval_score.format_compliance,
                    safety=eval_score.safety,
                    composite_score=eval_score.composite_score,
                    reasoning=eval_score.reasoning,
                    judge_model=eval_score.judge_model,
                    judge_latency_ms=eval_score.judge_latency_ms,
                    judge_cost_usd=eval_score.judge_cost_usd,
                )
                session.add(record)
        except Exception as e:
            logger.error(f"Failed to save evaluation: {e}")

    def _update_telemetry_quality(self, request_id: str, quality_score: float):
        """Update the telemetry record with quality score after evaluation."""
        try:
            with db_manager.session_scope() as session:
                log = session.query(TelemetryLog).filter(
                    TelemetryLog.request_id == request_id
                ).first()
                if log:
                    log.quality_score = quality_score
        except Exception as e:
            logger.error(f"Failed to update quality score: {e}")

    def run_batch(
        self,
        inputs: List[Dict[str, Any]],
        **kwargs
    ) -> List[PipelineResponse]:
        """
        Run pipeline on multiple inputs.

        Args:
            inputs: List of dicts with 'user_input' and optional overrides
            **kwargs: Default parameters for all calls

        Returns:
            List of PipelineResponse objects
        """
        results = []
        for item in inputs:
            call_kwargs = {**kwargs}
            call_kwargs.update(item)
            user_input = call_kwargs.pop("user_input")
            response = self.run(user_input, **call_kwargs)
            results.append(response)
        return results


# Global pipeline instance
pipeline = PromptOpsPipeline()
