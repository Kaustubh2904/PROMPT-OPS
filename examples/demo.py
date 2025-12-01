"""
Demo Application for Telemetry-Aware Model Monitoring

This script demonstrates how to use the telemetry system
with OpenAI API calls.
"""

import os
import time
import random
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.telemetry import tracker
from src.monitoring import monitor
from src.optimization import prompt_manager, prompt_optimizer, OptimizationGoal
from src.database import init_database


def setup_demo():
    """Initialize the database and create sample prompts."""
    print("🚀 Setting up demo environment...")
    
    # Initialize database
    init_database()
    print("✅ Database initialized")
    
    # Create sample prompt versions
    try:
        # Version 1: Basic summarization prompt
        prompt_manager.create_prompt_version(
            prompt_id="demo_summarization",
            template="Please summarize the following text in 2-3 sentences:\n\n{text}",
            name="Basic Summarization",
            description="Simple and direct summarization prompt",
            is_default=True,
            ab_test_group="control",
            traffic_weight=0.5
        )
        
        # Version 2: Enhanced summarization prompt
        prompt_manager.create_prompt_version(
            prompt_id="demo_summarization",
            template="You are an expert at concise summarization. Analyze the following text and provide a clear, informative summary in 2-3 sentences, focusing on the main points:\n\n{text}",
            name="Enhanced Summarization",
            description="More detailed prompt with better instructions",
            ab_test_group="variant_a",
            traffic_weight=0.5
        )
        
        print("✅ Sample prompts created")
    except Exception as e:
        print(f"⚠️  Prompts may already exist: {e}")


def simulate_llm_call(model_name: str, prompt_text: str, simulate_response: str):
    """
    Simulate an LLM API call with telemetry tracking.
    
    This is a mock function for demo purposes. In production,
    you would call the actual OpenAI API here.
    """
    with tracker.track_request(
        model_name=model_name,
        provider="openai",
        prompt_text=prompt_text,
        prompt_id="demo_summarization",
        prompt_version=random.choice([1, 2]),
        tags=["demo", "summarization"]
    ) as ctx:
        # Simulate API call latency
        time.sleep(random.uniform(0.1, 0.5))
        
        # Simulate token usage
        input_tokens = len(prompt_text.split()) * 1.3  # Rough estimate
        output_tokens = len(simulate_response.split()) * 1.3
        ctx.set_tokens(int(input_tokens), int(output_tokens))
        
        # Set response
        ctx.set_response(simulate_response)
        
        # Simulate quality score
        quality_score = random.uniform(0.7, 0.95)
        ctx.set_quality_score(quality_score)
        
        # Simulate user feedback (80% positive)
        feedback = "positive" if random.random() < 0.8 else "negative"
        ctx.set_user_feedback(feedback)
        
        return simulate_response


def run_demo_scenario_1():
    """
    Scenario 1: Basic telemetry tracking
    Demonstrates simple LLM call tracking
    """
    print("\n" + "="*60)
    print("📊 SCENARIO 1: Basic Telemetry Tracking")
    print("="*60)
    
    sample_text = """
    Artificial Intelligence has revolutionized various industries in recent years.
    From healthcare to finance, AI applications are improving efficiency and decision-making.
    Machine learning algorithms can analyze vast amounts of data, identify patterns,
    and make predictions with remarkable accuracy. However, ethical considerations
    and potential biases in AI systems remain important challenges to address.
    """
    
    prompt_version = prompt_manager.get_prompt_for_request("demo_summarization")
    if prompt_version:
        prompt_text = prompt_version.template.format(text=sample_text)
        print(f"\n🔄 Using prompt version: {prompt_version.version} - {prompt_version.name}")
    else:
        prompt_text = f"Please summarize: {sample_text}"
        print("\n🔄 Using default prompt")
    
    print(f"📝 Making LLM call...")
    
    response = simulate_llm_call(
        model_name="gpt-3.5-turbo",
        prompt_text=prompt_text,
        simulate_response="AI has transformed industries like healthcare and finance through efficient data analysis and pattern recognition. Machine learning algorithms can make accurate predictions from large datasets. Ethical concerns and bias in AI systems remain key challenges."
    )
    
    print(f"✅ Response received: {response[:100]}...")
    print("✅ Telemetry data saved!")


