# Architecture Documentation

## 🏗️ System Architecture Overview

This document provides a detailed explanation of the system's architecture, design decisions, and component interactions.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Your App   │  │ Streamlit    │  │   Examples   │  │
│  │              │  │  Dashboard   │  │   & Demos    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
└─────────┼──────────────────┼──────────────────┼─────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
┌────────────────────────────┼──────────────────────────┐
│                    Core Services Layer                 │
│  ┌──────────────────┐  ┌──────────────────┐          │
│  │   Telemetry      │  │   Optimization   │          │
│  │   Tracker        │  │   Engine         │          │
│  └────────┬─────────┘  └─────────┬────────┘          │
│           │                      │                     │
│  ┌────────┴──────────────────────┴────────┐          │
│  │         Monitoring Service              │          │
│  │  • Metrics Aggregation                  │          │
│  │  • Anomaly Detection                    │          │
│  │  • Alert Management                     │          │
│  └────────────────┬────────────────────────┘          │
└───────────────────┼─────────────────────────────────┘
                    │
┌───────────────────┼─────────────────────────────────┐
│              Data Layer                               │
│  ┌──────────────────────────────────────────────┐   │
│  │          SQLAlchemy ORM                       │   │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────┐       │   │
│  │  │Telemetry│ │ Prompt   │ │ Alerts  │       │   │
│  │  │  Logs   │ │ Versions │ │         │       │   │
│  │  └─────────┘ └──────────┘ └─────────┘       │   │
│  └──────────────────┬───────────────────────────┘   │
│                     │                                 │
│  ┌──────────────────┴───────────────────────────┐   │
│  │         SQLite/PostgreSQL Database           │   │
│  └──────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────┘
```

## Component Details

### 1. Telemetry Tracker (`src/telemetry/tracker.py`)

**Responsibility**: Capture and record metrics for every LLM API call

**Key Features**:
- Context manager for automatic tracking
- Decorator support for cleaner code
- Non-intrusive integration
- Graceful error handling

**Design Pattern**: Context Manager + Decorator

**Data Flow**:
1. Request initiated
2. Start timer and generate request ID
3. Execute LLM call
4. Capture response metrics (tokens, latency)
5. Calculate costs
6. Store in database

**Code Example**:
```python
with tracker.track_request(...) as ctx:
    response = llm_call()
    ctx.set_tokens(input, output)
    ctx.set_response(response)
```

### 2. Database Layer (`src/database/`)

**Models**:

#### TelemetryLog
- Stores every API call with full metrics
- Indexed by timestamp, model, prompt_id
- Supports JSON metadata for extensibility

#### PromptVersion
- Version control for prompts
- Tracks performance per version
- Enables A/B testing

#### ModelMetrics
- Aggregated statistics per time window
- Pre-computed for fast querying
- Hourly/daily/weekly rollups

#### Alert
- Stores triggered alerts
- Tracks resolution status
- Links to specific models/prompts

#### OptimizationRun
- Audit trail for optimization
- Stores recommendations
- Tracks success/failure

**Database Design Decisions**:
- **SQLAlchemy ORM**: Abstraction over SQL, easy migrations
- **SQLite for Dev**: Simple setup, no server needed
- **PostgreSQL Ready**: Production-grade with connection pooling
- **Indexes**: Strategic indexes on timestamp, model_name, prompt_id

### 3. Model Monitor (`src/monitoring/monitor.py`)

**Responsibility**: Aggregate data and provide insights

**Key Algorithms**:

#### Metrics Aggregation
- Calculates percentiles (P50, P95, P99) for latency
- Computes running averages for costs and quality
- Groups by time windows for trends

#### Anomaly Detection
Uses Z-score method:
```
Z = (X - μ) / σ

Where:
- X = observed value
- μ = mean of historical data
- σ = standard deviation
```

If |Z| > threshold (default 2.0), mark as anomaly.

#### Alert Generation
Compares metrics against configurable thresholds:
- Latency > 2000ms → Alert
- Error rate > 5% → Alert
- Cost > budget → Alert

### 4. Prompt Optimizer (`src/optimization/optimizer.py`)

**Responsibility**: A/B testing and automatic optimization

**Key Components**:

#### PromptManager
- Version control system for prompts
- Traffic splitting for A/B tests
- Template variable substitution

#### PromptOptimizer
- Analyzes performance across versions
- Calculates composite scores based on goals
- Recommends best-performing variants

**Optimization Goals**:

1. **LATENCY**: Minimize response time
   - Score = -avg_latency_ms

2. **COST**: Minimize API costs
   - Score = -avg_cost_usd

3. **QUALITY**: Maximize response quality
   - Score = avg_quality_score

4. **BALANCED**: Optimize all together
   - Score = (normalized_latency + normalized_cost + quality + success_rate) / 4

### 5. Dashboard (`dashboard/app.py`)

**Framework**: Streamlit

**Pages**:

1. **Overview**: High-level KPIs and recent activity
2. **Model Monitoring**: Deep dive into model performance
3. **Prompt Management**: CRUD operations for prompts
4. **Alerts**: View and manage alerts
5. **Settings**: Configure system parameters

**Visualization Library**: Plotly for interactive charts

## Design Decisions

### Why Context Managers?

```python
with tracker.track_request(...) as ctx:
    # Your code
