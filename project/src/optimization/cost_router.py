"""
Cost-Aware Model Router

Routes LLM requests to the cheapest model that still meets quality
thresholds. Implements an intelligent cascade:

1. Try the cheapest model first
2. Evaluate response quality
3. If quality is below threshold, escalate to a better model
4. Learn over time which prompts work well on cheap models

This saves significant costs by avoiding expensive models for
simple requests while preserving quality for complex ones.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from loguru import logger

from config import settings, MODEL_TIERS, MODEL_PRICING
from src.database import db_manager


@dataclass
class RoutingDecision:
    """Record of a cost-routing decision."""
    routing_id: str
    prompt_id: Optional[str]
    original_model: str
    routed_model: str
    tier_used: str
    quality_score: float
    escalated: bool
    escalation_reason: Optional[str]
    cost_saved_usd: float
    latency_ms: float
    content: str = ""


class CostAwareRouter:
    """
    Intelligently routes requests to minimize cost while maintaining quality.

    Strategy:
    - Maintain a quality history per prompt_id per model tier
    - For known prompts: route to cheapest tier that historically meets quality
    - For unknown prompts: start at cheapest, escalate if quality is low
    - Track savings achieved by routing

    Usage:
        router = CostAwareRouter()
        response = router.route_request(
            prompt="Summarize this text...",
            prompt_id="summarize",
            preferred_model="openai/gpt-4o",  # expensive!
        )
        # May use a cheaper model if quality is sufficient
    """

    def __init__(self):
        self.enabled = settings.cost_routing_enabled
        self.quality_threshold = settings.quality_threshold_for_downgrade
        # Cache of prompt_id → best known cheap tier
        self._quality_cache: Dict[str, Dict[str, float]] = {}

    def route_request(
        self,
        prompt: str,
        prompt_id: Optional[str] = None,
        preferred_model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        min_quality: Optional[float] = None,
    ) -> RoutingDecision:
        """
        Route a request to the optimal model for cost/quality.

        Args:
            prompt: The prompt text
            prompt_id: Prompt identifier (used for learning routing patterns)
            preferred_model: The model the user would normally use
            system_prompt: Optional system prompt
            temperature: Temperature to use
            min_quality: Minimum quality threshold (overrides config)

        Returns:
            RoutingDecision with the response and routing details
        """
        from src.llm.client import LLMClient
        from src.evaluation.evaluator import ResponseEvaluator

        preferred_model = preferred_model or settings.openrouter_default_model
        quality_threshold = min_quality or self.quality_threshold
        routing_id = f"route_{uuid.uuid4().hex[:10]}"

        if not self.enabled:
            # Routing disabled — use preferred model directly
            return self._call_model(
                routing_id=routing_id,
                prompt=prompt,
                prompt_id=prompt_id,
                model=preferred_model,
                system_prompt=system_prompt,
                temperature=temperature,
                original_model=preferred_model,
                tier="direct",
                escalated=False,
            )

        # Determine which tiers to try (cheapest first)
        tiers_to_try = self._get_tiers_to_try(prompt_id, preferred_model)

        client = LLMClient()
        eval_judge = ResponseEvaluator()

        for tier_name, models in tiers_to_try:
            model = models[0] if models else preferred_model

            try:
                response = client.chat(
                    prompt=prompt,
                    model=model,
                    temperature=temperature,
                    system_prompt=system_prompt,
                )

                if not response.success:
                    logger.warning(f"Tier {tier_name} ({model}) failed, escalating")
                    continue

                # Evaluate quality
                eval_score = eval_judge.evaluate(
                    original_prompt=prompt,
                    response=response.content,
                )

                quality = eval_score.composite_score

                # Update quality cache
                self._update_cache(prompt_id, tier_name, quality)

                if quality >= quality_threshold:
                    # Quality is good enough — use this cheaper model!
                    original_cost = self._estimate_cost(
                        preferred_model, response.input_tokens, response.output_tokens
                    )
                    actual_cost = response.cost_usd
                    cost_saved = max(0, original_cost - actual_cost)

                    decision = RoutingDecision(
                        routing_id=routing_id,
                        prompt_id=prompt_id,
                        original_model=preferred_model,
                        routed_model=model,
                        tier_used=tier_name,
                        quality_score=quality,
                        escalated=False,
                        escalation_reason=None,
                        cost_saved_usd=cost_saved,
                        latency_ms=response.latency_ms,
                        content=response.content,
                    )
                    self._save_routing_decision(decision)

                    logger.info(
                        f"Routed to {tier_name} ({model}): "
                        f"quality={quality:.2f}, saved=${cost_saved:.4f}"
                    )
                    return decision

                else:
                    logger.info(
                        f"Tier {tier_name} quality too low ({quality:.2f} < {quality_threshold}), "
                        f"escalating..."
                    )

            except Exception as e:
                logger.warning(f"Tier {tier_name} error: {e}, escalating")
                continue

        # All tiers failed or quality too low — use preferred model
        logger.info(f"Escalating to preferred model: {preferred_model}")
        return self._call_model(
            routing_id=routing_id,
            prompt=prompt,
            prompt_id=prompt_id,
            model=preferred_model,
            system_prompt=system_prompt,
            temperature=temperature,
            original_model=preferred_model,
            tier="premium_fallback",
            escalated=True,
            escalation_reason="All cheaper tiers below quality threshold",
        )

    def _get_tiers_to_try(
        self, prompt_id: Optional[str], preferred_model: str
    ) -> List[tuple]:
        """
        Determine which model tiers to try, cheapest first.

        If we have quality history for this prompt_id, skip tiers
        that we know won't meet quality threshold.
        """
        tier_order = ["tier_1", "tier_2", "tier_3", "tier_4"]
        tiers = []

        for tier_name in tier_order:
            models = MODEL_TIERS.get(tier_name, [])
            if not models:
                continue

            # Check if we have cached quality data
            if prompt_id and prompt_id in self._quality_cache:
                cached_quality = self._quality_cache[prompt_id].get(tier_name)
                if cached_quality is not None and cached_quality < self.quality_threshold * 0.8:
                    # Skip this tier — historically too low quality
                    logger.debug(f"Skipping tier {tier_name} for {prompt_id} (cached quality: {cached_quality:.2f})")
                    continue

            tiers.append((tier_name, models))

        return tiers

    def _update_cache(self, prompt_id: Optional[str], tier: str, quality: float):
        """Update the quality cache with new data."""
        if not prompt_id:
            return
        if prompt_id not in self._quality_cache:
            self._quality_cache[prompt_id] = {}
        # Exponential moving average
        old = self._quality_cache[prompt_id].get(tier)
        if old is not None:
            self._quality_cache[prompt_id][tier] = 0.7 * old + 0.3 * quality
        else:
            self._quality_cache[prompt_id][tier] = quality

    def _call_model(
        self,
        routing_id: str,
        prompt: str,
        prompt_id: Optional[str],
        model: str,
        system_prompt: Optional[str],
        temperature: float,
        original_model: str,
        tier: str,
        escalated: bool,
        escalation_reason: Optional[str] = None,
    ) -> RoutingDecision:
        """Make a direct call to a specific model."""
        from src.llm.client import LLMClient

        client = LLMClient()
        response = client.chat(
            prompt=prompt,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
        )

        decision = RoutingDecision(
            routing_id=routing_id,
            prompt_id=prompt_id,
            original_model=original_model,
            routed_model=model,
            tier_used=tier,
            quality_score=0.0,  # Not evaluated for direct calls
            escalated=escalated,
            escalation_reason=escalation_reason,
            cost_saved_usd=0.0,
            latency_ms=response.latency_ms,
            content=response.content if response.success else "",
        )
        self._save_routing_decision(decision)
        return decision

    def _estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate what a call WOULD cost on a different model."""
        pricing = MODEL_PRICING.get(model, {"input": 0.001, "output": 0.002})
        return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]

    def _save_routing_decision(self, decision: RoutingDecision):
        """Save routing decision to database."""
        try:
            from src.database.models import CostRoutingLog

            with db_manager.session_scope() as session:
                record = CostRoutingLog(
                    routing_id=decision.routing_id,
                    prompt_id=decision.prompt_id,
                    original_model=decision.original_model,
                    routed_model=decision.routed_model,
                    tier_used=decision.tier_used,
                    quality_score=decision.quality_score,
                    escalated=decision.escalated,
                    escalation_reason=decision.escalation_reason,
                    cost_saved_usd=decision.cost_saved_usd,
                    latency_ms=decision.latency_ms,
                )
                session.add(record)

        except Exception as e:
            logger.error(f"Failed to save routing decision: {e}")

    def get_routing_stats(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get cost routing statistics."""
        try:
            from src.database.models import CostRoutingLog

            cutoff = datetime.utcnow() - timedelta(hours=hours_back)

            with db_manager.session_scope() as session:
                records = session.query(CostRoutingLog).filter(
                    CostRoutingLog.created_at >= cutoff
                ).all()

                if not records:
                    return {"total_requests": 0, "total_saved": 0.0}

                total = len(records)
                downgraded = sum(1 for r in records if not r.escalated)
                escalated = sum(1 for r in records if r.escalated)
                total_saved = sum(r.cost_saved_usd for r in records if r.cost_saved_usd)
                avg_quality = sum(r.quality_score for r in records) / total

                return {
                    "total_requests": total,
                    "downgraded_count": downgraded,
                    "escalated_count": escalated,
                    "downgrade_rate": downgraded / total,
                    "total_saved_usd": round(total_saved, 4),
                    "avg_quality": round(avg_quality, 3),
                }

        except Exception as e:
            logger.error(f"Failed to get routing stats: {e}")
            return {"total_requests": 0, "total_saved": 0.0, "error": str(e)}


# Global instance
cost_router = CostAwareRouter()
