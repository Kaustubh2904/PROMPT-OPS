# Frequently Asked Questions (FAQ)

## General Questions

### Q: What is this system for?

**A**: This is a **Telemetry-Aware Model Monitoring and Prompt Optimization System** designed to:
- Track performance of Large Language Model (LLM) API calls
- Monitor costs, latency, and quality
- Optimize prompts through A/B testing
- Detect anomalies and alert on issues

Think of it as "Google Analytics for LLM applications" - you get visibility into how your AI is performing.

### Q: Who is this system for?

**A**: 
- **Students**: Learning about MLOps and LLM applications
- **Developers**: Building AI-powered applications
- **Companies**: Running LLM services in production
- **Researchers**: Studying prompt engineering effectiveness

### Q: Is this production-ready?

**A**: This is an **MVP (Minimum Viable Product)** suitable for:
- ✅ Academic projects and presentations
- ✅ Small-scale applications (< 1000 requests/day)
- ✅ Internal tools and prototypes
- ⚠️ Production use (requires PostgreSQL, authentication, etc.)

## Installation & Setup

### Q: What Python version do I need?

**A**: Python 3.8 or higher. Check with:
```powershell
python --version
```

### Q: Do I need an OpenAI API key?

**A**: 
- **For the demo**: No, it simulates API calls
- **For real integration**: Yes, get one at https://platform.openai.com/

### Q: Why do I get "execution policy" errors on Windows?

**A**: Windows PowerShell restricts script execution by default. Fix it with:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Q: Can I use this with other LLM providers?

**A**: Yes! The system is designed to be provider-agnostic. Currently includes:
- OpenAI (GPT-3.5, GPT-4)
- Anthropic (Claude) - pricing configured
- Easy to add: Cohere, Hugging Face, Azure OpenAI, etc.

## Usage Questions

### Q: How do I integrate this with my existing code?

**A**: Three easy ways:

**1. Context Manager (Recommended)**:
```python
from src.telemetry import tracker

with tracker.track_request(model_name="gpt-4", ...) as ctx:
    response = your_existing_llm_call()
    ctx.set_tokens(input_tokens, output_tokens)
    ctx.set_response(response)
```

**2. Decorator**:
```python
@tracker.track_openai_call(prompt_id="my_prompt")
def my_function():
    return openai.ChatCompletion.create(...)
```

**3. Manual**:
```python
# Track manually if needed
telemetry_data = {...}
tracker._save_telemetry(telemetry_data)
```

### Q: How do I create a new prompt version?

**A**: Use the PromptManager:
```python
from src.optimization import prompt_manager

prompt_manager.create_prompt_version(
    prompt_id="my_prompt",
    template="Your prompt text here",
    name="Descriptive Name",
    is_default=True
)
```

Or use the dashboard's "Prompt Management" page.

### Q: How does A/B testing work?

**A**: 
1. Create multiple prompt versions with different `traffic_weight`
2. System automatically selects versions based on weights
3. Each version gets tracked separately
4. Analyzer determines which performs best

Example:
```python
# Version 1: 50% traffic
create_prompt_version(..., traffic_weight=0.5)

# Version 2: 50% traffic
create_prompt_version(..., traffic_weight=0.5)
```

### Q: What metrics are tracked automatically?

**A**: Every request captures:
- ⏱️ **Latency**: Response time in milliseconds
- 🔢 **Tokens**: Input and output token counts
- 💰 **Cost**: Calculated based on model pricing
- ✅ **Success/Error**: Whether the request succeeded
- 📊 **Quality**: Optional quality score (0-1)
- 👍👎 **Feedback**: Optional user feedback
- 🏷️ **Metadata**: Custom tags and properties

## Technical Questions

### Q: What database does it use?

**A**: 
- **Development**: SQLite (file-based, no server needed)
- **Production**: PostgreSQL recommended (just change `DATABASE_URL`)

### Q: How much data will it store?

**A**: Approximate storage per request:
- ~2 KB per telemetry log
- 1,000 requests = ~2 MB
- 1,000,000 requests = ~2 GB

Implement data retention policies for production.

### Q: What's the performance impact?

**A**: Minimal:
- Tracking overhead: < 1ms
- Database write: < 10ms (asynchronous)
- Total impact: < 1% of typical LLM latency (200-2000ms)

### Q: Can I export the data?

