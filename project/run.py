"""
run.py — Single entry point for PROMPT-OPS
==========================================
Initialises the database, creates sample prompts, then runs through
every feature of the closed-loop system with real LLM API calls.

Usage:
    python run.py              # full demo
    python run.py --quick      # just 1 request to verify setup works
"""

import os, sys, time, argparse

# ── path setup ──────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv()

from config import settings, FREE_MODELS
from src.database import init_database
from src.optimization.optimizer import PromptManager, PromptOptimizer, OptimizationGoal
from src.monitoring.monitor import ModelMonitor
from src.pipeline.orchestrator import PromptOpsPipeline

pm = PromptManager()
monitor = ModelMonitor()


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


def setup_prompts():
    """Create two prompt variants for A/B testing."""
    print("\n📝 Setting up prompt versions …")

    pairs = [
        # ── summarisation ──
        (
            "summarize",
            "Summarize the following text:\n\n{input}",
            "Basic Summarization",
            "control",
            True,
        ),
        (
            "summarize",
            "You are an expert analyst. Read the text below and produce a clear, "
            "concise summary in exactly 3 bullet points. Be specific.\n\nText:\n{input}",
            "Enhanced Summarization",
            "variant_a",
            False,
        ),
        # ── Q&A ──
        (
            "qa",
            "Answer this question:\n{input}",
            "Basic Q&A",
            "control",
            True,
        ),
        (
            "qa",
            "You are a knowledgeable assistant. Answer accurately and concisely. "
            "If unsure, say so. Provide a brief explanation.\n\nQuestion: {input}",
            "Enhanced Q&A",
            "variant_a",
            False,
        ),
    ]

    for pid, tmpl, name, group, default in pairs:
        try:
            pm.create_prompt_version(
                prompt_id=pid,
                template=tmpl,
                name=name,
                is_default=default,
                ab_test_group=group,
                traffic_weight=0.5,
            )
            print(f"   ✅ {pid} — {name}")
        except Exception:
            print(f"   ⏭  {pid} — {name} (already exists)")


# ═══════════════════════════════════════════════════════════
#  DEMOS
# ═══════════════════════════════════════════════════════════
def demo_basic(pipe: PromptOpsPipeline):
    """Single call through the full pipeline."""
    banner("1 · Basic Pipeline Call + Auto-Evaluation")
    print("Making one LLM call with full telemetry + quality evaluation …\n")

    r = pipe.run(
        user_input="Explain what machine learning is in simple terms a 10-year-old would understand.",
        model=settings.openrouter_default_model,
        temperature=0.7,
        enable_evaluation=True,
        tags=["demo", "basic"],
    )

    print(f"📤 Model : {r.model}")
    print(f"📤 Response:\n   {r.content[:300]}…\n")
    print(f"   ⏱  Latency : {r.latency_ms:.0f} ms")
    print(f"   🔢 Tokens  : {r.input_tokens + r.output_tokens}")
    if r.quality_score is not None:
        print(f"   ⭐ Quality : {r.quality_score:.2f}")
        if r.evaluation_details:
            d = r.evaluation_details
            print(f"       relevance={d.get('relevance','—')}  accuracy={d.get('accuracy','—')}  "
                  f"completeness={d.get('completeness','—')}  format={d.get('format_compliance','—')}  "
                  f"safety={d.get('safety','—')}")


def demo_ab(pipe: PromptOpsPipeline, n: int = 4):
    """A/B testing with prompt versions."""
    banner("2 · A/B Testing — Prompt Versions")
    print(f"Sending {n} requests split across prompt versions …\n")

    text = (
        "Artificial intelligence spending hit $200 billion in 2025, up 35% year-over-year. "
        "Healthcare led adoption with 40% of hospitals using AI diagnostics. Concerns about "
        "job displacement grew, with 28% of companies reporting AI-driven layoffs."
    )

    for i in range(n):
        r = pipe.run(
            user_input=text,
            prompt_id="summarize",
            model=settings.openrouter_default_model,
            enable_evaluation=True,
            ab_testing=True,
            tags=["demo", "ab_test"],
        )
        v = f"v{r.prompt_version}" if r.prompt_version else "default"
        q = f"{r.quality_score:.2f}" if r.quality_score else "—"
        print(f"   [{i+1}/{n}] version={v}  quality={q}  latency={r.latency_ms:.0f}ms")
        time.sleep(0.3)

    # show comparison
    print("\n📊 Version comparison:")
    for v in pm.get_prompt_versions("summarize"):
        qs = f"{v.avg_quality_score:.2f}" if v.avg_quality_score else "—"
        print(f"   v{v.version} ({v.name}) — calls={v.total_calls or 0}  quality={qs}")


