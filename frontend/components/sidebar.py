import functools
from nicegui import ui, context, app
from backend.auth.security import decode_access_token
from database.db import SessionLocal
from sqlalchemy.orm import joinedload
from backend.models.models import User, Workspace, AuditLog

def get_current_user_from_cookie() -> User:
    try:
        request = context.client.request
        token = request.cookies.get("access_token")
        if not token:
            return None
            
        payload = decode_access_token(token)
        if not payload:
            return None
            
        username = payload.get("sub")
        db = SessionLocal()
        user = db.query(User).options(joinedload(User.role)).filter_by(username=username).first()
        db.close()
        return user
    except Exception:
        return None

def require_nicegui_auth(func):
    """
    Decorator to protect NiceGUI pages and redirect anonymous requests to login.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user_from_cookie()
        if not user:
            ui.navigate.to("/login")
            return
        return func(*args, **kwargs)
    return wrapper

class Layout:
    """
    Unified page shell inspired by Lumenore.
    Includes top navigation, global search, notifications, workspaces, theme switcher, and profile dropdowns.
    """
    def __init__(self, title: str):
        self.title = title
        
    def __enter__(self):
        # 1. Apply global themes and get active mode
        from frontend.theme import apply_theme
        dark_active = apply_theme()
        
        # 2. Verify authentication
        user = get_current_user_from_cookie()
        if not user:
            ui.navigate.to("/login")
            return self
            
        # 3. Dynamic layout color definitions
        header_color = "rgba(11, 15, 25, 0.85)" if dark_active else "rgba(248, 250, 252, 0.85)"
        text_color = "white" if dark_active else "indigo-950"
        btn_color = "white" if dark_active else "indigo-900"
        sidebar_bg = "rgba(11, 15, 25, 0.9)" if dark_active else "rgba(255, 255, 255, 0.95)"
        border_css = "border-bottom: 1px solid rgba(255, 255, 255, 0.08) !important;" if dark_active else "border-bottom: 1px solid rgba(0, 0, 0, 0.08) !important;"
        
        # Pull live notifications (latest audit logs)
        db = SessionLocal()
        try:
            live_logs = db.query(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.timestamp.desc()).limit(3).all()
        except Exception:
            live_logs = []
        db.close()

        # Helper callback to toggle light/dark theme preference
        def toggle_theme():
            app.storage.user['dark_mode'] = not dark_active
            ui.navigate.reload()

        # 4. Top Navigation Bar (Header)
        with ui.header().classes('glass-panel q-py-sm q-px-lg items-center justify-between').style(f'background-color: {header_color} !important; {border_css}'):
            with ui.row().classes('items-center gap-md'):
                ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props(f'flat round color={btn_color}')
                # Platform Logo
                ui.icon('insights', size='28px', color='indigo-400')
                ui.label('ANALYZER').classes('text-gradient text-h5 tracking-widest font-black')
                ui.badge("SaaS", color="indigo").classes('q-ml-xs text-caption font-bold')
                
            # Global Search input
            with ui.row().classes('items-center bg-gray-900/10 dark:bg-white/5 rounded-lg px-sm py-xs border border-gray-800/40 w-80 gt-xs'):
                ui.icon('search', color='indigo-400', size='20px')
                ui.input(placeholder='Search Reports & Insights...').props('borderless dense dark' if dark_active else 'borderless dense').classes('col text-caption bg-transparent')
                
            with ui.row().classes('items-center gap-md'):
                # Dynamic Workspace Selector
                db_sess = SessionLocal()
                try:
                    workspaces = db_sess.query(Workspace).filter_by(owner_id=user.id).all()
                    if not workspaces:
                        workspaces = db_sess.query(Workspace).all()
                except Exception:
                    workspaces = []
                ws_names = [w.name for w in workspaces]
                db_sess.close()
                
                if ws_names:
                    with ui.select(options=ws_names, value=ws_names[0]).classes('w-44 text-white' if dark_active else 'w-44 text-indigo-950').props('dense outlined color=indigo dark' if dark_active else 'dense outlined color=indigo'):
                        pass
                
                # Theme Switcher Toggler
                theme_icon = 'light_mode' if dark_active else 'dark_mode'
                ui.button(icon=theme_icon, on_click=toggle_theme).props(f'flat round color={btn_color}').tooltip('Toggle Light/Dark Theme')

                # Notification Center Dropdown Popover
                with ui.button(icon='notifications').props(f'flat round color={btn_color}') as notif_btn:
                    if len(live_logs) > 0:
                        ui.badge(str(len(live_logs)), color='red').props('floating')
                    with ui.menu().classes('q-pa-md glass-panel text-white' if dark_active else 'q-pa-md glass-panel text-indigo-950').style('width: 320px;'):
                        ui.label('Notification Center').classes('text-subtitle2 font-bold q-mb-sm')
                        if not live_logs:
                            ui.label("No recent events.").classes('text-caption text-gray-400')
                        else:
                            with ui.column().classes('w-full gap-sm'):
                                for l in live_logs:
                                    with ui.column().classes('gap-none w-full border-b border-gray-800/30 pb-xs'):
                                        ui.label(l.action).classes('text-caption font-bold')
                                        user_name = l.user.username if l.user else "System"
                                        ui.label(f"User: {user_name} • {l.timestamp.strftime('%H:%M:%S')}").classes('text-caption text-gray-400')
                        ui.button('View All Activity Log', on_click=lambda: ui.navigate.to('/admin')).props('flat size=sm color=indigo').classes('w-full q-mt-xs')

                # User Profile Avatar Dropdown Menu
                with ui.avatar(icon='person', color='indigo-600', text_color='white', size='32px').classes('cursor-pointer'):
                    with ui.menu().classes('q-pa-md glass-panel text-white' if dark_active else 'q-pa-md glass-panel text-indigo-950').style('width: 240px;'):
                        with ui.column().classes('items-center q-mb-md w-full'):
                            ui.avatar(icon='person', color='indigo-600', text_color='white', size='48px')
                            ui.label(user.username).classes('text-subtitle1 font-bold q-mt-xs')
                            ui.label(user.email).classes('text-caption text-gray-400')
                            ui.badge(user.role.name, color='indigo').classes('q-mt-xs')
                        
                        ui.separator().classes('q-my-sm')
                        
                        ui.button('Dashboard Center', on_click=lambda: ui.navigate.to('/dashboards'), icon='dashboard').props('flat align=left').classes('w-full').style('text-transform: none !important;')
                        ui.button('AI Copilot Chat', on_click=lambda: ui.navigate.to('/ask'), icon='chat').props('flat align=left').classes('w-full').style('text-transform: none !important;')
                        ui.button('Account Settings', on_click=lambda: ui.navigate.to('/settings'), icon='settings').props('flat align=left').classes('w-full').style('text-transform: none !important;')
                        
                        ui.separator().classes('q-my-sm')
                        
                        ui.button('Sign Out', icon='logout', on_click=self.logout).props('flat align=left color=red').classes('w-full').style('text-transform: none !important;')
                
        # 5. Left Navigation Drawer (Fixed left drawer style)
        with ui.left_drawer(value=True, elevated=False).props('behavior=desktop').classes('glass-panel q-py-lg q-px-sm').style(f'background-color: {sidebar_bg} !important;') as left_drawer:
            ui.label('ANALYTICS SaaS').classes('text-caption text-indigo-400 q-px-md q-mb-md font-bold tracking-wider')
            
            with ui.column().classes('w-full gap-xs'):
                self.nav_item('home', 'Overview', '/home')
                self.nav_item('dashboard_gallery', 'Insights Gallery', '/insights')
                self.nav_item('dashboard', 'Report Workspace', '/dashboards')
                self.nav_item('chat', 'Ask Me AI', '/ask')
                self.nav_item('transform', 'Visual ETL', '/etl')
                self.nav_item('trending_up', 'Predictions', '/predictive')
                self.nav_item('notifications', 'AI Bulletin Board', '/bulletin_board')
                self.nav_item('admin_panel_settings', 'Administration', '/admin')
                self.nav_item('settings', 'System Configuration', '/settings')
                
        # 6. Main Container
        self.container = ui.column().classes('w-full q-pa-lg animate-fade-in').style('margin-top: 10px;')
        self.container.__enter__()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.container.__exit__(exc_type, exc_val, exc_tb)
        
    def nav_item(self, icon: str, name: str, route: str):
        current_path = context.client.page.path
        is_active = current_path == route
        
        btn_classes = 'w-full justify-start q-py-sm rounded-lg '
        if is_active:
            btn_classes += 'bg-indigo-600/30 text-indigo-400 font-bold border-l-4 border-indigo-500 q-pl-md'
        else:
            btn_classes += 'text-gray-400 hover:bg-gray-800/10 q-pl-md'
            
        with ui.row().classes('w-full items-center'):
            ui.button(
                name,
                icon=icon,
                on_click=lambda: ui.navigate.to(route)
            ).props('flat align=left').classes(btn_classes).style('text-transform: none !important; font-size: 0.95rem;')
            
    def logout(self):
        ui.run_javascript("document.cookie = 'access_token=; Max-Age=0; path=/;';")
        ui.navigate.to("/login")
