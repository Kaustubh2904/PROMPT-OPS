# Telemetry-Aware Model Monitoring and Prompt Optimization

A comprehensive system for monitoring LLM model performance, tracking telemetry data, and automatically optimizing prompts through A/B testing and analytics.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-MVP-orange.svg)

## 🎯 Project Overview

This system provides enterprise-grade observability and optimization for Large Language Model (LLM) applications. It automatically tracks performance metrics, costs, and quality indicators while providing tools for prompt versioning, A/B testing, and automatic optimization.

### Key Features

- **📊 Real-time Telemetry Collection**: Automatically track latency, token usage, costs, and errors for every LLM API call
- **📈 Performance Monitoring**: Comprehensive dashboards showing model performance, trends, and comparisons
- **🔄 Prompt Versioning & A/B Testing**: Manage multiple prompt versions and automatically split traffic for testing
- **🚀 Automatic Optimization**: AI-driven prompt optimization based on performance data
- **🚨 Alerting & Anomaly Detection**: Get notified when metrics exceed thresholds or anomalies are detected
- **💾 Persistent Storage**: SQLite database for storing all telemetry and configuration data
- **🎨 Interactive Dashboard**: Beautiful Streamlit web interface for visualization and management

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Application                          │
│  (OpenAI/Anthropic API calls wrapped with telemetry)        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                 Telemetry Tracker                            │
│  • Captures request/response data                            │
│  • Calculates metrics (latency, tokens, cost)                │
│  • Handles errors gracefully                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer                             │
│  • SQLAlchemy ORM                                            │
│  • Stores: Telemetry logs, Prompt versions, Alerts          │
└──────────┬──────────────────────────┬───────────────────────┘
           │                          │
           ▼                          ▼
┌──────────────────────┐   ┌─────────────────────────┐
│  Model Monitor       │   │  Prompt Optimizer        │
│  • Aggregates data   │   │  • A/B testing logic     │
│  • Detects anomalies │   │  • Performance analysis  │
│  • Generates alerts  │   │  • Auto-optimization     │
└──────────┬───────────┘   └────────────┬────────────┘
           │                            │
           └────────────┬───────────────┘
                        │
                        ▼
           ┌────────────────────────┐
           │   Streamlit Dashboard  │
           │   • Visualizations     │
           │   • Management UI      │
           │   • Real-time metrics  │
           └────────────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) OpenAI API key for testing with real LLM calls

### Step 1: Clone or Download

```bash
cd d:\projects\extra-work\final-yr
```

### Step 2: Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# If you get an execution policy error, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

### Step 4: Configure Environment

```powershell
# Copy the example environment file
Copy-Item .env.example .env

# Edit .env file with your settings (optional for demo)
# notepad .env
```

### Step 5: Initialize Database

```powershell
python -c "from src.database import init_database; init_database()"
```

## 🚀 Quick Start

### Run the Demo

The easiest way to see the system in action is to run the demo:

```powershell
python examples\demo.py
```

This will:
1. Initialize the database
2. Create sample prompt versions
3. Simulate LLM API calls with telemetry tracking
4. Demonstrate A/B testing
5. Run prompt optimization
6. Show error handling and alerting

### Launch the Dashboard

After running the demo (or after collecting real telemetry data):

```powershell
streamlit run dashboard\app.py
```

The dashboard will open in your browser at `http://localhost:8501`

Navigate through the different pages:
- **Dashboard Overview**: High-level metrics and recent activity
- **Model Monitoring**: Detailed performance analysis per model
- **Prompt Management**: Create and manage prompt versions
- **Alerts & Anomalies**: View and resolve alerts
- **Settings**: Configure thresholds and system settings

## 📚 Usage Guide

### Basic Integration

#### 1. Context Manager Style (Recommended)

```python
from src.telemetry import tracker
from src.database import init_database

# Initialize once
init_database()

# Track a request
with tracker.track_request(
    model_name="gpt-4",
    provider="openai",
    prompt_text="What is machine learning?",
    tags=["production", "faq"]
) as ctx:
    # Make your API call here
    response = your_llm_call()
    
    # Set metrics
    ctx.set_tokens(input_tokens=10, output_tokens=50)
    ctx.set_response(response)
    ctx.set_quality_score(0.9)  # Optional
```

