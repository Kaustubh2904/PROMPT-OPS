"""
examples/real_demo.py — Live OpenRouter Demo
=============================================

Makes REAL LLM calls through OpenRouter (free models, $0 cost) and
demonstrates every feature of the PROMPT-OPS closed-loop system:

  1. Basic pipeline call with auto-evaluation
  2. A/B testing between prompt versions
  3. Temperature optimization experiment
  4. Cost-aware model routing
  5. Monitoring and alerting
  6. Automatic prompt optimization

Usage:
    python examples/real_demo.py
"""

import os, sys, time

# ── path setup ──────────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from config import settings, FREE_MODELS
from src.database import init_database
from src.optimization.optimizer import PromptManager, PromptOptimizer, OptimizationGoal
from src.monitoring.monitor import ModelMonitor
from src.pipeline.orchestrator import PromptOpsPipeline


# ── helpers ─────────────────────────────────────────────────
def banner(text: str):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def check_key():
    if not settings.openrouter_api_key:
        print("❌  OPENROUTER_API_KEY is not set in .env")
        print("    Get a free key → https://openrouter.ai/keys")
        sys.exit(1)
    print("✅ API key found")


def setup_prompts(pm: PromptManager):
    """Create prompt versions for A/B testing."""
    print("\n📝 Setting up prompt versions …")

    pairs = [
        ("summarize", "Summarize the following text:\n\n{input}",
         "Basic Summarization", "control", True),
        ("summarize",
         "You are an expert analyst. Read the text below and produce a clear, "
         "concise summary in exactly 3 bullet points. Be specific.\n\nText:\n{input}",
         "Enhanced Summarization", "variant_a", False),
        ("qa", "Answer this question:\n{input}",
         "Basic Q&A", "control", True),
        ("qa",
         "You are a knowledgeable assistant. Answer accurately and concisely. "
         "If unsure, say so. Provide a brief explanation.\n\nQuestion: {input}",
         "Enhanced Q&A", "variant_a", False),
    ]

    for pid, tmpl, name, group, default in pairs:
        try:
            pm.create_prompt_version(
                prompt_id=pid, template=tmpl, name=name,
                is_default=default, ab_test_group=group, traffic_weight=0.5,
            )
            print(f"   ✅ {pid} — {name}")
        except Exception:
            print(f"   ⏭  {pid} — {name} (already exists)")


# ═══════════════════════════════════════════════════════════
#  DEMOS
# ═══════════════════════════════════════════════════════════
def demo_basic(pipe: PromptOpsPipeline):
    banner("1 · Basic Pipeline Call + Auto-Evaluation")
    r = pipe.run(
        user_input="Explain what machine learning is in simple terms.",
        model=settings.openrouter_default_model,
        temperature=0.7,
        enable_evaluation=True,
        tags=["demo", "basic"],
    )
    print(f"📤 Model   : {r.model}")
    print(f"📤 Response: {r.content[:300]}…")
    print(f"   ⏱ Latency : {r.latency_ms:.0f} ms")
    print(f"   🔢 Tokens  : {r.input_tokens + r.output_tokens}")
    if r.quality_score is not None:
        print(f"   ⭐ Quality : {r.quality_score:.2f}")


def demo_ab(pipe: PromptOpsPipeline, pm: PromptManager, n: int = 4):
    banner("2 · A/B Testing — Prompt Versions")
    text = (
        "Artificial intelligence spending hit $200 billion in 2025, up 35% year-over-year. "
        "Healthcare led adoption with 40% of hospitals using AI diagnostics."
    )
    for i in range(n):
        r = pipe.run(
            user_input=text, prompt_id="summarize",
            model=settings.openrouter_default_model,
            enable_evaluation=True, ab_testing=True,
            tags=["demo", "ab_test"],
        )
        v = f"v{r.prompt_version}" if r.prompt_version else "default"
        q = f"{r.quality_score:.2f}" if r.quality_score else "—"
        print(f"   [{i + 1}/{n}] version={v}  quality={q}  latency={r.latency_ms:.0f}ms")
        time.sleep(0.3)

    print("\n📊 Version comparison:")
    for v in pm.get_prompt_versions("summarize"):
        qs = f"{v.avg_quality_score:.2f}" if v.avg_quality_score else "—"
        print(f"   v{v.version} ({v.name}) — calls={v.total_calls or 0}  quality={qs}")