```

**Benefits**:
- Automatic cleanup (even on errors)
- Clear scope boundaries
- Non-intrusive (wraps existing code)
- Handles exceptions gracefully

### Why SQLAlchemy ORM?

**Pros**:
- Database agnostic (SQLite → PostgreSQL migration is trivial)
- Python objects instead of SQL strings
- Built-in connection pooling
- Query optimization

**Cons**:
- Slight performance overhead (acceptable for this use case)
- Learning curve

### Why Streamlit?

**Pros**:
- Rapid development (pages built in hours, not days)
- Python-native (no JavaScript needed)
- Built-in widgets and components
- Good for MVPs and internal tools

**Cons**:
- Limited customization compared to React/Vue
- Not ideal for public-facing apps (but perfect for internal dashboards)

### Why Prompt Versioning?

LLM responses are highly sensitive to prompt phrasing. Small changes can have big impacts:

- "Summarize" → Generic output
- "Summarize in 2 sentences" → Better
- "You are an expert. Summarize in 2 sentences focusing on key points" → Best

Without versioning, you can't:
- Track what prompted what response
- Compare performance systematically
- Roll back to previous versions

## Data Flow Example

### Complete Request Flow:

```
1. User Request
   ↓
2. Get Prompt Version (A/B testing picks variant)
   ↓
3. Format Prompt Template
   ↓
4. Start Telemetry Tracking
   ↓
5. Call LLM API
   ↓
6. Capture Response
   ↓
7. Calculate Metrics (latency, tokens, cost)
   ↓
8. Store in TelemetryLog
   ↓
9. Check Alert Thresholds
   ↓
10. Update Aggregated Metrics
    ↓
11. Return Response to User
```

## Scalability Considerations

### Current MVP (SQLite):
- **Requests/sec**: ~100
- **Data size**: Millions of records
- **Users**: Single team

### Production (PostgreSQL):
- **Requests/sec**: 1000+
- **Data size**: Billions of records
- **Users**: Multiple teams

**To Scale**:
1. Replace SQLite with PostgreSQL
2. Add Redis for caching
3. Implement async I/O (asyncio)
4. Use message queue (RabbitMQ) for telemetry
5. Separate read/write databases (CQRS pattern)

## Security Considerations

### Current Implementation:
- Environment variables for API keys
- No authentication (internal tool)
- SQLite file permissions

### Production Requirements:
- Encrypt API keys at rest
- Add user authentication (OAuth2)
- Role-based access control (RBAC)
- API rate limiting
- Audit logging
- HTTPS for dashboard

## Testing Strategy

### Unit Tests (to be added):
```python
def test_telemetry_tracker():
    with tracker.track_request(...) as ctx:
        ctx.set_tokens(10, 20)
        assert ctx.data["input_tokens"] == 10
```

### Integration Tests:
```python
def test_end_to_end_flow():
    # Create prompt version
    # Make tracked call
    # Verify data in database
    # Check metrics calculation
```

### Performance Tests:
- Measure tracker overhead (< 1ms)
- Database query performance (< 100ms)
- Dashboard load time (< 2s)

## Future Enhancements

### Short-term (1-3 months):
- [ ] Add more LLM providers (Anthropic, Cohere)
- [ ] Implement caching layer
- [ ] Add export functionality (CSV, JSON)
- [ ] Email/Slack alert notifications

### Medium-term (3-6 months):
- [ ] Semantic similarity scoring
- [ ] Automatic prompt generation
- [ ] Multi-tenant support
- [ ] API endpoints (REST/GraphQL)

### Long-term (6+ months):
- [ ] ML-based anomaly detection
- [ ] Predictive cost modeling
- [ ] Integration with CI/CD pipelines
- [ ] Mobile dashboard app

## Conclusion

This architecture provides:
- ✅ **Modularity**: Each component can be developed/tested independently
- ✅ **Scalability**: Clear path from MVP to production
- ✅ **Maintainability**: Clean separation of concerns
- ✅ **Extensibility**: Easy to add new features
- ✅ **Observability**: Full visibility into system behavior

The design prioritizes:
1. **Developer Experience**: Easy to integrate and use
2. **Data Integrity**: Reliable tracking and storage
3. **Performance**: Minimal overhead on LLM calls
4. **Flexibility**: Adaptable to different use cases
