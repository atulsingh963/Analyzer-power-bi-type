from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from frontend.components.charts import render_chart
from database.db import SessionLocal
from backend.models.models import Dashboard, Widget, Dataset
from analytics.engine import analytics_engine

@ui.page('/dashboard_builder')
@require_nicegui_auth
def dashboard_builder_page(id: int = None):
    if id is None:
        ui.navigate.to("/dashboards")
        return
        
    db = SessionLocal()
    dashboard = db.query(Dashboard).filter_by(id=id).first()
    datasets = db.query(Dataset).all()
    db.close()
    
    if not dashboard:
        ui.notify("Error: Dashboard not found.", type='negative')
        ui.navigate.to("/dashboards")
        return
        
    # Options list for form
    ds_options = {d.id: d.name for d in datasets}
    
    # State values for Add Widget modal
    new_w_name = ""
    new_w_type = "bar"
    selected_ds_id = list(ds_options.keys())[0] if ds_options else None
    selected_x_col = ""
    selected_y_col = ""
    custom_sql = ""
    use_custom_sql = False
    
    # Dialog component references
    add_dialog = None
    widgets_grid = None
    
    # Form element references
    x_col_select = None
    y_col_select = None
    sql_input = None
    auto_form_container = None
    
    def refresh_builder_workspace():
        db_sess = SessionLocal()
        # Reload dashboard with widgets
        current_d = db_sess.query(Dashboard).filter_by(id=id).first()
        widgets = current_d.widgets if current_d else []
        db_sess.close()
        
        widgets_grid.clear()
        with widgets_grid:
            if not widgets:
                with ui.column().classes('w-full items-center justify-center q-pa-xl bg-gray-900/10 border border-dashed border-gray-800 rounded-lg'):
                    ui.icon('space_dashboard', size='48px', color='gray-600')
                    ui.label("This dashboard has no widgets. Click 'Add Widget' to design one!").classes('text-gray-400 text-body1 q-mt-sm')
                return
                
            for w in widgets:
                # Render widget inside a card
                with ui.card().classes('glass-card q-pa-md flex flex-col justify-between').style('width: 480px; min-height: 400px;'):
                    with ui.row().classes('w-full justify-between items-center q-mb-md'):
                        ui.label(w.name).classes('text-subtitle1 font-bold text-white')
                        ui.button(icon='delete', on_click=lambda target_w=w: delete_widget_flow(target_w)).props('flat dense color=red-4')
                        
                    # Execute widget query and draw chart
                    db_conn = SessionLocal()
                    success, cols, data, err = execute_widget_query(w, db_conn)
                    db_conn.close()
                    
                    if not success:
                        ui.label(f"Query Error: {err}").classes('text-red-400 text-caption bg-red-950/20 q-pa-sm rounded')
                    else:
                        with ui.column().classes('w-full items-center justify-center grow'):
                            render_chart(columns=cols, data=data, chart_type=w.type)

    def execute_widget_query(widget: Widget, db: SessionLocal) -> tuple:
        """
        Runs the query config in the widget and returns (success, columns, data, error_message).
        """
        qc = widget.query_config or {}
        
        # 1. Custom SQL Query execution
        if qc.get("use_custom_sql") or "custom_sql" in qc:
            sql = qc.get("custom_sql")
            res = analytics_engine.execute_query(sql, db)
            if res["success"]:
                return True, res["columns"], res["data"], None
            else:
                return False, None, None, res["error"]
                
        # 2. Automated Column Builder query execution
        ds_id = qc.get("dataset_id")
        x_col = qc.get("x_col")
        y_col = qc.get("y_col")
        
        if not ds_id or not x_col or not y_col:
            return False, None, None, "Widget configuration details are incomplete."
            
        dataset = db.query(Dataset).filter_by(id=ds_id).first()
        if not dataset:
            return False, None, None, f"Source dataset {ds_id} not found."
            
        # Compile SQL query based on chart columns
        table_name = dataset.name.lower().replace(" ", "_").replace("-", "_")
        
        # Simple grouping aggregation for standard visuals
        if widget.type == "kpi":
            sql = f"SELECT '{x_col}' AS metric, SUM({y_col}) AS total FROM {table_name}"
        else:
            sql = f"SELECT {x_col}, SUM({y_col}) AS total FROM {table_name} GROUP BY {x_col} ORDER BY total DESC"
            
        res = analytics_engine.execute_query(sql, db)
        if res["success"]:
            return True, res["columns"], res["data"], None
        else:
            return False, None, None, res["error"]

    def on_modal_source_change(e):
        nonlocal selected_ds_id
        selected_ds_id = e.value
        db_s = SessionLocal()
        ds = db_s.query(Dataset).filter_by(id=selected_ds_id).first()
        db_s.close()
        
        cols = []
        if ds and ds.schema_info:
            cols = [c["name"] for c in ds.schema_info.get("columns", [])]
            
        x_col_select.set_options(cols)
        y_col_select.set_options(cols)

    def toggle_sql_mode(e):
        nonlocal use_custom_sql
        use_custom_sql = e.value
        auto_form_container.set_visibility(not use_custom_sql)
        sql_input.set_visibility(use_custom_sql)

    def save_widget():
        nonlocal new_w_name, new_w_type, selected_ds_id, selected_x_col, selected_y_col, custom_sql, use_custom_sql
        
        name = new_w_name.strip()
        if not name:
            ui.notify("Error: Widget Name is required.", type='negative')
            return
            
        if use_custom_sql:
            sql = custom_sql.strip()
            if not sql:
                ui.notify("Error: SQL query is required in custom mode.", type='negative')
                return
            query_config = {
                "use_custom_sql": True,
                "custom_sql": sql
            }
        else:
            if not selected_ds_id or not selected_x_col or not selected_y_col:
                ui.notify("Error: Dataset and Axis columns must be selected.", type='negative')
                return
            query_config = {
                "use_custom_sql": False,
                "dataset_id": int(selected_ds_id),
                "x_col": selected_x_col,
                "y_col": selected_y_col
            }
            
        db_sess = SessionLocal()
        new_w = Widget(
            dashboard_id=id,
            name=name,
            type=new_w_type,
            query_config=query_config,
            visual_config={}
        )
        db_sess.add(new_w)
        # Update dashboard version
        dash = db_sess.query(Dashboard).filter_by(id=id).first()
        if dash:
            dash.version += 1
        db_sess.commit()
        db_sess.close()
        
        add_dialog.close()
        ui.notify(f"Widget '{name}' added successfully!", type='positive')
        refresh_builder_workspace()

    def delete_widget_flow(w: Widget):
        async def confirm():
            db_session = SessionLocal()
            target = db_session.query(Widget).filter_by(id=w.id).first()
            if target:
                db_session.delete(target)
                dash = db_session.query(Dashboard).filter_by(id=id).first()
                if dash:
                    dash.version += 1
                db_session.commit()
            db_session.close()
            ui.notify(f"Deleted widget '{w.name}'", type='warning')
            dialog.close()
            refresh_builder_workspace()
            
        with ui.dialog() as dialog, ui.card().classes('q-pa-lg glass-panel'):
            ui.label(f"Delete Widget '{w.name}'?").classes('text-h6 text-white font-bold')
            ui.label("This action cannot be undone.").classes('text-body2 text-gray-400')
            with ui.row().classes('w-full justify-end gap-sm q-mt-md'):
                ui.button('Cancel', on_click=dialog.close).props('flat color=white')
                ui.button('Confirm Delete', on_click=confirm).props('flat color=red')
        dialog.open()

    with Layout(f"Builder — {dashboard.name}"):
        # Header breadcrumbs and actions
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                with ui.row().classes('items-center gap-xs'):
                    ui.button(icon='arrow_back', on_click=lambda: ui.navigate.to('/dashboards')).props('flat dense color=indigo-3')
                    ui.label(dashboard.name).classes('text-h4 font-bold text-white')
                ui.label(dashboard.description or "Report workspace builder").classes('text-caption text-gray-400 q-pl-md')
                
            ui.button('Add Widget', on_click=lambda: add_dialog.open(), icon='add_chart').classes('bg-gradient-primary text-white font-bold rounded-lg').style('text-transform: none !important;')
            
        # Dialog Modal for adding widget
        with ui.dialog() as add_dialog:
            with ui.card().classes('q-pa-lg glass-panel').style('width: 500px; max-width: 95%;'):
                ui.label("Add Dashboard Widget").classes('text-h6 text-white font-bold q-mb-md')
                
                # Event binding helpers
                def set_wname(val):
                    nonlocal new_w_name
                    new_w_name = val
                    
                def set_wtype(val):
                    nonlocal new_w_type
                    new_w_type = val
                    
                def set_x(val):
                    nonlocal selected_x_col
                    selected_x_col = val
                    
                def set_y(val):
                    nonlocal selected_y_col
                    selected_y_col = val
                    
                def set_sql(val):
                    nonlocal custom_sql
                    custom_sql = val

                # Name
                name_el = ui.input(
                    label="Widget Title",
                    on_change=lambda e: set_wname(e.value)
                ).classes('w-full q-mb-sm').props('outlined dark color=indigo')
                
                # Chart Type
                type_el = ui.select(
                    options={"kpi": "KPI Value", "bar": "Bar Chart", "line": "Line Chart", "pie": "Pie Chart", "table": "Table View"},
                    value=new_w_type,
                    label="Visualization Type",
                    on_change=lambda e: set_wtype(e.value)
                ).classes('w-full q-mb-sm').props('outlined dark color=indigo')
                
                # Custom SQL Toggle
                sql_toggle = ui.switch(
                    "Custom SQL Query mode",
                    on_change=toggle_sql_mode
                ).classes('q-mb-md text-white')
                
                # Automated Builder Forms
                with ui.column().classes('w-full q-mb-md') as auto_form_container:
                    if not ds_options:
                        ui.label("No source datasets to configure. Add one in settings.").classes('text-red-400 text-caption')
                    else:
                        ds_select = ui.select(
                            options=ds_options,
                            value=selected_ds_id,
                            label="Dataset Source",
                            on_change=on_modal_source_change
                        ).classes('w-full q-mb-xs').props('outlined dark color=indigo dense')
                        
                        with ui.row().classes('w-full gap-sm'):
                            x_col_select = ui.select(
                                options=[],
                                label="X Axis (Labels / Cohorts)",
                                on_change=lambda e: set_x(e.value)
                            ).classes('col').props('outlined dark color=indigo dense')
                            
                            y_col_select = ui.select(
                                options=[],
                                label="Y Axis (Metric values sum)",
                                on_change=lambda e: set_y(e.value)
                            ).classes('col').props('outlined dark color=indigo dense')
                            
                # Custom SQL input field (hidden by default)
                sql_input = ui.textarea(
                    label="DuckDB SQL Statement",
                    placeholder="e.g. SELECT store_name, SUM(sales_amount) FROM store_sales GROUP BY 1",
                    on_change=lambda e: set_sql(e.value)
                ).classes('w-full q-mb-md').props('outlined dark color=indigo').style('display: none;')
                
                # Save button row
                with ui.row().classes('w-full justify-end gap-sm q-mt-md'):
                    ui.button('Cancel', on_click=add_dialog.close).props('flat color=white')
                    ui.button('Add Widget', on_click=save_widget).classes('bg-gradient-primary text-white font-bold').style('text-transform: none !important;')
                    
        # Grid layout for visual workspace
        widgets_grid = ui.row().classes('w-full gap-md q-py-md items-start justify-start')
        
        # Populate column options if defaults exist
        if selected_ds_id:
            on_modal_source_change(type('Obj', (object,), {'value': selected_ds_id}))
            
        # Refresh widgets list
        refresh_builder_workspace()
