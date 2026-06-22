from nicegui import app, ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from backend.models.models import Dashboard

@ui.page('/insights')
@require_nicegui_auth
def insights_page():
    db = SessionLocal()
    try:
        dashboards = db.query(Dashboard).all()
    except Exception:
        dashboards = []
    finally:
        db.close()
        
    # Get user favorite dashboards from persistent user storage
    favorites = app.storage.user.get('favorite_dashboards', [])
    
    # State values for filters
    search_query = ""
    selected_category = "All"
    selected_tag = "All"
    
    gallery_grid = None
    
    # Static helper maps for category & tags mapping by dashboard ID
    def get_dashboard_meta(d_id: int):
        if d_id % 2 == 1:
            return "Executive", ["Sales", "Parquet", "Holt-Winters"]
        else:
            return "Operations", ["ETL", "Web Metrics", "DuckDB"]
            
    def toggle_favorite(d_id: int):
        favs = app.storage.user.get('favorite_dashboards', [])
        if d_id in favs:
            favs.remove(d_id)
            ui.notify("Removed from favorites", type='warning')
        else:
            favs.append(d_id)
            ui.notify("Added to favorites", type='positive')
        app.storage.user['favorite_dashboards'] = favs
        refresh_gallery()
        
    def refresh_gallery():
        gallery_grid.clear()
        
        filtered = []
        for d in dashboards:
            category, tags = get_dashboard_meta(d.id)
            is_fav = d.id in app.storage.user.get('favorite_dashboards', [])
            
            # Apply search filter
            if search_query and search_query.lower() not in d.name.lower() and (d.description and search_query.lower() not in d.description.lower()):
                continue
                
            # Apply category filter
            if selected_category != "All" and selected_category != category:
                continue
                
            # Apply tags filter
            if selected_tag != "All" and selected_tag not in tags:
                continue
                
            filtered.append((d, category, tags, is_fav))
            
        with gallery_grid:
            if not filtered:
                with ui.column().classes('w-full items-center justify-center q-pa-xl bg-gray-900/10 rounded-lg'):
                    ui.icon('search_off', size='48px', color='gray-600')
                    ui.label("No dashboards match your criteria.").classes('text-gray-400 text-body2 q-mt-sm')
                return
                
            for d, category, tags, is_fav in filtered:
                with ui.card().classes('glass-card q-pa-md flex flex-col justify-between').style('width: 320px; height: 260px;'):
                    with ui.column().classes('gap-xs w-full'):
                        with ui.row().classes('w-full justify-between items-center q-mb-xs'):
                            ui.badge(category, color='indigo' if category == "Executive" else 'purple')
                            # Favorite toggle
                            fav_icon = 'star' if is_fav else 'star_border'
                            fav_color = 'yellow-500' if is_fav else 'gray-500'
                            ui.button(on_click=lambda d_id=d.id: toggle_favorite(d_id), icon=fav_icon).props(f'flat round color={fav_color} size=sm')
                            
                        ui.label(d.name).classes('text-h6 font-bold text-white text-ellipsis overflow-hidden').style('white-space: nowrap;')
                        ui.label(d.description or "No description provided.").classes('text-caption text-gray-400 text-ellipsis overflow-hidden').style('display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; height: 36px; white-space: normal;')
                        
                        # Tag badges
                        with ui.row().classes('w-full gap-xs q-mt-sm'):
                            for tag in tags:
                                ui.badge(tag, color='gray-800').style('font-size: 0.65rem;')
                                
                    # Bottom Action buttons
                    with ui.row().classes('w-full justify-between items-center border-t border-gray-800/40 q-pt-md q-mt-auto'):
                        ui.button('Launch Report', on_click=lambda d_id=d.id: ui.navigate.to(f'/dashboard_builder?id={d_id}')).classes('bg-indigo-600 text-white font-bold text-caption').style('text-transform: none !important; border-radius: 6px;')
                        ui.label(f"v{d.version}").classes('text-caption text-gray-500')

    # Trigger filter changes
    def on_search(e):
        nonlocal search_query
        search_query = e.value
        refresh_gallery()
        
    def filter_by_cat(cat):
        nonlocal selected_category
        selected_category = cat
        refresh_gallery()
        
    with Layout("Insights Gallery"):
        # Header Controls
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("Insights Gallery").classes('text-h4 font-bold text-white')
                ui.label("Search dashboard collections, view favorites, and filter by tags.").classes('text-caption text-gray-400')
                
        # Filters toolbar
        with ui.row().classes('w-full glass-panel q-pa-md items-center justify-between gap-md q-mb-lg'):
            # Text Search
            with ui.row().classes('items-center bg-gray-900/20 rounded-lg px-sm py-xs border border-gray-800/40 w-80'):
                ui.icon('search', color='indigo-400', size='20px')
                ui.input(placeholder='Search gallery reports...', on_change=on_search).props('borderless dense dark').classes('col text-caption bg-transparent')
                
            # Category selection
            with ui.row().classes('items-center gap-xs'):
                ui.label("Category:").classes('text-caption text-gray-400 font-bold')
                with ui.row().classes('gap-xs'):
                    for cat in ["All", "Executive", "Operations"]:
                        ui.button(cat, on_click=lambda c=cat: filter_by_cat(c)).props('flat size=sm color=indigo')
                        
            # Tags filter selection
            with ui.row().classes('items-center gap-xs'):
                ui.label("Filter Tag:").classes('text-caption text-gray-400 font-bold')
                tags_list = ["All", "Sales", "Parquet", "ETL", "DuckDB", "Web Metrics"]
                
                def set_tag_filter(e):
                    nonlocal selected_tag
                    selected_tag = e.value
                    refresh_gallery()
                    
                ui.select(options=tags_list, value="All", on_change=set_tag_filter).classes('w-32').props('dense outlined color=indigo dark')

        # Grid view container
        gallery_grid = ui.row().classes('w-full gap-md q-py-md items-start justify-start')
        
        # Inital Load
        refresh_gallery()