**A**: Yes, several ways:
1. Direct database access (it's SQLite/PostgreSQL)
2. Use pandas: `df = pd.read_sql("SELECT * FROM telemetry_logs", connection)`
3. API endpoints (to be added)

### Q: How do I backup the data?

**A**:
```powershell
# SQLite backup
Copy-Item telemetry.db telemetry_backup_$(Get-Date -Format 'yyyyMMdd').db

# PostgreSQL backup
pg_dump database_name > backup.sql
```

## Troubleshooting

### Q: Dashboard shows "No data available"

**A**: Run the demo first to generate sample data:
```powershell
python examples\demo.py
```

### Q: "Import error: No module named 'src'"

**A**: Make sure you're running from the project root:
```powershell
cd d:\projects\extra-work\final-yr
python examples\demo.py
```

### Q: Streamlit won't start

**A**: 
1. Check if virtual environment is activated
2. Verify installation: `pip show streamlit`
3. Try reinstalling: `pip install --force-reinstall streamlit`

### Q: Database locked error

**A**: SQLite doesn't handle concurrent writes well. Either:
- Use a single process for writes
- Migrate to PostgreSQL for production

### Q: Metrics look wrong

**A**: Check:
1. Model pricing in `config/config.py`
2. Token counts are being set correctly
3. Time zone settings (all times are UTC)

## Conceptual Questions

### Q: Why is monitoring LLMs important?

**A**: LLMs are:
- **Expensive**: $0.03 per 1K tokens (GPT-4)
- **Variable**: Same prompt can give different results
- **Unpredictable**: Latency varies based on load
- **Complex**: Many parameters affect performance

Without monitoring, you're flying blind.

### Q: What's the difference between telemetry and monitoring?

**A**:
- **Telemetry**: Raw data collection (every request)
- **Monitoring**: Aggregation and analysis (averages, trends)

Telemetry feeds monitoring.

### Q: Why use prompts versioning?

**A**: Because:
- Small prompt changes → Big result differences
- Need to track what prompt generated what response
- Want to compare variants scientifically
- Must be able to roll back bad changes

### Q: How is anomaly detection useful?

**A**: Catches issues like:
- Sudden latency spikes (API problems)
- Cost increases (inefficient prompts)
- Quality drops (model changes)
- Error rate increases (outages)

## Project Presentation

### Q: What should I focus on in my presentation?

**A**: Cover these points:
1. **Problem**: Why LLM monitoring matters
2. **Solution**: Your system architecture
3. **Demo**: Live demonstration
4. **Technical**: Key algorithms and design decisions
5. **Results**: Metrics and insights
6. **Future**: Potential enhancements

### Q: What are the key technical contributions?

**A**:
1. Non-intrusive telemetry collection
2. Automatic A/B testing framework
3. Real-time monitoring dashboard
4. Statistical anomaly detection
5. Modular, extensible architecture

### Q: What makes this project unique?

**A**:
- **End-to-end**: Complete monitoring solution, not just one piece
- **Production-oriented**: Real design patterns, not toy code
- **Educational**: Well-documented with learning materials
- **Practical**: Solves actual industry problems

### Q: How do I explain the technical depth?

**A**: Highlight:
- Database schema design (indexes, relationships)
- Context managers and decorators (Python patterns)
- Statistical methods (Z-score anomaly detection)
- A/B testing implementation (traffic splitting)
- Scalability considerations (SQLite → PostgreSQL)

## Advanced Usage

### Q: Can I add custom metrics?

**A**: Yes! Use the metadata field:
```python
ctx.add_metadata("custom_metric", value)
```

### Q: How do I integrate with existing monitoring?

**A**: 
- Export to Prometheus (metrics exposed)
- Send to Datadog/New Relic (custom integration)
- Push to ELK stack (log shipping)

### Q: Can I use this for non-OpenAI models?

**A**: Absolutely! Just set the `provider` parameter:
```python
tracker.track_request(
    model_name="claude-3",
    provider="anthropic",
    ...
)
```

### Q: How do I implement custom optimization goals?

**A**: Extend the `OptimizationGoal` enum and add scoring logic in `_calculate_score()` method.

## Future Questions

### Q: Will you add [feature X]?

**A**: This is an MVP for educational purposes. However, the codebase is designed to be extended. Check the README for planned enhancements.

### Q: Can I contribute?

**A**: This is an academic project, but the architecture allows easy extensions. Fork it and customize for your needs!

### Q: Is there commercial support?

**A**: No, this is an educational project. For production use, consider:
- [Langfuse](https://langfuse.com/)
- [Weights & Biases](https://wandb.ai/)
- [MLflow](https://mlflow.org/)

## Still Have Questions?

- 📖 Read the full documentation: `README.md`
- 🎓 Try the tutorial: `examples/tutorial.ipynb`
- 💡 Check the examples: `examples/` folder
- 🏗️ Review architecture: `docs/ARCHITECTURE.md`

**For academic purposes, consult your project supervisor.**
