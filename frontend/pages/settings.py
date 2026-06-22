import os
import shutil
import polars as pl
from nicegui import ui, events
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal, LAKEHOUSE_DIR
from backend.models.models import Dataset, Workspace
from etl.quality import get_dataset_quality_metrics

@ui.page('/settings')
@require_nicegui_auth
def settings_page():
    db = SessionLocal()
    # Fetch datasets
    datasets = db.query(Dataset).all()
    workspaces = db.query(Workspace).all()
    ws_options = {w.id: w.name for w in workspaces}
    db.close()
    
    selected_workspace_id = list(ws_options.keys())[0] if ws_options else 1
    
    # State containers
    datasets_list_container = None
    schema_dialog = None
    quality_dialog = None
    
    def refresh_datasets_list():
        db_session = SessionLocal()
        ds_list = db_session.query(Dataset).all()
        db_session.close()
        
        datasets_list_container.clear()
        with datasets_list_container:
            if not ds_list:
                ui.label("No datasets registered yet.").classes('text-gray-400 q-pa-md')
                return
                
            for ds in ds_list:
                with ui.row().classes('w-full items-center justify-between q-py-md q-px-md border-b border-gray-800/40 hover:bg-gray-800/20 rounded-lg transition-colors'):
                    with ui.row().classes('items-center gap-md'):
                        ui.avatar(icon='insert_drive_file', color='indigo-950/40', text_color='indigo-400', size='36px')
                        with ui.column().classes('gap-none'):
                            ui.label(ds.name).classes('text-subtitle1 text-white font-medium')
                            ui.label(f"{ds.file_type.upper()} • {ds.file_path}").classes('text-caption text-gray-500')
                            
                    with ui.row().classes('items-center gap-xs'):
                        ui.button('Schema', on_click=lambda d=ds: show_schema(d)).props('flat dense color=indigo')
                        ui.button('Data Quality', on_click=lambda d=ds: show_quality(d)).props('flat dense color=pink')
                        ui.button('Delete', on_click=lambda d=ds: delete_dataset_flow(d)).props('flat dense color=red-4')

    async def handle_upload(e: events.UploadEventArguments):
        filename = e.name
        ext = os.path.splitext(filename)[1].lower()
        
        if ext not in (".csv", ".parquet"):
            ui.notify("Error: Only CSV and Parquet files are supported.", type='negative')
            return
            
        file_type = "parquet" if ext == ".parquet" else "csv"
        
        # Save file to raw directory
        save_dir = os.path.join(LAKEHOUSE_DIR, "raw")
        os.makedirs(save_dir, exist_ok=True)
        
        # Create safe filename
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (".", "_", "-")).strip()
        file_path = os.path.abspath(os.path.join(save_dir, safe_filename))
        
        try:
            # Read upload stream content
            content = e.content.read()
            with open(file_path, "wb") as f:
                f.write(content)
        except Exception as err:
            ui.notify(f"Error saving upload file: {str(err)}", type='negative')
            return
            
        # Parse schema info using Polars
        try:
            if file_type == "parquet":
                df = pl.read_parquet(file_path, n_rows=5)
            else:
                df = pl.read_csv(file_path, n_rows=5)
                
            columns = [{"name": col, "type": str(dtype)} for col, dtype in df.schema.items()]
            schema_info = {"columns": columns}
        except Exception as err:
            if os.path.exists(file_path):
                os.remove(file_path)
            ui.notify(f"Invalid file structure: {str(err)}", type='negative')
            return
            
        # Register in SQLite
        db_session = SessionLocal()
        new_ds = Dataset(
            name=os.path.splitext(filename)[0].replace("_", " ").title(),
            file_path=file_path,
            file_type=file_type,
            schema_info=schema_info,
            workspace_id=selected_workspace_id
        )
        db_session.add(new_ds)
        db_session.commit()
        db_session.close()
        
        ui.notify(f"Dataset '{filename}' successfully uploaded and registered!", type='positive')
        refresh_datasets_list()

    def delete_dataset_flow(ds: Dataset):
        async def confirm():
            db_session = SessionLocal()
            target = db_session.query(Dataset).filter_by(id=ds.id).first()
            if target:
                # Remove file from disk
                if os.path.exists(target.file_path):
                    try:
                        os.remove(target.file_path)
                    except Exception:
                        pass
                db_session.delete(target)
                db_session.commit()
            db_session.close()
            ui.notify(f"Deleted dataset '{ds.name}'", type='warning')
            d.close()
            refresh_datasets_list()
            
        with ui.dialog() as d, ui.card().classes('q-pa-lg glass-panel'):
            ui.label(f"Delete Dataset '{ds.name}'?").classes('text-h6 text-white font-bold')
            ui.label("This action is permanent and deletes the raw file from storage.").classes('text-body2 text-gray-400')
            with ui.row().classes('w-full justify-end gap-sm q-mt-md'):
                ui.button('Cancel', on_click=d.close).props('flat color=white')
                ui.button('Confirm Delete', on_click=confirm).props('flat color=red')
        d.open()

    def show_schema(ds: Dataset):
        schema_dialog.clear()
        with schema_dialog:
            with ui.card().classes('q-pa-lg glass-panel').style('width: 500px; max-width: 90%;'):
                ui.label(f"Schema Details: {ds.name}").classes('text-h6 text-white font-bold q-mb-md')
                
                # Table of columns
                columns = ds.schema_info.get("columns", []) if ds.schema_info else []
                if not columns:
                    ui.label("No schema information available.").classes('text-gray-400')
                else:
                    with ui.column().classes('w-full gap-sm'):
                        # Table header
                        with ui.row().classes('w-full justify-between items-center text-caption text-gray-500 font-bold border-b border-gray-800 q-pb-xs'):
                            ui.label("Column Name")
                            ui.label("Data Type")
                        # Rows
                        for col in columns:
                            with ui.row().classes('w-full justify-between items-center text-body2 text-gray-200 border-b border-gray-850/40 q-py-xs'):
                                ui.label(col.get("name"))
                                ui.label(col.get("type")).classes('text-indigo-400 font-mono')
                                
                with ui.row().classes('w-full justify-end q-mt-md'):
                    ui.button('Close', on_click=schema_dialog.close).props('flat color=white')
        schema_dialog.open()

    def show_quality(ds: Dataset):
        quality_dialog.clear()
        with quality_dialog:
            with ui.card().classes('q-pa-xl glass-panel').style('width: 750px; max-width: 95%;'):
                ui.label(f"Data Quality Diagnostics: {ds.name}").classes('text-h5 text-white font-bold q-mb-md')
                
                metrics = get_dataset_quality_metrics(ds.file_path, ds.file_type)
                if "error" in metrics:
                    ui.label(metrics["error"]).classes('text-red-400')
                else:
                    # Totals
                    with ui.row().classes('w-full justify-around q-mb-lg border border-gray-800/40 q-pa-md rounded-lg'):
                        with ui.column().classes('items-center'):
                            ui.label("Total Rows").classes('text-caption text-gray-500')
                            ui.label(f"{metrics['total_rows']:,}").classes('text-h6 text-white font-black')
                        with ui.column().classes('items-center'):
                            ui.label("Duplicate Rows").classes('text-caption text-gray-500')
                            ui.label(f"{metrics['duplicate_rows']:,}").classes('text-h6 text-pink-400 font-black')
                        with ui.column().classes('items-center'):
                            ui.label("Duplicate Rate").classes('text-caption text-gray-500')
                            ui.label(f"{metrics['duplicate_percentage']}%").classes('text-h6 text-pink-400 font-black')
                            
                    ui.label("Column Diagnostics").classes('text-subtitle1 text-white font-bold q-mb-sm')
                    
                    with ui.column().classes('w-full gap-sm').style('max-height: 400px; overflow-y: auto;'):
                        # Table Header
                        with ui.row().classes('w-full justify-between items-center text-caption text-indigo-300 font-bold border-b border-gray-800 q-pb-xs q-pr-sm'):
                            ui.label("Column").style('width: 150px;')
                            ui.label("Type").style('width: 100px;')
                            ui.label("Nulls (%)").style('width: 100px;')
                            ui.label("Outliers (%)").style('width: 100px;')
                            ui.label("Range / Cardinality").style('width: 180px;')
                            
                        # Rows
                        for col_name, stats in metrics.get("column_stats", {}).items():
                            with ui.row().classes('w-full justify-between items-center text-body2 text-gray-200 border-b border-gray-850/40 q-py-sm q-pr-sm'):
                                ui.label(col_name).style('width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;')
                                ui.label(stats.get("data_type")).classes('text-indigo-400 font-mono').style('width: 100px;')
                                
                                # Null status
                                null_text = f"{stats.get('null_count')} ({stats.get('null_percentage')}%)"
                                null_color = "text-pink-400 font-bold" if stats.get('null_count') > 0 else "text-gray-300"
                                ui.label(null_text).classes(null_color).style('width: 100px;')
                                
                                # Outliers
                                if stats.get("is_numeric"):
                                    outliers_text = f"{stats.get('outlier_count')} ({stats.get('outlier_percentage')}%)"
                                    outliers_color = "text-yellow-500 font-bold" if stats.get('outlier_count') > 0 else "text-gray-300"
                                    ui.label(outliers_text).classes(outliers_color).style('width: 100px;')
                                    
                                    # Range info
                                    range_text = f"{stats.get('min')} to {stats.get('max')}"
                                    ui.label(range_text).classes('text-gray-400 text-caption').style('width: 180px;')
                                else:
                                    ui.label("-").classes('text-gray-600').style('width: 100px;')
                                    cardinality_text = f"{stats.get('unique_values_count')} unique"
                                    ui.label(cardinality_text).classes('text-gray-400 text-caption').style('width: 180px;')
                                    
                with ui.row().classes('w-full justify-end q-mt-lg'):
                    ui.button('Close', on_click=quality_dialog.close).props('flat color=white')
        quality_dialog.open()
        
    with Layout("Settings"):
        # Header title
        with ui.row().classes('w-full q-mb-md'):
            ui.label("Settings & Data Management").classes('text-h4 font-bold text-white')
            
        schema_dialog = ui.dialog()
        quality_dialog = ui.dialog()
        
        # Tabs for management sections
        with ui.tabs().classes('w-full bg-transparent text-indigo-300') as tabs:
            data_tab = ui.tab('Datasets & Connections', icon='cloud_upload')
            system_tab = ui.tab('System Configuration', icon='settings')
            
        with ui.tab_panels(tabs, value=data_tab).classes('w-full bg-transparent q-mt-md'):
            with ui.tab_panel(data_tab).classes('q-pa-none gap-lg'):
                # Split columns: Left is dataset list, Right is File Upload box
                with ui.row().classes('w-full gap-lg items-stretch'):
                    # Datasets registry listing
                    with ui.column().classes('glass-panel q-pa-lg').style('flex: 2; min-width: 400px;'):
                        ui.label("Registered Datasets").classes('text-h5 font-bold text-white q-mb-md')
                        datasets_list_container = ui.column().classes('w-full gap-sm')
                        refresh_datasets_list()
                        
                    # File upload box
                    with ui.column().classes('glass-panel q-pa-lg justify-start').style('flex: 1; min-width: 250px;'):
                        ui.label("Upload Dataset").classes('text-h5 font-bold text-white q-mb-sm')
                        ui.label("Upload CSV or Parquet data file into the raw layer storage.").classes('text-caption text-gray-500 q-mb-md')
                        
                        # Upload Widget
                        ui.upload(
                            on_upload=handle_upload,
                            label="Choose CSV/Parquet",
                            auto_upload=True,
                            max_files=1
                        ).classes('w-full bg-gray-900/30 text-white').props('dark flat bordered color=indigo')
                        
            with ui.tab_panel(system_tab).classes('glass-panel q-pa-lg'):
                ui.label("Platform Preferences").classes('text-h5 font-bold text-white q-mb-md')
                
                with ui.column().classes('gap-md'):
                    # Dark mode switch
                    with ui.row().classes('items-center justify-between w-64'):
                        ui.label("Dark UI Mode").classes('text-body1 text-gray-200')
                        ui.switch(value=True, on_change=lambda e: ui.dark_mode().enable() if e.value else ui.dark_mode().disable()).props('color=indigo')
                        
                    # Target SQL Engine info
                    with ui.row().classes('items-center justify-between w-64'):
                        ui.label("Analytical Engine").classes('text-body1 text-gray-200')
                        ui.label("DuckDB (In-Memory)").classes('text-body2 text-indigo-400 font-bold')
                        
                    # AI model status
                    with ui.row().classes('items-center justify-between w-64'):
                        ui.label("AI Copilot Router").classes('text-body1 text-gray-200')
                        has_openai = "OpenAI (active)" if os.environ.get("OPENAI_API_KEY") else "Regex Rule Fallback"
                        ui.label(has_openai).classes('text-body2 text-pink-400 font-bold')