#### 2. Decorator Style

```python
@tracker.track_openai_call(
    prompt_id="summarization_v1",
    tags=["production"]
)
def call_openai(prompt, model="gpt-3.5-turbo"):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    return response
```

### Prompt Versioning

#### Create a Prompt Version

```python
from src.optimization import prompt_manager

prompt_manager.create_prompt_version(
    prompt_id="summarization",
    template="Summarize the following text:\n\n{text}",
    name="Basic Summarization",
    description="Simple summarization prompt",
    is_default=True
)
```

#### Get Prompt for Request (with A/B Testing)

```python
# This automatically handles A/B testing and traffic splitting
prompt_version = prompt_manager.get_prompt_for_request(
    prompt_id="summarization",
    ab_testing=True
)

prompt_text = prompt_version.template.format(text=your_text)
```

### Monitoring

#### Get Model Statistics

```python
from src.monitoring import monitor

stats = monitor.get_model_stats(
    model_name="gpt-4",
    time_window_hours=24
)

print(f"Total requests: {stats['total_requests']}")
print(f"Average latency: {stats['avg_latency_ms']}ms")
print(f"Success rate: {stats['success_rate']:.1%}")
```

#### Detect Anomalies

```python
anomalies = monitor.detect_anomalies(
    model_name="gpt-4",
    metric="latency_ms",
    sensitivity=2.0  # Standard deviations
)
```

### Optimization

#### Run Prompt Optimization

```python
from src.optimization import prompt_optimizer, OptimizationGoal

result = prompt_optimizer.run_optimization(
    prompt_id="summarization",
    goal=OptimizationGoal.BALANCED  # or LATENCY, COST, QUALITY
)

if result["status"] == "success":
    recommended_version = result["recommendation"]["recommended_version"]
    print(f"Best version: {recommended_version}")
```

## 📊 Understanding the Metrics

### Telemetry Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| **Latency** | Time from request to response | milliseconds |
| **Input Tokens** | Number of tokens in the prompt | count |
| **Output Tokens** | Number of tokens in the response | count |
| **Cost** | Estimated API cost | USD |
| **Quality Score** | Custom quality metric (0-1) | score |
| **Error Rate** | Percentage of failed requests | percentage |

### Aggregated Metrics

- **P50, P95, P99 Latency**: Percentile latencies for performance analysis
- **Success Rate**: Percentage of requests without errors
- **Average Cost per Request**: Mean cost across all requests
- **Feedback Ratio**: Positive feedback / (positive + negative)

## 🎓 Learning Materials

### Core Concepts

#### 1. **Telemetry Collection**
Telemetry is the automatic measurement and wireless transmission of data. In this system:
- Every LLM API call is automatically tracked
- Metrics are captured without modifying your core logic
- Data is stored for historical analysis

#### 2. **Prompt Engineering & Versioning**
- Different phrasings of prompts can yield vastly different results
- Version control allows you to track changes and compare performance
- A/B testing helps identify the best-performing variant

#### 3. **A/B Testing**
- Multiple prompt versions run simultaneously
- Traffic is split according to configured weights
- Statistical analysis determines the winner

#### 4. **Anomaly Detection**
- Z-score based detection (statistical method)
- Identifies unusual patterns in latency, cost, or quality
- Helps catch issues before they become critical

#### 5. **Cost Optimization**
- Different models have different cost structures
- Monitoring helps identify expensive operations
- Can switch to cheaper models for simple tasks

## 🔧 Configuration

### Environment Variables

Edit the `.env` file to configure the system:

```bash
# API Keys (for real LLM calls)
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Database
DATABASE_URL=sqlite:///./telemetry.db

# Telemetry
ENABLE_TELEMETRY=true

# Alert Thresholds
LATENCY_THRESHOLD_MS=2000
ERROR_RATE_THRESHOLD=0.05
COST_THRESHOLD_USD=10.0

# Optimization
AUTO_OPTIMIZE_ENABLED=true
MIN_SAMPLES_FOR_OPTIMIZATION=10
```

