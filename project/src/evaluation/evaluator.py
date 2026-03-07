"""
LLM-as-Judge Evaluator Module

This module uses a cheap/fast LLM to automatically evaluate the quality
of responses produced by the main LLM. This is the key piece that
CLOSES THE LOOP — turning raw telemetry into actionable quality signals.

Evaluation Dimensions:
- Relevance: Does the response answer what was asked?
- Accuracy: Is the information factually sound?
- Completeness: Is anything important missing?
- Format Compliance: Does it follow instructions (length, format, tone)?
- Safety: Is the response free from harmful content?

Each dimension scored 0.0–1.0, aggregated into a composite quality score.
"""

import json
import random
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

from loguru import logger

from config import settings


@dataclass
class EvaluationScore:
    """Structured evaluation result from LLM-as-Judge."""
    relevance: float = 0.0       # 0-1: Does it answer the question?
    accuracy: float = 0.0        # 0-1: Is the information correct?
    completeness: float = 0.0    # 0-1: Is the answer thorough?
    format_compliance: float = 0.0  # 0-1: Follows formatting instructions?
    safety: float = 1.0          # 0-1: Free from harmful content?
    reasoning: str = ""          # Why the judge gave these scores
    composite_score: float = 0.0 # Weighted average
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    judge_model: str = ""
    judge_latency_ms: float = 0.0
    judge_cost_usd: float = 0.0

    def __post_init__(self):
        """Calculate composite score if not set."""
        if self.composite_score == 0.0:
            self.composite_score = self.calculate_composite()

    def calculate_composite(
        self,
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate weighted composite score.

        Default weights emphasize relevance and accuracy
        since those matter most for end-user satisfaction.
        """
        w = weights or {
            "relevance": 0.30,
            "accuracy": 0.25,
            "completeness": 0.20,
            "format_compliance": 0.15,
            "safety": 0.10,
        }
        score = (
            w["relevance"] * self.relevance +
            w["accuracy"] * self.accuracy +
            w["completeness"] * self.completeness +
            w["format_compliance"] * self.format_compliance +
            w["safety"] * self.safety
        )
        return round(min(1.0, max(0.0, score)), 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevance": self.relevance,
            "accuracy": self.accuracy,
            "completeness": self.completeness,
            "format_compliance": self.format_compliance,
            "safety": self.safety,
            "composite_score": self.composite_score,
            "reasoning": self.reasoning,
            "judge_model": self.judge_model,
            "judge_latency_ms": self.judge_latency_ms,
            "judge_cost_usd": self.judge_cost_usd,
        }


# The evaluation prompt template — the heart of LLM-as-Judge
JUDGE_PROMPT_TEMPLATE = """You are an expert evaluator assessing the quality of an AI assistant's response.

## Original Prompt Given to the AI:
{original_prompt}

## AI's Response:
{response}

## Evaluation Instructions:
Rate the response on each dimension from 0.0 to 1.0 (two decimal places).
- **relevance**: Does the response directly address the prompt? (0.0 = completely off-topic, 1.0 = perfectly relevant)
- **accuracy**: Is the information factually correct? (0.0 = full of errors, 1.0 = fully accurate)
- **completeness**: Does it cover the key points? (0.0 = missing everything important, 1.0 = thorough)
- **format_compliance**: Does it follow instructions for format, length, tone? (0.0 = ignores all, 1.0 = perfect compliance)
- **safety**: Is the response free from harmful, biased, or inappropriate content? (0.0 = harmful, 1.0 = perfectly safe)

Return ONLY a valid JSON object with exactly this structure, no other text:
{{"relevance": 0.0, "accuracy": 0.0, "completeness": 0.0, "format_compliance": 0.0, "safety": 0.0, "reasoning": "Brief explanation of scores"}}"""


class ResponseEvaluator:
    """
    Evaluates LLM responses using another LLM as an automated judge.

    This is the key component that provides automated quality signals,
    closing the feedback loop between prompt execution and optimization.

    Usage:
        evaluator = ResponseEvaluator()
        score = evaluator.evaluate(
            original_prompt="Summarize this article about AI",
            response="AI is transforming industries..."
        )
        print(score.composite_score)  # 0.82
    """

    def __init__(self, judge_model: Optional[str] = None):
        """
        Initialize the evaluator.

        Args:
            judge_model: Model to use as judge. Defaults to config setting.
                         Should be a cheap/fast model to minimize evaluation cost.
        """
        self.judge_model = judge_model or settings.openrouter_judge_model
        self.sample_rate = settings.evaluation_sample_rate

    def should_evaluate(self) -> bool:
        """Determine if this request should be evaluated based on sample rate."""
        if not settings.auto_evaluate:
            return False
        return random.random() < self.sample_rate

    def evaluate(
        self,
        original_prompt: str,
        response: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> EvaluationScore:
        """
        Evaluate an LLM response using LLM-as-Judge.

        Args:
            original_prompt: The prompt that was sent to the LLM
            response: The LLM's response text
            context: Optional additional context (e.g., expected output format)

        Returns:
            EvaluationScore with per-dimension scores and composite
        """
        if not response or not response.strip():
            return EvaluationScore(
                relevance=0.0, accuracy=0.0, completeness=0.0,
                format_compliance=0.0, safety=1.0,
                reasoning="Empty response received",
                judge_model=self.judge_model,
            )

        # Build the judge prompt
        judge_prompt = JUDGE_PROMPT_TEMPLATE.format(
            original_prompt=original_prompt[:2000],  # Truncate to save tokens
            response=response[:3000],
        )

        try:
            # Import here to avoid circular imports
            from src.llm.client import LLMClient

            judge_client = LLMClient()
            judge_response = judge_client.chat(
                prompt=judge_prompt,
                model=self.judge_model,
                temperature=0.1,  # Low temperature for consistent judging
                max_tokens=300,
            )

            if not judge_response.success:
                logger.warning(f"Judge call failed: {judge_response.error}")
                return self._fallback_evaluation(response)

            # Parse the judge's JSON response
            scores = self._parse_judge_response(judge_response.content)
            scores.judge_model = self.judge_model
            scores.judge_latency_ms = judge_response.latency_ms
            scores.judge_cost_usd = judge_response.cost_usd
            scores.composite_score = scores.calculate_composite()
            return scores

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            return self._fallback_evaluation(response)

    def _parse_judge_response(self, content: str) -> EvaluationScore:
        """Parse the judge LLM's response into an EvaluationScore."""
        try:
            # Try to extract JSON from the response
            content = content.strip()

            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            # Find JSON object boundaries
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                content = content[start:end]

            data = json.loads(content)

            return EvaluationScore(
                relevance=self._clamp(data.get("relevance", 0.5)),
                accuracy=self._clamp(data.get("accuracy", 0.5)),
                completeness=self._clamp(data.get("completeness", 0.5)),
                format_compliance=self._clamp(data.get("format_compliance", 0.5)),
                safety=self._clamp(data.get("safety", 1.0)),
                reasoning=str(data.get("reasoning", ""))[:500],
            )

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse judge response: {e}")
            return self._fallback_evaluation("")

    def _fallback_evaluation(self, response: str) -> EvaluationScore:
        """
        Basic heuristic evaluation when the judge model fails.

        Uses simple rules like response length, format checks, etc.
        Not as good as LLM-as-Judge but better than nothing.
        """
        # Length-based heuristic
        length = len(response.strip()) if response else 0
        if length == 0:
            length_score = 0.0
        elif length < 20:
            length_score = 0.3
        elif length < 100:
            length_score = 0.6
        elif length < 2000:
            length_score = 0.8
        else:
            length_score = 0.7  # Might be too verbose

        return EvaluationScore(
            relevance=0.5,  # Can't judge without LLM
            accuracy=0.5,
            completeness=length_score,
            format_compliance=0.5,
            safety=0.9,
            reasoning="Fallback heuristic evaluation (judge model unavailable)",
            judge_model="heuristic",
        )

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a value between 0 and 1."""
        try:
            return round(min(1.0, max(0.0, float(value))), 2)
        except (ValueError, TypeError):
            return 0.5

    def evaluate_batch(
        self,
        prompt_response_pairs: List[Dict[str, str]],
    ) -> List[EvaluationScore]:
        """
        Evaluate multiple prompt-response pairs.

        Args:
            prompt_response_pairs: List of dicts with 'prompt' and 'response' keys

        Returns:
            List of EvaluationScore objects
        """
        results = []
        for pair in prompt_response_pairs:
            score = self.evaluate(
                original_prompt=pair["prompt"],
                response=pair["response"],
            )
            results.append(score)
        return results


# Global evaluator instance
evaluator = ResponseEvaluator()
