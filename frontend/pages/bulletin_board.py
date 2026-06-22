from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from backend.models.models import AIInsight

@ui.page('/bulletin_board')
@require_nicegui_auth
def bulletin_board_page():
    db = SessionLocal()
    try:
        # Check insights and seed if empty
        if db.query(AIInsight).count() == 0:
            db.add_all([
                AIInsight(dataset_id=1, title="Sales Volatility Alert — NY Store", content="New York Downtown experienced a 14.2% drop in transaction volume. Outliers fell below 1.5 IQR lower bound.", category="alert"),
                AIInsight(dataset_id=1, title="Expansion Opportunity — Apparel Group", content="Groceries category sales show positive correlation (+0.82) with customer age segments 35-48. Propose targeting regional promotions.", category="opportunity"),
                AIInsight(dataset_id=2, title="Bounce Rate Risk Indicator", content="Mobile visitors browsing `/products` have a bounce rate exceeding 68.2%, which is 22% higher than desktop.", category="risk")
            ])
            db.commit()
        insights = db.query(AIInsight).all()
    except Exception:
        insights = []
    finally:
        db.close()
        
    # Group items by executive category
    alerts = [ins for ins in insights if ins.category in ("alert", "risk")]
    opportunities = [ins for ins in insights if ins.category == "opportunity"]
    
    # Static forecast bulletin details ( Holt-Winters models )
    forecasts = [
        {
            "title": "30-Day Sales Forecast",
            "content": "Sales projections indicate a **9.4% revenue increase** across Electronics over the next quarter. Baseline Holt-Winters model parameters: alpha=0.3, beta=0.1, seasonal=30.",
            "conf_level": "95%"
        }
    ]
    
    recommendations = [
        {
            "title": "Data Magnet ETL Consolidation",
            "content": "Schedule duplicate checking ETL transformation workflows on the transactional Parquet storage weekly to optimize query performance in DuckDB.",
            "urgency": "Medium"
        }
    ]
    
    anomalies = [
        {
            "title": "Ingestion Row Duplication",
            "content": "ETL ingestion logs identified **247 duplicate rows** during the weekly metrics ingestion script execution on metrics dataset.",
            "severity": "Low"
        }
    ]
    
    with Layout("AI Bulletin Board"):
        # Header title
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("AI Bulletin Board & Insights Hub").classes('text-h4 font-bold text-white')
                ui.label("Executive summaries of system anomalies, segment risks, forecasting indicators, and recommendations.").classes('text-caption text-gray-400')
                
        # Main responsive flex layouts
        with ui.row().classes('w-full gap-md items-stretch'):
            # Column 1: Critical Alerts & Risks
            with ui.column().classes('col').style('min-width: 320px;'):
                ui.label("Critical Alerts & Risks").classes('text-subtitle1 text-red-400 font-bold uppercase tracking-wider q-mb-sm')
                if not alerts:
                    ui.label("No active alerts.").classes('text-caption text-gray-500')
                for a in alerts:
                    bulletin_card(a.title, a.content, "error", "border-red-500", "red-4")
                    
            # Column 2: Growth Opportunities
            with ui.column().classes('col').style('min-width: 320px;'):
                ui.label("Growth Opportunities").classes('text-subtitle1 text-emerald-400 font-bold uppercase tracking-wider q-mb-sm')
                if not opportunities:
                    ui.label("No opportunities detected.").classes('text-caption text-gray-500')
                for o in opportunities:
                    bulletin_card(o.title, o.content, "trending_up", "border-emerald-500", "emerald-4")
                    
            # Column 3: Predictions & Forecasts
            with ui.column().classes('col').style('min-width: 320px;'):
                ui.label("Forecasts & Projections").classes('text-subtitle1 text-cyan-400 font-bold uppercase tracking-wider q-mb-sm')
                for f in forecasts:
                    bulletin_card(f["title"], f["content"], "show_chart", "border-cyan-500", "cyan-4")
                    
        with ui.row().classes('w-full gap-md items-stretch q-mt-lg'):
            # Column 4: Actionable Recommendations
            with ui.column().classes('col').style('min-width: 480px;'):
                ui.label("System Recommendations").classes('text-subtitle1 text-purple-400 font-bold uppercase tracking-wider q-mb-sm')
                for r in recommendations:
                    bulletin_card(r["title"], r["content"], "lightbulb", "border-purple-500", "purple-4")
                    
            # Column 5: Statistics & Anomalies
            with ui.column().classes('col').style('min-width: 480px;'):
                ui.label("Lakehouse Statistical Anomalies").classes('text-subtitle1 text-yellow-400 font-bold uppercase tracking-wider q-mb-sm')
                for an in anomalies:
                    bulletin_card(an["title"], an["content"], "report_problem", "border-yellow-500", "yellow-4")

def bulletin_card(title: str, content: str, icon: str, border_class: str, icon_color: str):
    with ui.card().classes(f'glass-card w-full q-pa-lg border-l-4 {border_class} q-mb-md'):
        with ui.row().classes('w-full items-center justify-between q-mb-xs'):
            with ui.row().classes('items-center gap-sm'):
                ui.icon(icon, color=icon_color, size='24px')
                ui.label(title).classes('text-h6 text-white font-bold')
        ui.markdown(content).classes('text-body2 text-gray-300 q-pl-md')
