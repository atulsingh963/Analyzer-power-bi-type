from nicegui import ui
from database.db import SessionLocal
from backend.models.models import User
from backend.auth.security import create_access_token, verify_password
from frontend.theme import apply_theme

@ui.page('/login')
def login_page():
    apply_theme()
    
    # Custom CSS for high-end SaaS background animation and layout styling
    login_style = """
    <style>
    .login-container {
        min-height: 100vh;
        width: 100vw;
        background: radial-gradient(circle at 15% 25%, rgba(99, 102, 241, 0.15) 0%, transparent 45%),
                    radial-gradient(circle at 85% 75%, rgba(139, 92, 246, 0.12) 0%, transparent 45%),
                    #0B0F19 !important;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        position: relative;
    }
    .login-bg-shapes {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        z-index: 0;
        pointer-events: none;
    }
    .bubble {
        position: absolute;
        border-radius: 50%;
        background: linear-gradient(135deg, rgba(99,102,241,0.1) 0%, rgba(236,72,153,0.05) 100%);
        animation: floatShape 20s infinite ease-in-out;
    }
    .bubble-1 { width: 300px; height: 300px; top: -100px; left: -100px; }
    .bubble-2 { width: 400px; height: 400px; bottom: -150px; right: -150px; animation-duration: 25s; }
    @keyframes floatShape {
        0%, 100% { transform: translateY(0) scale(1); }
        50% { transform: translateY(-30px) scale(1.05); }
    }
    .glowing-btn {
        background: linear-gradient(90deg, #6366F1, #8B5CF6) !important;
        box-shadow: 0 4px 15px rgba(99, 102, 241, 0.4);
        transition: all 0.3s ease;
    }
    .glowing-btn:hover {
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.6);
        transform: translateY(-1px);
    }
    </style>
    """
    ui.add_head_html(login_style)
    
    # State variables
    username_input = None
    password_input = None
    error_label = None
    
    async def handle_login():
        username = username_input.value.strip()
        password = password_input.value
        
        if not username or not password:
            error_label.set_text("Please fill in all fields.")
            error_label.set_visibility(True)
            return
            
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username=username).first()
            if not user or not verify_password(password, user.hashed_password):
                error_label.set_text("Invalid username or password.")
                error_label.set_visibility(True)
                return
                
            if not user.is_active:
                error_label.set_text("Your account is deactivated.")
                error_label.set_visibility(True)
                return
                
            # Generate session token
            token = create_access_token(data={"sub": user.username})
            ui.run_javascript(f"document.cookie = 'access_token={token}; path=/; max-age=86400;';")
            ui.navigate.to("/home")
            
        except Exception as e:
            error_label.set_text(f"Authentication error: {str(e)}")
            error_label.set_visibility(True)
        finally:
            db.close()
            
    with ui.column().classes('login-container w-full h-screen items-center justify-center'):
        # Animated background elements
        with ui.element('div').classes('login-bg-shapes'):
            ui.element('div').classes('bubble bubble-1')
            ui.element('div').classes('bubble bubble-2')
            
        # Login card
        with ui.card().classes('glass-panel q-pa-xl items-center z-10').style('width: 450px; max-width: 90%;'):
            # Header Branding
            with ui.row().classes('items-center justify-center gap-xs q-mb-xs'):
                ui.icon('insights', size='44px', color='indigo-400')
                ui.label('ANALYZER').classes('text-gradient text-h4 font-black tracking-wider')
            ui.label('Analytics SaaS Platform').classes('text-subtitle2 text-indigo-300 font-bold q-mb-md')
            
            # Form Fields
            username_input = ui.input(label='Username').classes('w-full q-mb-sm').props('outlined dark color=indigo')
            username_input.on('keydown.enter', handle_login)
            
            password_input = ui.input(label='Password').classes('w-full q-mb-sm').props('outlined dark password color=indigo')
            password_input.on('keydown.enter', handle_login)
            
            error_label = ui.label("").classes('text-red-400 text-caption w-full text-center q-mb-md').style('display: none;')
            
            # Action button
            ui.button('Sign In', on_click=handle_login).classes('w-full glowing-btn text-white text-subtitle1 font-bold rounded-lg q-py-sm').style('text-transform: none !important;')
            
            # Social login buttons placeholder
            with ui.column().classes('w-full items-center q-mt-md gap-xs'):
                ui.label("or continue with").classes('text-caption text-gray-500 q-mb-xs')
                with ui.row().classes('w-full justify-center gap-md'):
                    ui.button(icon='google', color='indigo').props('flat round size=md').tooltip('Google Sign In')
                    ui.button(icon='github', color='indigo').props('flat round size=md').tooltip('GitHub Sign In')
                    ui.button(icon='microsoft', color='indigo').props('flat round size=md').tooltip('Microsoft Active Directory')
            
            ui.separator().classes('q-my-md w-full')
            
            # Help links
            with ui.row().classes('w-full justify-between items-center text-caption text-gray-400'):
                ui.button('Register Account', on_click=lambda: ui.navigate.to('/register')).props('flat dense size=sm color=indigo')
                ui.button('Forgot Password?', on_click=lambda: ui.navigate.to('/forgot_password')).props('flat dense size=sm color=indigo')