def demo_temperature(pipe: PromptOpsPipeline):
    banner("3 · Temperature Optimisation")
    from src.optimization.temperature_optimizer import TemperatureOptimizer

    t = TemperatureOptimizer()
    result = t.run_experiment(
        prompt_id="summarize",
        prompt_text=(
            "You are an expert analyst. Summarize in 3 bullet points:\n\n"
            "The global EV market grew 25% in 2025 to 20 million units. China had 60% share."
        ),
        model=settings.openrouter_default_model,
    )
    print(f"🏆 Best temperature : {result.best_temperature}")
    print(f"   Quality score    : {result.best_quality_score:.3f}")
    for temp, data in sorted(result.results_by_temp.items()):
        print(f"   temp={temp:.1f}  quality={data['avg_quality']:.3f}  consistency={data['consistency']:.3f}")


def demo_cost_routing(pipe: PromptOpsPipeline):
    banner("4 · Cost-Aware Model Routing")
    premium = FREE_MODELS[-1]
    r = pipe.run(
        user_input="What is the capital of France?",
        prompt_id="qa", model=premium,
        enable_cost_routing=True, enable_evaluation=True,
        tags=["demo", "routing"],
    )
    print(f"   Requested : {premium}")
    print(f"   Routed to : {r.model}")
    print(f"   Downgraded: {'Yes ✅' if r.was_cost_routed else 'No'}")
    if r.quality_score:
        print(f"   Quality   : {r.quality_score:.2f}")


def demo_monitoring(monitor: ModelMonitor):
    banner("5 · Monitoring Summary")
    monitor.aggregate_hourly_metrics(hours_back=1)
    summaries = monitor.get_all_models_summary(time_window_hours=1)
    if summaries:
        for s in summaries:
            if s.get("total_requests", 0) > 0:
                lat = f"{s['avg_latency_ms']:.0f}ms" if s.get("avg_latency_ms") else "—"
                print(f"   {s['model_name']} — reqs={s['total_requests']}  "
                      f"success={s['success_rate']:.0%}  latency={lat}")
    else:
        print("   (no data yet)")

    alerts = monitor.get_active_alerts()
    if alerts:
        print(f"\n   🚨 {len(alerts)} active alert(s):")
        for a in alerts:
            print(f"      {a.alert_type}: {a.message}")
    else:
        print("\n   ✅ No alerts")


def demo_optimise():
    banner("6 · Automatic Prompt Optimisation")
    opt = PromptOptimizer()
    for pid in ["summarize", "qa"]:
        try:
            result = opt.run_optimization(pid, OptimizationGoal.BALANCED)
            if result["status"] == "success":
                rec = result["recommendation"]
                print(f"   ✅ {pid}: best = v{rec['recommended_version']} "
                      f"({rec['version_name']}) score={rec['score']:.3f}")
            else:
                print(f"   ⏳ {pid}: {result.get('message', 'need more data')}")
        except Exception as e:
            print(f"   ⚠  {pid}: {e}")


# ═══════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════
def main():
    banner("PROMPT-OPS — Live OpenRouter Demo")
    print(f"   Default model : {settings.openrouter_default_model}")
    print(f"   Judge model   : {settings.openrouter_judge_model}")
    print(f"   Database      : {settings.database_url}")

    check_key()
    init_database()
    print("✅ Database ready")

    pm = PromptManager()
    mon = ModelMonitor()
    setup_prompts(pm)

    pipe = PromptOpsPipeline()

    try:
        demo_basic(pipe)
        time.sleep(0.5)
        demo_ab(pipe, pm)
        time.sleep(0.5)
        demo_temperature(pipe)
        time.sleep(0.5)
        demo_cost_routing(pipe)
        time.sleep(0.5)
        demo_monitoring(mon)
        demo_optimise()
    except KeyboardInterrupt:
        print("\n⚠  Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

    banner("DEMO COMPLETE")
    print("""
   Next → open the dashboard:
     streamlit run dashboard/app.py
""")


if __name__ == "__main__":
    main()
