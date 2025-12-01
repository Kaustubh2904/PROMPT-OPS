"""
Telemetry Tracker Module

This is the core module that wraps LLM API calls and collects telemetry data.
It automatically tracks latency, tokens, costs, errors, and other metrics.
"""

import time
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps

from loguru import logger

from config import settings, get_model_cost
from src.database import db_manager, TelemetryLog


class TelemetryTracker:
    """
    Main telemetry tracking class.
    
    This class provides decorators and context managers to automatically
    track metrics for LLM API calls. It's designed to be non-intrusive
    and easy to integrate into existing code.
    """
    
    def __init__(self):
        """Initialize the telemetry tracker."""
        self.enabled = settings.enable_telemetry
        
    def generate_request_id(self) -> str:
        """Generate a unique request ID."""
        return f"req_{uuid.uuid4().hex[:16]}"
    
    @contextmanager
    def track_request(
        self,
        model_name: str,
        provider: str,
        prompt_text: str,
        prompt_id: Optional[str] = None,
        prompt_version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None
    ):
        """
        Context manager for tracking a single LLM request.
        
        Args:
            model_name: Name of the model being used
            provider: Provider name (openai, anthropic, etc.)
            prompt_text: The prompt being sent
            prompt_id: Optional prompt identifier for versioning
            prompt_version: Optional prompt version number
            metadata: Additional metadata to store
            tags: List of tags for categorization
            
        Yields:
            A context object for updating telemetry data
            
        Example:
            with tracker.track_request("gpt-4", "openai", prompt) as ctx:
                response = openai.ChatCompletion.create(...)
                ctx.set_response(response.choices[0].message.content)
                ctx.set_tokens(response.usage.prompt_tokens, 
                               response.usage.completion_tokens)
        """
        if not self.enabled:
            yield _DummyContext()
            return
        
        # Initialize telemetry record
        request_id = self.generate_request_id()
        start_time = time.time()
        
        telemetry_data = {
            "request_id": request_id,
            "timestamp": datetime.utcnow(),
            "model_name": model_name,
            "provider": provider,
            "prompt_text": prompt_text,
            "prompt_id": prompt_id,
            "prompt_version": prompt_version,
            "metadata": metadata or {},
            "tags": tags or [],
            "is_error": False,
        }
        
        # Create context for updating telemetry
        ctx = _TelemetryContext(telemetry_data)
        
        try:
            yield ctx
            
        except Exception as e:
            # Track error
            telemetry_data["is_error"] = True
            telemetry_data["error_type"] = type(e).__name__
            telemetry_data["error_message"] = str(e)
            logger.error(f"Error in tracked request {request_id}: {e}")
            raise
            
        finally:
            # Calculate latency
            end_time = time.time()
            telemetry_data["latency_ms"] = (end_time - start_time) * 1000
            
            # Calculate cost if tokens are available
            if "input_tokens" in telemetry_data and "output_tokens" in telemetry_data:
                cost = get_model_cost(
                    model_name,
                    telemetry_data["input_tokens"],
                    telemetry_data["output_tokens"]
                )
                telemetry_data["cost_usd"] = cost
                telemetry_data["total_tokens"] = (
                    telemetry_data["input_tokens"] + 
                    telemetry_data["output_tokens"]
                )
            
            # Save to database
            self._save_telemetry(telemetry_data)
    
    def _save_telemetry(self, data: Dict[str, Any]):
        """
        Save telemetry data to the database.
        
        Args:
            data: Dictionary containing telemetry data
        """
        try:
            with db_manager.session_scope() as session:
                log_entry = TelemetryLog(**data)
                session.add(log_entry)
                
            logger.debug(f"Saved telemetry for request {data['request_id']}")
            
        except Exception as e:
            logger.error(f"Failed to save telemetry: {e}")
    
    def track_openai_call(
        self,
        prompt_id: Optional[str] = None,
        prompt_version: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None
    ):
        """
        Decorator for tracking OpenAI API calls.
        
        Args:
            prompt_id: Optional prompt identifier
            prompt_version: Optional prompt version
            metadata: Additional metadata
            tags: List of tags
            
        Example:
            @tracker.track_openai_call(prompt_id="summarization_v1")
            def call_openai(prompt):
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}]
                )
                return response
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract prompt from args/kwargs (customize as needed)
                prompt = kwargs.get('prompt') or (args[0] if args else "")
                
                # Get model from kwargs or use default
                model = kwargs.get('model', 'gpt-3.5-turbo')
                
                with self.track_request(
                    model_name=model,
                    provider="openai",
                    prompt_text=str(prompt),
                    prompt_id=prompt_id,
                    prompt_version=prompt_version,
                    metadata=metadata,
                    tags=tags
                ) as ctx:
                    # Call the actual function
                    response = func(*args, **kwargs)
                    
                    # Extract metrics from OpenAI response
                    if hasattr(response, 'usage'):
                        ctx.set_tokens(
                            response.usage.prompt_tokens,
                            response.usage.completion_tokens
                        )
                    
                    if hasattr(response, 'choices') and response.choices:
                        content = response.choices[0].message.content
                        ctx.set_response(content)
                    
                    return response
                    
            return wrapper
        return decorator


class _TelemetryContext:
    """
    Context object for updating telemetry data during tracking.
    
    This class provides methods to update telemetry information
    as the request progresses.
    """
    
    def __init__(self, data: Dict[str, Any]):
        """Initialize with telemetry data dictionary."""
        self.data = data
    
    def set_tokens(self, input_tokens: int, output_tokens: int):
        """Set token usage."""
        self.data["input_tokens"] = input_tokens
        self.data["output_tokens"] = output_tokens
    
    def set_response(self, response_text: str):
        """Set response text."""
        self.data["response_text"] = response_text
        self.data["response_length"] = len(response_text)
    
    def set_quality_score(self, score: float):
        """Set quality score (0-1)."""
        self.data["quality_score"] = max(0.0, min(1.0, score))
    
    def set_user_feedback(self, feedback: str):
        """Set user feedback (positive, negative, neutral)."""
        self.data["user_feedback"] = feedback
    
    def add_metadata(self, key: str, value: Any):
        """Add metadata field."""
        self.data["metadata"][key] = value
    
    def add_tag(self, tag: str):
        """Add a tag."""
        if tag not in self.data["tags"]:
            self.data["tags"].append(tag)


class _DummyContext:
    """Dummy context when telemetry is disabled."""
    
    def set_tokens(self, *args, **kwargs):
        pass
    
    def set_response(self, *args, **kwargs):
        pass
    
    def set_quality_score(self, *args, **kwargs):
        pass
    
    def set_user_feedback(self, *args, **kwargs):
        pass
    
    def add_metadata(self, *args, **kwargs):
        pass
    
    def add_tag(self, *args, **kwargs):
        pass


# Global tracker instance
tracker = TelemetryTracker()
