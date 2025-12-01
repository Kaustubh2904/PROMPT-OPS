"""
Example: Integrating Telemetry with OpenAI

This example shows how to integrate the telemetry system
with actual OpenAI API calls.
"""

import os
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

from src.telemetry import tracker
from src.database import init_database

# Initialize
init_database()
openai.api_key = os.getenv("OPENAI_API_KEY")


def example_1_basic_tracking():
    """
    Example 1: Basic telemetry tracking with context manager
    """
    print("Example 1: Basic Tracking")
    print("-" * 40)
    
    prompt = "Explain what machine learning is in one sentence."
    
    # Use the telemetry tracker
    with tracker.track_request(
        model_name="gpt-3.5-turbo",
        provider="openai",
        prompt_text=prompt,
        tags=["example", "ml_explanation"]
    ) as ctx:
        # Make the actual API call
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Extract and set metrics
        ctx.set_tokens(
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )
        
        answer = response.choices[0].message.content
        ctx.set_response(answer)
        
        # Optional: Add quality score if you have a scoring mechanism
        ctx.set_quality_score(0.9)
        
        print(f"Response: {answer}")
        print("✓ Telemetry recorded")


def example_2_with_prompt_versioning():
    """
    Example 2: Using prompt versioning and A/B testing
    """
    print("\nExample 2: Prompt Versioning")
    print("-" * 40)
    
    from src.optimization import prompt_manager
    
    # Create prompt versions (do this once)
    try:
        prompt_manager.create_prompt_version(
            prompt_id="translation",
            template="Translate the following to French: {text}",
            name="Basic Translation",
            is_default=True
        )
    except:
        pass  # Already exists
    
    # Get prompt for this request (handles A/B testing automatically)
    prompt_version = prompt_manager.get_prompt_for_request("translation")
    
    text_to_translate = "Hello, how are you?"
    prompt_text = prompt_version.template.format(text=text_to_translate)
    
    with tracker.track_request(
        model_name="gpt-3.5-turbo",
        provider="openai",
        prompt_text=prompt_text,
        prompt_id=prompt_version.prompt_id,
        prompt_version=prompt_version.version
    ) as ctx:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt_text}]
        )
        
        ctx.set_tokens(
            response.usage.prompt_tokens,
            response.usage.completion_tokens
        )
        
        answer = response.choices[0].message.content
        ctx.set_response(answer)
        
        print(f"Translation: {answer}")
        print("✓ Telemetry with prompt version recorded")


def example_3_decorator_style():
    """
    Example 3: Using the decorator for cleaner code
    """
    print("\nExample 3: Decorator Style")
    print("-" * 40)
    
    @tracker.track_openai_call(
        prompt_id="summarization",
        tags=["example", "decorator"]
    )
    def summarize_text(prompt, model="gpt-3.5-turbo"):
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response
    
    prompt = "Summarize: The Earth orbits the Sun, taking approximately 365.25 days."
    response = summarize_text(prompt)
    
    print(f"Summary: {response.choices[0].message.content}")
    print("✓ Automatic telemetry with decorator")


def example_4_monitoring_and_optimization():
    """
    Example 4: Checking monitoring data and running optimization
    """
    print("\nExample 4: Monitoring & Optimization")
    print("-" * 40)
    
    from src.monitoring import monitor
    from src.optimization import prompt_optimizer, OptimizationGoal
    
    # Get model statistics
    stats = monitor.get_model_stats("gpt-3.5-turbo", time_window_hours=24)
    
    if stats.get("total_requests", 0) > 0:
        print(f"Model: gpt-3.5-turbo")
        print(f"  Total Requests: {stats['total_requests']}")
        print(f"  Avg Latency: {stats.get('avg_latency_ms', 0):.0f}ms")
        print(f"  Success Rate: {stats.get('success_rate', 0):.1%}")
        print(f"  Total Cost: ${stats.get('total_cost_usd', 0):.4f}")
    else:
        print("No data available yet")
    
    # Check for active alerts
    alerts = monitor.get_active_alerts()
    if alerts:
        print(f"\n⚠️ {len(alerts)} active alert(s)")
    else:
        print("\n✓ No active alerts")
    
    # Run prompt optimization
    # (Only works if you have enough data for a prompt)
    # result = prompt_optimizer.run_optimization(
    #     prompt_id="translation",
    #     goal=OptimizationGoal.BALANCED
    # )
    # print(f"Optimization: {result['status']}")


if __name__ == "__main__":
    print("="*60)
    print("OPENAI INTEGRATION EXAMPLES")
    print("="*60)
    print("\nNote: These examples require a valid OPENAI_API_KEY")
    print("Set it in your .env file before running.\n")
    
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  OPENAI_API_KEY not found in environment variables")
        print("Please set it in your .env file and try again.")
    else:
        try:
            example_1_basic_tracking()
            example_2_with_prompt_versioning()
            example_3_decorator_style()
            example_4_monitoring_and_optimization()
            
            print("\n" + "="*60)
            print("✨ All examples completed successfully!")
            print("Run 'streamlit run dashboard/app.py' to view metrics")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("\nMake sure your OpenAI API key is valid and you have credits.")
