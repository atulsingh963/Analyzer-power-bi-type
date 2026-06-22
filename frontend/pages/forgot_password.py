from nicegui import ui
from database.db import SessionLocal
from backend.models.models import User
from frontend.theme import apply_theme

@ui.page('/forgot_password')
def forgot_password_page():
    apply_theme()
    
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
    
    username_input = None
    error_label = None
    
    def handle_submit():
        user_val = username_input.value.strip()
        if not user_val:
            error_label.set_text("Please enter your Username or Email.")
            error_label.set_visibility(True)
            return
            
        db = SessionLocal()
        try:
            # Check by username or email
            user = db.query(User).filter((User.username == user_val) | (User.email == user_val)).first()
            if not user:
                error_label.set_text("Account not found. Verify your details.")
                error_label.set_visibility(True)
                return
                
            ui.notify("Validation successful! Redirecting to password reset screen...", type='info')
            ui.navigate.to(f"/reset_password?username={user.username}")
            
        except Exception as e:
            error_label.set_text(f"Error checking user account: {str(e)}")
            error_label.set_visibility(True)
        finally:
            db.close()
            
    with ui.column().classes('login-container w-full h-screen items-center justify-center'):
        with ui.element('div').classes('login-bg-shapes'):
            ui.element('div').classes('bubble bubble-1')
            ui.element('div').classes('bubble bubble-2')
            
        with ui.card().classes('glass-panel q-pa-xl items-center z-10').style('width: 450px; max-width: 90%;'):
            with ui.row().classes('items-center justify-center gap-xs q-mb-xs'):
                ui.icon('insights', size='44px', color='indigo-400')
                ui.label('ANALYZER').classes('text-gradient text-h4 font-black tracking-wider')
            ui.label('Password Recovery').classes('text-subtitle2 text-indigo-300 font-bold q-mb-md')
            
            ui.label("Enter your account username or registered email address to verify your identity and configure a new password.").classes('text-caption text-gray-400 text-center q-mb-md')
            
            username_input = ui.input(label='Username or Email').classes('w-full q-mb-sm').props('outlined dark color=indigo')
            username_input.on('keydown.enter', handle_submit)
            
            error_label = ui.label("").classes('text-red-400 text-caption w-full text-center q-mb-md').style('display: none;')
            
            ui.button('Verify Account', on_click=handle_submit).classes('w-full glowing-btn text-white text-subtitle1 font-bold rounded-lg q-py-sm').style('text-transform: none !important;')
            
            ui.separator().classes('q-my-md w-full')
            
            with ui.row().classes('w-full justify-center text-caption text-gray-400'):
                ui.button('Back to Login', on_click=lambda: ui.navigate.to('/login')).props('flat dense size=sm color=indigo')
