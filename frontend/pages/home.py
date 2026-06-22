from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from sqlalchemy.orm import joinedload
from backend.models.models import Dataset, Dashboard, User, AuditLog, AIInsight
from analytics.engine import analytics_engine

@ui.page('/home')
@require_nicegui_auth
def home_page():
    db = SessionLocal()
    try:
        num_datasets = db.query(Dataset).count()
        num_dashboards = db.query(Dashboard).count()
        num_users = db.query(User).count()
        
        # Inquire total store sales rows
        res = analytics_engine.execute_query("SELECT COUNT(*) FROM store_sales", db)
        total_rows = res["data"][0][0] if res["success"] and res["data"] else 0
        
        # Load recents
        dashboards = db.query(Dashboard).limit(3).all()
        
        # Load dynamic insights
        ai_insights = db.query(AIInsight).limit(3).all()
        if not ai_insights:
            # Seed default if empty
            ai_insights = [
                AIInsight(title="New Sales Peak", content="Electronics segment sales grew by 15.4% yesterday.", category="opportunity"),
                AIInsight(title="Bounce Rate Alert", content="Mobile sessions show high bounce rates on product pages.", category="risk")
            ]
            
        # Inquire system activity feed & recent queries from logs
        activity_logs = db.query(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.timestamp.desc()).limit(4).all()
        
    except Exception as e:
        print(f"Error loading home data: {e}")
        num_datasets, num_dashboards, num_users, total_rows = 0, 0, 0, 0
        dashboards, ai_insights, activity_logs = [], [], []
    finally:
        db.close()
        
    with Layout("Overview"):
        # Executive Welcome Banner
        with ui.card().classes('w-full q-pa-xl bg-gradient-primary text-white relative-position overflow-hidden shadow-2xl rounded-2xl').style('border: none;'):
            with ui.column().classes('gap-xs z-10 relative'):
                ui.label("Analyzer Analytics Platform").classes('text-h3 font-black tracking-tight')
                ui.label("Study insights, run visual ETL flows, or ask the AI Copilot to analyze transactional databases.").classes('text-subtitle1 text-indigo-100/90')
            # Decorative radial glow behind banner text
            ui.element('div').style('position: absolute; right: -50px; top: -50px; width: 300px; height: 300px; background: radial-gradient(circle, rgba(236,72,153,0.3) 0%, transparent 70%); pointer-events: none;')
            
        # Grid layout for KPIs
        with ui.row().classes('w-full gap-md q-mt-md items-stretch'):
            kpi_card("Connected Data", str(num_datasets), "folder", "text-indigo-400")
            kpi_card("Analytical Dashboards", str(num_dashboards), "dashboard", "text-purple-400")
            kpi_card("SaaS Profiles", str(num_users), "people", "text-cyan-400")
            kpi_card("Lakehouse Row Count", f"{total_rows:,}", "storage", "text-emerald-400")
            
        # Main Dashboard Workspace
        with ui.row().classes('w-full gap-lg items-stretch q-mt-lg'):
            # Left Column: Recent Dashboards & Activity Feed
            with ui.column().classes('gap-lg').style('flex: 2; min-width: 450px;'):
                # Recent Dashboards
                with ui.column().classes('glass-panel q-pa-lg w-full'):
                    ui.label("My Recent Reports").classes('text-h5 font-bold text-gradient q-mb-md')
                    if not dashboards:
                        ui.label("No dashboards configured yet. Start building inside Report Workspace.").classes('text-gray-400 text-body2')
                    else:
                        with ui.column().classes('w-full gap-sm'):
                            for d in dashboards:
                                with ui.row().classes('w-full items-center justify-between q-pa-md border border-gray-800/20 hover:border-indigo-500/40 rounded-lg hover:bg-gray-800/10 transition-all'):
                                    with ui.row().classes('items-center gap-md'):
                                        ui.avatar(icon='space_dashboard', color='indigo-950/40', text_color='indigo-400', size='36px')
                                        with ui.column().classes('gap-none'):
                                            ui.label(d.name).classes('text-subtitle2 font-bold')
                                            ui.label(f"Version {d.version}").classes('text-caption text-gray-500')
                                    ui.button('Open Report', on_click=lambda d_id=d.id: ui.navigate.to(f'/dashboard_builder?id={d_id}')).props('flat dense size=sm color=indigo')
                                    
                # Recent SQL Queries
                with ui.column().classes('glass-panel q-pa-lg w-full'):
                    ui.label("Direct Lakehouse Queries").classes('text-h5 font-bold text-gradient q-mb-md')
                    # List typical DuckDB analytical queries
                    queries = [
                        "SELECT date, SUM(sales_amount) FROM store_sales GROUP BY 1 ORDER BY 1",
                        "SELECT product_category, SUM(sales_amount) FROM store_sales GROUP BY 1",
                        "SELECT store_location, AVG(customer_age) FROM store_sales GROUP BY 1",
                        "SELECT referrer_channel, COUNT(*) FROM web_metrics GROUP BY 1"
                    ]
                    with ui.column().classes('w-full gap-sm'):
                        for q in queries:
                            with ui.row().classes('w-full items-center justify-between q-pa-sm border-b border-gray-800/20 bg-gray-900/10 rounded px-md'):
                                ui.label(q).classes('text-caption font-mono text-indigo-300 text-ellipsis overflow-hidden').style('max-width: 80%; white-space: nowrap;')
                                ui.button('Run SQL', on_click=lambda query_sql=q: ui.navigate.to(f'/ask?q={query_sql}')).props('flat size=sm color=indigo icon=play_arrow')
                                
            # Right Column: AI Insights & System Log
            with ui.column().classes('gap-lg').style('flex: 1; min-width: 300px;'):
                # AI Insights Card
                with ui.column().classes('glass-panel q-pa-lg w-full'):
                    ui.label("Automated AI Insights").classes('text-h5 font-bold text-gradient q-mb-md')
                    with ui.column().classes('w-full gap-md'):
                        for ins in ai_insights:
                            color = "red-400" if ins.category == "risk" else "emerald-400" if ins.category == "opportunity" else "indigo-400"
                            border_color = "red-500" if ins.category == "risk" else "emerald-500" if ins.category == "opportunity" else "indigo-500"
                            with ui.card().classes(f'w-full q-pa-md border-l-4 border-{border_color}').style('background: rgba(30,41,59,0.3) !important; border-radius: 8px;'):
                                ui.label(ins.title).classes(f'text-subtitle2 font-bold {color}')
                                ui.label(ins.content).classes('text-caption text-gray-300')
                                
                # Audit Logs Activity Feed
                with ui.column().classes('glass-panel q-pa-lg w-full'):
                    ui.label("Live Audit Activity").classes('text-h5 font-bold text-gradient q-mb-md')
                    if not activity_logs:
                        ui.label("No recent system activities.").classes('text-gray-500 text-caption')
                    else:
                        with ui.column().classes('w-full gap-md'):
                            for log in activity_logs:
                                with ui.row().classes('w-full items-start gap-sm'):
                                    ui.avatar(icon='history', color='gray-800', size='24px')
                                    with ui.column().classes('gap-none col'):
                                        ui.label(log.action).classes('text-caption font-bold')
                                        u_name = log.user.username if log.user else "System"
                                        ui.label(f"{u_name} • {log.timestamp.strftime('%H:%M') if log.timestamp else ''}").classes('text-caption text-gray-500')

def kpi_card(title: str, value: str, icon: str, text_color: str):
    with ui.card().classes('glass-card q-pa-lg items-center justify-between col').style('min-width: 200px;'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label(title).classes('text-caption text-gray-400 font-bold uppercase tracking-wider')
            ui.avatar(icon=icon, color='indigo-950/30', text_color='indigo-400', size='32px')
        ui.label(value).classes(f'text-h4 font-black {text_color} q-mt-xs')
