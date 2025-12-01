# Quick Start Guide

This guide will help you get the Telemetry-Aware Model Monitoring system up and running in 5 minutes!

## 📋 Prerequisites

- Windows PC with PowerShell
- Python 3.8 or higher installed
- Internet connection

## 🚀 5-Minute Setup

### Step 1: Open PowerShell in the Project Directory

```powershell
cd d:\projects\extra-work\final-yr
```

### Step 2: Create and Activate Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate it
.\venv\Scripts\Activate.ps1
```

> **Note**: If you get an execution policy error, run:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### Step 3: Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install all required packages. It may take 2-3 minutes.

### Step 4: Set Up Environment Variables

```powershell
# Copy the example environment file
Copy-Item .env.example .env
```

> **Note**: For the demo, you don't need to edit the .env file. For real OpenAI integration, add your API key.

### Step 5: Run the Demo

```powershell
python examples\demo.py
```

This will:
- Initialize the database
- Create sample prompt versions
- Simulate LLM API calls
- Demonstrate A/B testing
- Run optimization
- Show monitoring metrics

**Expected output**: You should see various scenarios running with ✅ checkmarks.

### Step 6: Launch the Dashboard

```powershell
streamlit run dashboard\app.py
```

Your browser will automatically open to `http://localhost:8501` showing the interactive dashboard!

## 🎓 What to Explore

### In the Dashboard:

1. **Dashboard Overview**: See total requests, costs, and recent activity
2. **Model Monitoring**: Deep dive into performance metrics
3. **Prompt Management**: Create and test different prompt versions
4. **Alerts & Anomalies**: Check system health
5. **Settings**: Configure thresholds

### Learning Materials:

1. **Tutorial Notebook**: Open `examples\tutorial.ipynb` in Jupyter
   ```powershell
   jupyter notebook examples\tutorial.ipynb
   ```

2. **Example Scripts**: Check `examples\` folder for integration examples

3. **Source Code**: Explore the `src\` directory to understand implementation

## 🎯 For Your Presentation

### Demo Flow:

1. **Show the Problem**: Explain why LLM monitoring is important
2. **Live Demo**: Run `python examples\demo.py` 
3. **Dashboard Tour**: Walk through the Streamlit dashboard
4. **Code Walkthrough**: Show the telemetry tracker implementation
5. **Results**: Display the performance metrics and optimization results

### Key Features to Highlight:

- ✅ **Automatic Telemetry Collection**: No manual logging needed
- ✅ **Real-time Monitoring**: See metrics as they happen
- ✅ **A/B Testing**: Data-driven prompt optimization
- ✅ **Cost Tracking**: Understand and manage API spending
- ✅ **Anomaly Detection**: Catch issues before they impact users

### Talking Points:

1. **Architecture**: Modular, scalable design
2. **Technology Stack**: Python, SQLAlchemy, Streamlit, Plotly
3. **Industry Relevance**: Used in production LLM applications
4. **Extensibility**: Easy to add new metrics and features
5. **Open Source**: Can be adapted for any LLM provider

## 🐛 Troubleshooting

### Issue: "pip is not recognized"
**Solution**: Make sure Python is installed and added to PATH

### Issue: "streamlit: command not found"
**Solution**: Ensure virtual environment is activated and dependencies are installed

### Issue: "No data in dashboard"
**Solution**: Run the demo first: `python examples\demo.py`

### Issue: "Import errors"
**Solution**: Make sure you're in the project root directory

## 📚 Next Steps

1. **Read the Full README**: `README.md` has comprehensive documentation
2. **Try the Tutorial Notebook**: Interactive learning experience
3. **Integrate with Real APIs**: Add your OpenAI API key and test with real calls
4. **Customize**: Modify prompts, thresholds, and features for your use case

## 🎉 You're Ready!

You now have a fully functional Telemetry-Aware Model Monitoring system!

**Questions?** Refer to:
- `README.md` - Complete documentation
- `examples\tutorial.ipynb` - Interactive tutorial
- `examples\openai_integration.py` - Real API integration examples

**Good luck with your presentation! 🚀**