def run_demo_scenario_2():
    """
    Scenario 2: Multiple model comparison
    Makes calls to different models for comparison
    """
    print("\n" + "="*60)
    print("📊 SCENARIO 2: Multiple Model Comparison")
    print("="*60)
    
    models = ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"]
    sample_text = "Explain quantum computing in simple terms."
    
    print(f"\n🔄 Testing {len(models)} different models...")
    
    for model in models:
        print(f"\n  Testing {model}...")
        
        response = simulate_llm_call(
            model_name=model,
            prompt_text=sample_text,
            simulate_response=f"Quantum computing uses quantum mechanics principles to process information. [Response from {model}]"
        )
        
        time.sleep(0.2)  # Brief pause between calls
    
    print("\n✅ All models tested!")
    
    # Show comparison
    print("\n📈 Performance Comparison:")
    for model in models:
        stats = monitor.get_model_stats(model, time_window_hours=1)
        if stats.get("total_requests", 0) > 0:
            print(f"  {model}:")
            print(f"    - Avg Latency: {stats.get('avg_latency_ms', 0):.0f}ms")
            print(f"    - Avg Cost: ${stats.get('avg_cost_per_request', 0):.6f}")
            print(f"    - Success Rate: {stats.get('success_rate', 0):.1%}")


def run_demo_scenario_3():
    """
    Scenario 3: A/B Testing demonstration
    Shows how different prompt versions perform
    """
    print("\n" + "="*60)
    print("📊 SCENARIO 3: A/B Testing Demonstration")
    print("="*60)
    
    print("\n🔄 Running 20 requests with A/B testing...")
    
    sample_texts = [
        "Artificial intelligence is transforming business operations.",
        "Climate change poses significant challenges for future generations.",
        "Blockchain technology enables secure, decentralized transactions.",
        "Remote work has become increasingly popular in recent years.",
        "Renewable energy sources are crucial for sustainability.",
    ]
    
    for i in range(20):
        text = random.choice(sample_texts)
        prompt_version = prompt_manager.get_prompt_for_request("demo_summarization", ab_testing=True)
        
        if prompt_version:
            prompt_text = prompt_version.template.format(text=text)
            
            response = simulate_llm_call(
                model_name="gpt-3.5-turbo",
                prompt_text=prompt_text,
                simulate_response=f"Summary of the text. [Generated by version {prompt_version.version}]"
            )
            
            # Update metrics
            prompt_manager.update_prompt_metrics("demo_summarization", prompt_version.version)
        
        if (i + 1) % 5 == 0:
            print(f"  ✓ Completed {i + 1}/20 requests")
        
        time.sleep(0.1)
    
    print("\n✅ A/B testing complete!")
    
    # Show results
    print("\n📊 A/B Test Results:")
    versions = prompt_manager.get_prompt_versions("demo_summarization")
    for version in versions:
        if version.total_calls and version.total_calls > 0:
            print(f"\n  Version {version.version}: {version.name}")
            print(f"    - Calls: {version.total_calls}")
            print(f"    - Avg Latency: {version.avg_latency_ms:.0f}ms" if version.avg_latency_ms else "    - Avg Latency: N/A")
            print(f"    - Avg Quality: {version.avg_quality_score:.2f}" if version.avg_quality_score else "    - Avg Quality: N/A")


