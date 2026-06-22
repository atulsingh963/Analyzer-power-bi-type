from nicegui import ui
from database.db import SessionLocal
from backend.models.models import User
from backend.auth.security import hash_password
from frontend.theme import apply_theme

@ui.page('/reset_password')
def reset_password_page(username: str = None):
    apply_theme()
    
    if not username:
        ui.navigate.to("/login")
        return
        
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
    
    password_input = None
    confirm_password_input = None
    error_label = None
    
    def handle_reset():
        password = password_input.value
        confirm_password = confirm_password_input.value
        
        if not password or not confirm_password:
            error_label.set_text("Please fill in all fields.")
            error_label.set_visibility(True)
            return
            
        if password != confirm_password:
            error_label.set_text("Passwords do not match.")
            error_label.set_visibility(True)
            return
            
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(username=username).first()
            if not user:
                error_label.set_text("Error identifying active user account.")
                error_label.set_visibility(True)
                return
                
            # Update password
            user.hashed_password = hash_password(password)
            db.commit()
            
            ui.notify("Password successfully reset! Please sign in with your new credentials.", type='positive')
            ui.navigate.to("/login")
            
        except Exception as e:
            error_label.set_text(f"Password reset failed: {str(e)}")
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
            ui.label('Reset Your Password').classes('text-subtitle2 text-indigo-300 font-bold q-mb-md')
            
            ui.label(f"Account Username: {username}").classes('text-caption text-indigo-400 font-bold tracking-wide q-mb-md')
            
            password_input = ui.input(label='New Password').classes('w-full q-mb-sm').props('outlined dark password color=indigo')
            confirm_password_input = ui.input(label='Confirm New Password').classes('w-full q-mb-sm').props('outlined dark password color=indigo')
            
            error_label = ui.label("").classes('text-red-400 text-caption w-full text-center q-mb-md').style('display: none;')
            
            ui.button('Update Password', on_click=handle_reset).classes('w-full glowing-btn text-white text-subtitle1 font-bold rounded-lg q-py-sm').style('text-transform: none !important;')
            
            ui.separator().classes('q-my-md w-full')
            
            with ui.row().classes('w-full justify-center text-caption text-gray-400'):
                ui.button('Back to Login', on_click=lambda: ui.navigate.to('/login')).props('flat dense size=sm color=indigo')
