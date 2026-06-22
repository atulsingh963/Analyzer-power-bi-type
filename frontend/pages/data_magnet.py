from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from backend.models.models import Dataset, ETLJob
from etl.engine import etl_engine

@ui.page('/etl')
@require_nicegui_auth
def data_magnet_page():
    # Load source dataset options
    db = SessionLocal()
    try:
        datasets = db.query(Dataset).all()
    except Exception:
        datasets = []
    finally:
        db.close()
        
    ds_options = {d.id: d.name for d in datasets}
    
    # State values
    selected_source_id = list(ds_options.keys())[0] if ds_options else None
    filter_op = ">"
    filter_val = ""
    pipeline_name = "Clean Analytical Table"
    agg_func = "sum"
    
    # UI Element References
    filter_col_select = None
    agg_col_select = None
    select_cols_select = None
    groupby_cols_select = None
    summary_label = None
    canvas_row = None
    
    def on_source_change(e):
        nonlocal selected_source_id
        selected_source_id = e.value
        db_sess = SessionLocal()
        try:
            ds = db_sess.query(Dataset).filter_by(id=selected_source_id).first()
        except Exception:
            ds = None
        db_sess.close()
        
        cols = []
        if ds and ds.schema_info:
            cols = [c["name"] for c in ds.schema_info.get("columns", [])]
            
        filter_col_select.set_options(cols)
        agg_col_select.set_options(cols)
        select_cols_select.set_options(cols)
        groupby_cols_select.set_options(cols)
        update_summary()

    def draw_node(label: str, icon: str, active: bool):
        border = "border-indigo-500/80" if active else "border-gray-800/40"
        text = "text-white" if active else "text-gray-600"
        glow = "box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);" if active else ""
        with ui.card().classes(f'q-pa-md flex flex-row items-center gap-sm border {border}').style(f'background: rgba(30,41,59,0.4) !important; border-radius: 30px; {glow}'):
            ui.icon(icon, color='indigo-400' if active else 'gray-600', size='24px')
            ui.label(label).classes(f'text-caption font-bold {text}')

    def update_summary():
        # 1. Update text summary steps
        steps = []
        is_filter_active = False
        is_select_active = False
        is_groupby_active = False
        
        if selected_source_id:
            steps.append(f"1. Read raw source: **{ds_options.get(selected_source_id)}**")
        if filter_col_select and filter_col_select.value and filter_val:
            steps.append(f"2. Filter records where **{filter_col_select.value} {filter_op} {filter_val}**")
            is_filter_active = True
        if select_cols_select and select_cols_select.value:
            steps.append(f"3. Retain columns: **{', '.join(select_cols_select.value)}**")
            is_select_active = True
        if groupby_cols_select and groupby_cols_select.value and agg_col_select and agg_col_select.value:
            steps.append(f"4. Group by **{', '.join(groupby_cols_select.value)}** (aggregate: **{agg_func.upper()}** of **{agg_col_select.value}**)")
            is_groupby_active = True
            
        summary_content = "\n".join([f"* {s}" for s in steps]) if steps else "*Configure source dataset to view transformation steps.*"
        summary_label.set_content(summary_content)
        
        # 2. Update visual node canvas highlights
        canvas_row.clear()
        with canvas_row:
            draw_node("Source Ingestion", "cloud_download", selected_source_id is not None)
            ui.icon('arrow_forward', color='indigo-400' if is_filter_active else 'gray-700', size='24px')
            
            draw_node("Filter Records", "filter_alt", is_filter_active)
            ui.icon('arrow_forward', color='indigo-400' if is_select_active else 'gray-700', size='24px')
            
            draw_node("Select Columns", "view_column", is_select_active)
            ui.icon('arrow_forward', color='indigo-400' if is_groupby_active else 'gray-700', size='24px')
            
            draw_node("Group Aggregates", "functions", is_groupby_active)
            ui.icon('arrow_forward', color='indigo-400' if pipeline_name else 'gray-700', size='24px')
            
            draw_node("Lakehouse Target", "storage", bool(pipeline_name.strip()))

    def run_pipeline():
        if not selected_source_id:
            ui.notify("Error: Source dataset is required.", type='negative')
            return
            
        if not pipeline_name.strip():
            ui.notify("Error: Output dataset name is required.", type='negative')
            return
            
        nodes = [
            {
                "id": "node_source",
                "type": "source",
                "config": {"dataset_id": int(selected_source_id)}
            }
        ]
        
        if filter_col_select.value and filter_val.strip():
            nodes.append({
                "id": "node_filter",
                "type": "filter",
                "config": {
                    "column": filter_col_select.value,
                    "operator": filter_op,
                    "value": filter_val.strip()
                }
            })
            
        if select_cols_select.value:
            nodes.append({
                "id": "node_select",
                "type": "select",
                "config": {"columns": select_cols_select.value}
            })
            
        if groupby_cols_select.value and agg_col_select.value:
            nodes.append({
                "id": "node_groupby",
                "type": "groupby",
                "config": {
                    "groupby_cols": groupby_cols_select.value,
                    "agg_col": agg_col_select.value,
                    "agg_func": agg_func
                }
            })
            
        definition = {"nodes": nodes}
        
        db_sess = SessionLocal()
        try:
            new_job = ETLJob(
                name=pipeline_name.strip(),
                definition=definition,
                status="Idle"
            )
            db_sess.add(new_job)
            db_sess.commit()
            job_id = new_job.id
        except Exception as e:
            ui.notify(f"DB Error: {e}", type='negative')
            db_sess.close()
            return
        db_sess.close()
        
        ui.notify("Starting Polars ETL job execution...", type='info')
        res = etl_engine.run_job(job_id)
        
        if res.get("success"):
            ui.notify(f"Polars Pipeline executed! Output dataset '{pipeline_name}' ({res.get('rows')} rows) saved as Parquet.", type='positive')
            ui.navigate.to("/settings")
        else:
            ui.notify(f"ETL Failure: {res.get('error')}", type='negative')

    with Layout("Visual ETL Ingestion"):
        # Header Info
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("Visual ETL Canvas").classes('text-h4 font-bold text-white')
                ui.label("Ingest raw data sources, filter records, select groupings, and save outputs to the Parquet Lakehouse.").classes('text-caption text-gray-400')

        # 1. Flow Ingestion Canvas Node sequence
        with ui.card().classes('w-full glass-panel q-pa-lg q-mb-lg items-center justify-center'):
            ui.label("ETL Ingestion Pipeline Canvas").classes('text-caption text-indigo-400 font-bold uppercase tracking-wider q-mb-md')
            canvas_row = ui.row().classes('items-center justify-center gap-md w-full q-py-sm overflow-x-auto')

        # 2. Main Builder Columns
        with ui.row().classes('w-full gap-lg items-stretch'):
            # Left panel: Configurations
            with ui.column().classes('glass-panel q-pa-lg').style('flex: 2; min-width: 400px;'):
                ui.label("Configure Transformations").classes('text-h5 font-bold text-white q-mb-md')
                
                # Step 1: Source Selection
                with ui.column().classes('w-full q-mb-md q-pa-md bg-gray-900/20 rounded-lg border border-gray-800/40'):
                    ui.label("Step 1: Source Lakehouse Dataset").classes('text-subtitle2 text-indigo-300 font-bold')
                    if not ds_options:
                        ui.label("No source datasets available. Upload CSV/Parquet files in System Configuration.").classes('text-red-400')
                    else:
                        ui.select(
                            options=ds_options,
                            value=selected_source_id,
                            label="Choose Source Dataset",
                            on_change=on_source_change
                        ).classes('w-full').props('outlined dark color=indigo dense')
                        
                # Step 2: Filters
                with ui.column().classes('w-full q-mb-md q-pa-md bg-gray-900/20 rounded-lg border border-gray-800/40'):
                    ui.label("Step 2: Filter Records (Optional)").classes('text-subtitle2 text-indigo-300 font-bold')
                    with ui.row().classes('w-full items-center gap-sm'):
                        filter_col_select = ui.select(
                            options=[],
                            label="Column",
                            on_change=lambda _: update_summary()
                        ).classes('col').props('outlined dark color=indigo dense')
                        
                        def set_op(val):
                            nonlocal filter_op
                            filter_op = val
                            update_summary()
                            
                        op_select = ui.select(
                            options=[">", "<", "==", "contains"],
                            value=">",
                            label="Operator",
                            on_change=lambda e: set_op(e.value)
                        ).classes('w-32').props('outlined dark color=indigo dense')
                        
                        def update_filter_val(val):
                            nonlocal filter_val
                            filter_val = val
                            update_summary()
                            
                        filter_val_input = ui.input(
                            label="Comparison Value",
                            on_change=lambda e: update_filter_val(e.value)
                        ).classes('col').props('outlined dark color=indigo dense')
                        
                # Step 3: Column Selection
                with ui.column().classes('w-full q-mb-md q-pa-md bg-gray-900/20 rounded-lg border border-gray-800/40'):
                    ui.label("Step 3: Columns Selection (Optional)").classes('text-subtitle2 text-indigo-300 font-bold')
                    select_cols_select = ui.select(
                        options=[],
                        label="Columns to keep (empty retains all)",
                        multiple=True,
                        on_change=lambda _: update_summary()
                    ).classes('w-full').props('outlined dark color=indigo dense use-chips')
                    
                # Step 4: Group By & Aggregation
                with ui.column().classes('w-full q-mb-md q-pa-md bg-gray-900/20 rounded-lg border border-gray-800/40'):
                    ui.label("Step 4: Group By & Aggregation (Optional)").classes('text-subtitle2 text-indigo-300 font-bold')
                    with ui.row().classes('w-full items-center gap-sm'):
                        groupby_cols_select = ui.select(
                            options=[],
                            label="Group By Columns",
                            multiple=True,
                            on_change=lambda _: update_summary()
                        ).classes('col').props('outlined dark color=indigo dense use-chips')
                        
                        agg_col_select = ui.select(
                            options=[],
                            label="Aggregate Column",
                            on_change=lambda _: update_summary()
                        ).classes('col').props('outlined dark color=indigo dense')
                        
                        def set_agg(val):
                            nonlocal agg_func
                            agg_func = val
                            update_summary()
                            
                        agg_func_select = ui.select(
                            options=["sum", "mean", "count", "max", "min"],
                            value="sum",
                            label="Function",
                            on_change=lambda e: set_agg(e.value)
                        ).classes('w-32').props('outlined dark color=indigo dense')
                        
            # Right panel: Summary Target & Execute
            with ui.column().classes('glass-panel q-pa-lg justify-start').style('flex: 1; min-width: 300px;'):
                ui.label("Pipeline Execution Summary").classes('text-h5 font-bold text-white q-mb-md')
                summary_label = ui.markdown("*Configure source dataset to view transformation steps.*").classes('text-body2 text-gray-300 q-mb-lg')
                
                ui.label("Save Options").classes('text-subtitle2 text-indigo-300 font-bold q-mb-xs')
                
                def set_pname(val):
                    nonlocal pipeline_name
                    pipeline_name = val
                    update_summary()
                    
                pname_input = ui.input(
                    label="Output Dataset Name",
                    value=pipeline_name,
                    on_change=lambda e: set_pname(e.value)
                ).classes('w-full q-mb-lg').props('outlined dark color=indigo dense')
                
                ui.button(
                    'Execute Pipeline', 
                    on_click=run_pipeline,
                    icon='play_arrow'
                ).classes('w-full bg-gradient-primary text-white font-bold q-py-sm rounded-lg hover-glow').style('text-transform: none !important;')
                
        # Trigger initial column load
        if selected_source_id:
            on_source_change(type('Obj', (object,), {'value': selected_source_id}))
