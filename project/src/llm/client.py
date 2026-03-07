"""
LLM Client Module — Real API calls via OpenRouter

This module provides a unified client for making LLM API calls through
OpenRouter, which gives access to 200+ models through a single API.

Features:
- Automatic retry with exponential backoff
- Token counting and cost calculation
- Support for temperature control
- Structured response objects
- Timeout and error handling
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

from config import settings, get_model_cost


@dataclass
class LLMResponse:
    """Structured response from an LLM API call."""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: float
    cost_usd: float
    request_id: str
    temperature: float
    finish_reason: str = "stop"
    raw_response: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and len(self.content) > 0


class LLMClient:
    """
    Unified LLM client that routes through OpenRouter.

    OpenRouter provides access to models from OpenAI, Anthropic, Google,
    Meta, Mistral, etc. through a single OpenAI-compatible API.

    Usage:
        client = LLMClient()
        response = client.chat("Summarize this text...", model="openai/gpt-4o-mini")
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.default_model = settings.openrouter_default_model

        if not self.api_key:
            logger.warning(
                "No OpenRouter API key found. Set OPENROUTER_API_KEY in .env"
            )

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/prompt-ops",
                "X-Title": "PROMPT-OPS Telemetry System",
            },
            timeout=httpx.Timeout(60.0, connect=10.0),
        )

    def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LLMResponse:
        """
        Make an LLM API call through OpenRouter.

        Args:
            prompt: The user prompt text
            model: Model identifier (e.g., "openai/gpt-4o-mini")
            temperature: Sampling temperature (0.0 = deterministic, 1.5 = creative)
            max_tokens: Maximum tokens in the response
            system_prompt: Optional system message to set behavior
            messages: Optional pre-built messages list (overrides prompt/system_prompt)
            metadata: Optional extra metadata to attach

        Returns:
            LLMResponse with content, tokens, cost, latency
        """
        model = model or self.default_model
        request_id = f"llm_{uuid.uuid4().hex[:12]}"

        # Build messages
        if messages is None:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        start_time = time.time()

        try:
            response = self._call_api(payload)
            latency_ms = (time.time() - start_time) * 1000

            # Parse response
            choice = response.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "")
            finish_reason = choice.get("finish_reason", "stop")

            usage = response.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

            # Calculate cost
            cost_usd = get_model_cost(model, input_tokens, output_tokens)

            return LLMResponse(
                content=content,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
                request_id=request_id,
                temperature=temperature,
                finish_reason=finish_reason,
                raw_response=response,
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"LLM call failed [{request_id}]: {e}")
            return LLMResponse(
                content="",
                model=model,
                input_tokens=0,
                output_tokens=0,
                total_tokens=0,
                latency_ms=latency_ms,
                cost_usd=0.0,
                request_id=request_id,
                temperature=temperature,
                error=str(e),
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    def _call_api(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make the actual HTTP call with retries."""
        response = self._client.post("/chat/completions", json=payload)
        response.raise_for_status()
        return response.json()

    def list_available_models(self) -> List[Dict[str, Any]]:
        """Fetch available models from OpenRouter."""
        try:
            response = self._client.get("/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch models: {e}")
            return []

    def estimate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate cost for a call without making it."""
        return get_model_cost(model, input_tokens, output_tokens)

    def close(self):
        """Close the HTTP client."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


# Global client instance
llm_client = LLMClient()