### Model Pricing

Pricing is configured in `config/config.py`. Update if API prices change:

```python
MODEL_PRICING = {
    "gpt-4": {"input": 0.03, "output": 0.06},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
}
```

## 📁 Project Structure

```
final-yr/
├── config/                  # Configuration management
│   ├── __init__.py
│   └── config.py           # Settings and pricing
├── src/                    # Source code
│   ├── database/           # Database models and connection
│   │   ├── __init__.py
│   │   ├── models.py       # SQLAlchemy models
│   │   └── connection.py   # DB connection management
│   ├── telemetry/          # Telemetry collection
│   │   ├── __init__.py
│   │   └── tracker.py      # Core tracking logic
│   ├── monitoring/         # Performance monitoring
│   │   ├── __init__.py
│   │   └── monitor.py      # Metrics and alerts
│   └── optimization/       # Prompt optimization
│       ├── __init__.py
│       └── optimizer.py    # A/B testing and optimization
├── dashboard/              # Web dashboard
│   └── app.py             # Streamlit application
├── examples/               # Example scripts
│   ├── demo.py            # Full demo
│   └── openai_integration.py  # OpenAI examples
├── data/                   # Data directory (auto-created)
├── logs/                   # Log files (auto-created)
├── requirements.txt        # Python dependencies
├── .env.example           # Environment template
└── README.md              # This file
```

## 🎯 Presentation Tips

### For Your Final Year Project Defense

1. **Start with the Problem**
   - LLM applications are expensive and unpredictable
   - No visibility into performance or costs
   - Difficult to optimize prompts systematically

2. **Show the Demo**
   - Run `python examples\demo.py` live
   - Show the dashboard with real metrics
   - Demonstrate A/B testing results

3. **Explain the Architecture**
   - Use the architecture diagram
   - Explain how components interact
   - Highlight the modular design

4. **Technical Deep Dive**
   - Show the database schema (models.py)
   - Explain the telemetry tracker implementation
   - Discuss the optimization algorithms

5. **Real-World Applications**
   - Production monitoring for LLM-based products
   - Cost optimization for AI startups
   - Quality assurance for customer-facing AI

### Key Talking Points

- **Scalability**: SQLAlchemy supports PostgreSQL for production
- **Extensibility**: Modular design allows adding new metrics
- **Non-intrusive**: Minimal code changes to integrate
- **Data-driven**: All decisions backed by actual metrics
- **Industry-relevant**: Solves real problems in AI/ML space

## 🐛 Troubleshooting

### Common Issues

**Issue**: Import errors when running scripts
```powershell
# Solution: Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# And you're in the project root directory
cd d:\projects\extra-work\final-yr
```

**Issue**: Database errors
```powershell
# Solution: Reinitialize the database
python -c "from src.database import db_manager; db_manager.drop_tables(); db_manager.create_tables()"
```

**Issue**: Streamlit not found
```powershell
# Solution: Reinstall requirements
pip install -r requirements.txt
```

**Issue**: No data showing in dashboard
```powershell
# Solution: Run the demo first to generate data
python examples\demo.py
```

## 📝 Future Enhancements

- [ ] Support for more LLM providers (Anthropic, Cohere, etc.)
- [ ] Advanced optimization algorithms (Bayesian optimization)
- [ ] Cost prediction and budgeting
- [ ] Semantic similarity analysis for responses
- [ ] Integration with existing MLOps tools (MLflow, Weights & Biases)
- [ ] Real-time streaming dashboard
- [ ] Multi-user authentication and role-based access
- [ ] Export reports to PDF/Excel

## 📄 License

This project is created for educational purposes as a final year project.

## 🤝 Contributing

This is an academic project, but suggestions and feedback are welcome!

## 📧 Contact

For questions about this project, please contact your project supervisor or refer to the project documentation.

---

**Built with** ❤️ **for Final Year Project 2025**

*Telemetry-Aware Model Monitoring and Prompt Optimization System*