def run_demo_scenario_4():
    """
    Scenario 4: Prompt optimization
    Demonstrates automatic prompt optimization
    """
    print("\n" + "="*60)
    print("📊 SCENARIO 4: Prompt Optimization")
    print("="*60)
    
    print("\n🚀 Running optimization analysis...")
    
    try:
        result = prompt_optimizer.run_optimization(
            prompt_id="demo_summarization",
            goal=OptimizationGoal.BALANCED
        )
        
        if result["status"] == "success":
            print("\n✅ Optimization completed successfully!")
            
            recommendation = result["recommendation"]
            print(f"\n🎯 Recommended Version: {recommendation['recommended_version']}")
            print(f"   Name: {recommendation['version_name']}")
            print(f"   Score: {recommendation['score']:.4f}")
            print(f"\n📊 Metrics:")
            metrics = recommendation['metrics']
            print(f"   - Total Calls: {metrics['total_calls']}")
            print(f"   - Success Rate: {metrics['success_rate']:.1%}")
            if metrics.get('avg_latency_ms'):
                print(f"   - Avg Latency: {metrics['avg_latency_ms']:.0f}ms")
            if metrics.get('avg_quality_score'):
                print(f"   - Avg Quality: {metrics['avg_quality_score']:.2f}")
        else:
            print(f"\n⚠️  {result.get('message', 'Optimization could not complete')}")
    
    except Exception as e:
        print(f"\n❌ Optimization failed: {e}")


def run_demo_scenario_5():
    """
    Scenario 5: Error handling and alerts
    Demonstrates error tracking and alert generation
    """
    print("\n" + "="*60)
    print("📊 SCENARIO 5: Error Handling & Alerts")
    print("="*60)
    
    print("\n🔄 Simulating various scenarios including errors...")
    
    # Simulate successful calls with high latency
    for i in range(5):
        with tracker.track_request(
            model_name="gpt-4",
            provider="openai",
            prompt_text="Test prompt",
            tags=["demo", "stress_test"]
        ) as ctx:
            # Simulate high latency
            time.sleep(random.uniform(2.0, 3.0))
            ctx.set_tokens(100, 50)
            ctx.set_response("Test response")
    
    print("  ✓ Simulated high latency calls")
    
    # Simulate some errors
    for i in range(3):
        try:
            with tracker.track_request(
                model_name="gpt-4",
                provider="openai",
                prompt_text="Test prompt that will fail",
                tags=["demo", "error_test"]
            ) as ctx:
                # Simulate error
                raise Exception("Simulated API error")
        except:
            pass  # Error is tracked automatically
    
    print("  ✓ Simulated error conditions")
    
    # Check for alerts
    print("\n🚨 Checking for alerts...")
    
    # Trigger alert check
    stats = monitor.get_model_stats("gpt-4", time_window_hours=1)
    
    active_alerts = monitor.get_active_alerts()
    if active_alerts:
        print(f"\n⚠️  Found {len(active_alerts)} active alert(s):")
        for alert in active_alerts:
            print(f"  - {alert.alert_type}: {alert.message}")
    else:
        print("\n✅ No alerts triggered")


def main():
    """Main demo function."""
    print("="*60)
    print("🎯 TELEMETRY-AWARE MODEL MONITORING DEMO")
    print("="*60)
    print("\nThis demo showcases the key features of the system:")
    print("  1. Automatic telemetry collection")
    print("  2. Multi-model performance comparison")
    print("  3. A/B testing for prompts")
    print("  4. Automatic prompt optimization")
    print("  5. Error handling and alerting")
    
    # Setup
    setup_demo()
    
    # Run scenarios
    try:
        run_demo_scenario_1()
        time.sleep(1)
        
        run_demo_scenario_2()
        time.sleep(1)
        
        run_demo_scenario_3()
        time.sleep(1)
        
        run_demo_scenario_4()
        time.sleep(1)
        
        run_demo_scenario_5()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    # Final summary
    print("\n" + "="*60)
    print("🎉 DEMO COMPLETED!")
    print("="*60)
    print("\n📊 Next Steps:")
    print("  1. Run the dashboard: streamlit run dashboard/app.py")
    print("  2. Explore the Jupyter notebooks in the examples/ folder")
    print("  3. Check the README.md for integration instructions")
    print("  4. Review the generated telemetry.db for stored metrics")
    print("\n✨ Thank you for trying the Telemetry-Aware Model Monitoring system!")


if __name__ == "__main__":
    main()
