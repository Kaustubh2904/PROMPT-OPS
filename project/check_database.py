"""
Quick script to check database status and contents
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database import db_manager, TelemetryLog, PromptVersion, Alert
from config import settings

def check_database():
    """Check database location and contents."""
    print("=" * 60)
    print("📊 DATABASE STATUS CHECK")
    print("=" * 60)
    
    # Show database location
    db_url = settings.database_url
    print(f"\n📂 Database URL: {db_url}")
    
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
        if os.path.exists(db_path):
            print(f"✅ Database file exists at: {os.path.abspath(db_path)}")
            file_size = os.path.getsize(db_path)
            print(f"📦 Database size: {file_size:,} bytes ({file_size/1024:.2f} KB)")
        else:
            print(f"❌ Database file not found at: {os.path.abspath(db_path)}")
            print("   Run demo.py to create and populate the database")
            return
    
    # Check table contents
    print("\n" + "=" * 60)
    print("📊 TABLE CONTENTS")
    print("=" * 60)
    
    with db_manager.session_scope() as session:
        # Telemetry Logs
        log_count = session.query(TelemetryLog).count()
        print(f"\n📝 Telemetry Logs: {log_count:,} records")
        
        if log_count > 0:
            recent_log = session.query(TelemetryLog).order_by(
                TelemetryLog.timestamp.desc()
            ).first()
            print(f"   Latest log: {recent_log.model_name} at {recent_log.timestamp}")
            print(f"   Models tracked: ", end="")
            models = session.query(TelemetryLog.model_name).distinct().all()
            print(", ".join([m[0] for m in models]))
        
        # Prompt Versions
        prompt_count = session.query(PromptVersion).count()
        print(f"\n🔄 Prompt Versions: {prompt_count:,} records")
        
        if prompt_count > 0:
            prompts = session.query(PromptVersion.prompt_id).distinct().all()
            print(f"   Unique prompts: {len(prompts)}")
            for p in prompts:
                versions = session.query(PromptVersion).filter(
                    PromptVersion.prompt_id == p[0]
                ).count()
                print(f"   - {p[0]}: {versions} version(s)")
        
        # Alerts
        alert_count = session.query(Alert).count()
        active_alerts = session.query(Alert).filter(Alert.is_resolved == False).count()
        print(f"\n🚨 Alerts: {alert_count:,} total ({active_alerts} active)")
    
    print("\n" + "=" * 60)
    print("✅ Database check complete!")
    print("=" * 60)
    print("\n💡 Tips:")
    print("  - Run 'python examples/demo.py' to generate sample data")
    print("  - Run 'streamlit run dashboard/app.py' to view the dashboard")
    print("  - Both scripts now use the same database file")


if __name__ == "__main__":
    check_database()