def demo_temperature(pipe: PromptOpsPipeline):
    """Temperature optimisation experiment."""
    banner("3 · Temperature Optimisation")
    print("Testing temperatures 0.0 → 1.5 (step 0.5, 2 trials each) …\n")

    from src.optimization.temperature_optimizer import TemperatureOptimizer
    t = TemperatureOptimizer()

    result = t.run_experiment(
        prompt_id="summarize",
        prompt_text=(
            "You are an expert analyst. Summarize in 3 bullet points:\n\n"
            "The global EV market grew 25% in 2025 to 20 million units. China had 60% share. "
            "Battery costs fell 15%. Major automakers committed to full EV lineups by 2030."
        ),
        model=settings.openrouter_default_model,
    )

    print(f"🏆 Best temperature : {result.best_temperature}")
    print(f"   Quality score    : {result.best_quality_score:.3f}")
    print(f"   Total trials     : {result.total_trials}")
    for temp, data in sorted(result.results_by_temp.items()):
        print(f"   temp={temp:.1f}  quality={data['avg_quality']:.3f}  consistency={data['consistency']:.3f}")


def demo_cost_routing(pipe: PromptOpsPipeline):
    """Cost-aware model routing."""
    banner("4 · Cost-Aware Model Routing")
    print("Requesting a 'premium' model but letting the router try cheaper ones first …\n")

    # Use the last free model (strongest) as the "expensive" requested model
    premium = FREE_MODELS[-1]

    r = pipe.run(
        user_input="What is the capital of France and why is it culturally significant?",
        prompt_id="qa",
        model=premium,
        enable_cost_routing=True,
        enable_evaluation=True,
        tags=["demo", "routing"],
    )

    print(f"   Requested : {premium}")
    print(f"   Routed to : {r.model}")
    print(f"   Downgraded: {'Yes ✅' if r.was_cost_routed else 'No'}")
    if r.quality_score:
        print(f"   Quality   : {r.quality_score:.2f}")
    print(f"   Response  : {r.content[:200]}…")


def demo_monitoring():
    """Show monitoring stats."""
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
    """Run prompt optimizer."""
    banner("6 · Automatic Prompt Optimisation")
    print("Analyzing prompt versions to recommend the best one …\n")

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
    parser = argparse.ArgumentParser(description="PROMPT-OPS demo runner")
    parser.add_argument("--quick", action="store_true", help="Just one request to verify setup")
    args = parser.parse_args()

    banner("PROMPT-OPS — Closed-Loop Prompt Optimisation System")
    print(f"   Default model : {settings.openrouter_default_model}")
    print(f"   Judge model   : {settings.openrouter_judge_model}")
    print(f"   Database      : {settings.database_url}")

    check_key()
    init_database()
    print("✅ Database ready")

    setup_prompts()

    pipe = PromptOpsPipeline()

    try:
        demo_basic(pipe)

        if args.quick:
            print("\n✅ Quick check passed. Run without --quick for the full demo.")
            return

        time.sleep(0.5)
        demo_ab(pipe)
        time.sleep(0.5)
        demo_temperature(pipe)
        time.sleep(0.5)
        demo_cost_routing(pipe)
        time.sleep(0.5)
        demo_monitoring()
        demo_optimise()

    except KeyboardInterrupt:
        print("\n\n⚠  Interrupted")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback; traceback.print_exc()

    banner("DEMO COMPLETE")
    print("""
   What just happened:
     1. Prompt versions created & A/B tested
     2. Real LLM calls via OpenRouter (free models)
     3. Every response auto-evaluated by LLM-as-Judge
     4. Temperature optimisation experiment ran
     5. Cost-aware model routing tested
     6. Monitoring aggregated & checked alerts
     7. Optimizer recommended best prompt version

   Next → open the dashboard:
     streamlit run dashboard/app.py
""")


if __name__ == "__main__":
    main()
