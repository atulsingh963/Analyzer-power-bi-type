from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from backend.models.models import Dashboard, Workspace

@ui.page('/dashboards')
@require_nicegui_auth
def dashboard_center_page():
    # Dialog configuration references
    create_dialog = None
    dashboard_grid = None
    
    # State values
    new_name = ""
    new_desc = ""
    
    def refresh_dashboards_grid():
        db = SessionLocal()
        dashboards = db.query(Dashboard).all()
        db.close()
        
        dashboard_grid.clear()
        with dashboard_grid:
            if not dashboards:
                ui.label("No dashboards found. Build one to get started!").classes('text-gray-400 q-pa-lg text-body1')
                return
                
            for d in dashboards:
                with ui.card().classes('glass-card q-pa-lg flex flex-col justify-between').style('width: 320px; height: 220px;'):
                    # Icon + Details
                    with ui.column().classes('gap-xs w-full'):
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.avatar(icon='space_dashboard', color='indigo-950/50', text_color='indigo-400', size='32px')
                            ui.badge(f"v{d.version}", color='indigo')
                            
                        ui.label(d.name).classes('text-h6 font-bold text-white q-mt-xs text-ellipsis overflow-hidden').style('white-space: nowrap;')
                        ui.label(d.description or "No description provided.").classes('text-caption text-gray-400 text-ellipsis overflow-hidden').style('display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; height: 36px; white-space: normal;')
                        
                    # Action Buttons
                    with ui.row().classes('w-full justify-between items-center border-t border-gray-800/40 q-pt-md q-mt-auto'):
                        ui.button('Open Builder', on_click=lambda d_id=d.id: ui.navigate.to(f'/dashboard_builder?id={d_id}')).classes('bg-indigo-650 text-white font-bold text-caption').style('text-transform: none !important; border-radius: 6px;')
                        ui.button(icon='delete', on_click=lambda target_d=d: delete_dashboard_flow(target_d)).props('flat dense color=red-4')

    def save_dashboard():
        nonlocal new_name, new_desc
        name = new_name.strip()
        desc = new_desc.strip()
        
        if not name:
            ui.notify("Error: Dashboard Name is required.", type='negative')
            return
            
        db = SessionLocal()
        # Fetch first available workspace
        ws = db.query(Workspace).first()
        ws_id = ws.id if ws else 1
        
        new_d = Dashboard(
            name=name,
            description=desc,
            workspace_id=ws_id,
            is_shared=True,
            layout={},
            version=1
        )
        db.add(new_d)
        db.commit()
        d_id = new_d.id
        db.close()
        
        create_dialog.close()
        ui.notify(f"Dashboard '{name}' created successfully!", type='positive')
        
        # Navigate directly to the builder
        ui.navigate.to(f'/dashboard_builder?id={d_id}')

    def delete_dashboard_flow(d: Dashboard):
        async def confirm():
            db_session = SessionLocal()
            target = db_session.query(Dashboard).filter_by(id=d.id).first()
            if target:
                db_session.delete(target)
                db_session.commit()
            db_session.close()
            ui.notify(f"Deleted dashboard '{d.name}'", type='warning')
            dialog.close()
            refresh_dashboards_grid()
            
        with ui.dialog() as dialog, ui.card().classes('q-pa-lg glass-panel'):
            ui.label(f"Delete Dashboard '{d.name}'?").classes('text-h6 text-white font-bold')
            ui.label("This deletes the dashboard and all its widgets permanently.").classes('text-body2 text-gray-400')
            with ui.row().classes('w-full justify-end gap-sm q-mt-md'):
                ui.button('Cancel', on_click=dialog.close).props('flat color=white')
                ui.button('Confirm Delete', on_click=confirm).props('flat color=red')
        dialog.open()

    with Layout("Dashboards"):
        # Header info
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("Analytical Reports").classes('text-h4 font-bold text-white')
                ui.label("Build multi-widget dashboards and configure layout grids.").classes('text-caption text-gray-400')
            ui.button('Create Dashboard', on_click=lambda: create_dialog.open(), icon='add').classes('bg-gradient-primary text-white font-bold rounded-lg').style('text-transform: none !important;')
            
        # Dialog modal for dashboard creation
        with ui.dialog() as create_dialog:
            with ui.card().classes('q-pa-lg glass-panel').style('width: 440px; max-width: 90%;'):
                ui.label("Create New Dashboard").classes('text-h6 text-white font-bold q-mb-md')
                
                # Bind values
                def update_name(val):
                    nonlocal new_name
                    new_name = val
                    
                def update_desc(val):
                    nonlocal new_desc
                    new_desc = val
                    
                name_input = ui.input(
                    label="Name",
                    on_change=lambda e: update_name(e.value)
                ).classes('w-full q-mb-sm').props('outlined dark color=indigo')
                
                desc_input = ui.input(
                    label="Description (Optional)",
                    on_change=lambda e: update_desc(e.value)
                ).classes('w-full q-mb-md').props('outlined dark color=indigo')
                
                with ui.row().classes('w-full justify-end gap-sm q-mt-md'):
                    ui.button('Cancel', on_click=create_dialog.close).props('flat color=white')
                    ui.button('Create & Build', on_click=save_dashboard).classes('bg-gradient-primary text-white font-bold').style('text-transform: none !important;')
                    
        # Grid container of cards
        dashboard_grid = ui.row().classes('w-full gap-md q-py-md')
        
        # Initialize
        refresh_dashboards_grid()
