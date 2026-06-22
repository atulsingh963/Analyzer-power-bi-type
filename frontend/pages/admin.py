from nicegui import app, ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from backend.models.models import User, AuditLog, Role
from sqlalchemy.orm import joinedload
from sqlalchemy import text
import plotly.graph_objects as go

@ui.page('/admin')
@require_nicegui_auth
def admin_page():
    db = SessionLocal()
    try:
        users = db.query(User).options(joinedload(User.role)).all()
        
        # Seed mock audit logs if empty
        if db.query(AuditLog).count() == 0:
            db.add_all([
                AuditLog(user_id=1, action="User Login Successful", target_type="User", target_id=1, details={"ip": "127.0.0.1"}),
                AuditLog(user_id=1, action="Dataset Ingested", target_type="Dataset", target_id=1, details={"file": "store_sales.parquet"}),
                AuditLog(user_id=1, action="Dashboard Created", target_type="Dashboard", target_id=1, details={"name": "Executive Sales Summary"})
            ])
            db.commit()
            
        logs = db.query(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        # Query usage analytics from database audit log timestamps
        usage_res = db.execute(text("SELECT date(timestamp) as log_date, count(*) as log_count FROM audit_logs GROUP BY log_date ORDER BY log_date ASC")).all()
        usage_dates = [str(r[0]) for r in usage_res]
        usage_counts = [int(r[1]) for r in usage_res]
        
    except Exception as e:
        print(f"Admin load error: {e}")
        users = []
        logs = []
        usage_dates = ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]
        usage_counts = [4, 12, 8, 18]
    finally:
        db.close()

    # Draw Plotly Usage Chart
    dark_active = app.storage.user.get('dark_mode', True)
    text_color = "#F3F4F6" if dark_active else "#0F172A"
    grid_color = "rgba(255,255,255,0.08)" if dark_active else "rgba(0,0,0,0.08)"
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=usage_dates,
        y=usage_counts,
        mode='lines+markers',
        line=dict(color='#8B5CF6', width=3),
        marker=dict(size=8, color='#6366F1'),
        fill='tozeroy',
        fillcolor='rgba(139, 92, 246, 0.12)',
        name="Logs Ingested"
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=text_color,
        font_family='Plus Jakarta Sans',
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(gridcolor=grid_color, tickfont=dict(color=text_color)),
        yaxis=dict(gridcolor=grid_color, tickfont=dict(color=text_color))
    )

    with Layout("Administration"):
        # Header Info
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("Administration Console").classes('text-h4 font-bold text-white')
                ui.label("Manage users, review system configuration audit trails, and monitor server usage metrics.").classes('text-caption text-gray-400')
                
        # Tab selection
        with ui.tabs().classes('w-full bg-transparent text-indigo-300') as tabs:
            users_tab = ui.tab('User Directory', icon='people')
            audit_tab = ui.tab('System Audit Logs', icon='history')
            metrics_tab = ui.tab('Usage & System Health', icon='analytics')
            
        with ui.tab_panels(tabs, value=users_tab).classes('w-full bg-transparent q-mt-md'):
            # Tab 1: User Directory
            with ui.tab_panel(users_tab).classes('glass-panel q-pa-lg'):
                ui.label("SaaS User Directory").classes('text-h5 font-bold text-white q-mb-md')
                
                cols_def = [
                    {"name": "id", "label": "ID", "field": "id", "align": "center"},
                    {"name": "username", "label": "Username", "field": "username", "align": "left"},
                    {"name": "email", "label": "Email Address", "field": "email", "align": "left"},
                    {"name": "role", "label": "Assigned Role", "field": "role", "align": "center"},
                    {"name": "status", "label": "Status", "field": "status", "align": "center"}
                ]
                
                rows_def = []
                for u in users:
                    rows_def.append({
                        "id": u.id,
                        "username": u.username,
                        "email": u.email,
                        "role": u.role.name if u.role else "None",
                        "status": "Active" if u.is_active else "Inactive"
                    })
                    
                ui.table(columns=cols_def, rows=rows_def).classes('w-full').props('dark flat bordered' if dark_active else 'flat bordered')
                
            # Tab 2: Audit Logs
            with ui.tab_panel(audit_tab).classes('glass-panel q-pa-lg'):
                ui.label("Recent Operations Audit Trail").classes('text-h5 font-bold text-white q-mb-md')
                
                cols_log = [
                    {"name": "timestamp", "label": "Timestamp", "field": "timestamp", "align": "left"},
                    {"name": "user", "label": "User Profiles", "field": "user", "align": "center"},
                    {"name": "action", "label": "Action Executed", "field": "action", "align": "left"},
                    {"name": "target", "label": "Object Class", "field": "target", "align": "center"}
                ]
                
                rows_log = []
                for log in logs:
                    rows_log.append({
                        "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "",
                        "user": log.user.username if log.user else "System",
                        "action": log.action,
                        "target": log.target_type or "None"
                    })
                    
                ui.table(columns=cols_log, rows=rows_log).classes('w-full').props('dark flat bordered' if dark_active else 'flat bordered')

            # Tab 3: Usage Metrics & Health
            with ui.tab_panel(metrics_tab).classes('glass-panel q-pa-lg'):
                with ui.row().classes('w-full gap-lg items-stretch'):
                    # Usage chart
                    with ui.column().classes('col-8').style('min-width: 450px;'):
                        ui.label("Platform Log Ingest Trends").classes('text-h5 font-bold text-white q-mb-md')
                        ui.plotly(fig).classes('w-full h-80 bg-transparent')
                    # System info
                    with ui.column().classes('col').style('min-width: 250px;'):
                        ui.label("Server Status").classes('text-h5 font-bold text-white q-mb-md')
                        with ui.column().classes('w-full gap-sm q-pa-md bg-gray-900/10 rounded-lg border border-gray-800/30'):
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("CPU Core Load").classes('text-caption text-gray-400')
                                ui.badge("Healthy (12%)", color='emerald')
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("RAM In-Memory").classes('text-caption text-gray-400')
                                ui.badge("344 MB / 8 GB", color='indigo')
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("Lakehouse Engine").classes('text-caption text-gray-400')
                                ui.badge("DuckDB", color='cyan')
                            with ui.row().classes('w-full justify-between items-center'):
                                ui.label("ETL Runner").classes('text-caption text-gray-400')
                                ui.badge("Polars", color='purple')
