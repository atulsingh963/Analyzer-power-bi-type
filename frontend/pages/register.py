from nicegui import ui
from database.db import SessionLocal
from backend.models.models import User, Role
from backend.auth.security import hash_password
from frontend.theme import apply_theme

@ui.page('/register')
def register_page():
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
    
    # Form fields
    username_input = None
    email_input = None
    password_input = None
    confirm_password_input = None
    error_label = None
    
    async def handle_register():
        username = username_input.value.strip()
        email = email_input.value.strip()
        password = password_input.value
        confirm_password = confirm_password_input.value
        
        if not username or not email or not password or not confirm_password:
            error_label.set_text("Please fill in all fields.")
            error_label.set_visibility(True)
            return
            
        if password != confirm_password:
            error_label.set_text("Passwords do not match.")
            error_label.set_visibility(True)
            return
            
        db = SessionLocal()
        try:
            # Check existing username
            existing_user = db.query(User).filter_by(username=username).first()
            if existing_user:
                error_label.set_text("Username already taken.")
                error_label.set_visibility(True)
                return
                
            # Check existing email
            existing_email = db.query(User).filter_by(email=email).first()
            if existing_email:
                error_label.set_text("Email address already registered.")
                error_label.set_visibility(True)
                return
                
            # Find default Analyst role (id=2)
            analyst_role = db.query(Role).filter_by(name="Analyst").first()
            role_id = analyst_role.id if analyst_role else 2
            
            # Create user
            hashed = hash_password(password)
            new_user = User(
                username=username,
                email=email,
                hashed_password=hashed,
                role_id=role_id,
                is_active=True
            )
            db.add(new_user)
            db.commit()
            
            ui.notify("Account created successfully! Please sign in.", type='positive')
            ui.navigate.to("/login")
            
        except Exception as e:
            error_label.set_text(f"Registration failed: {str(e)}")
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
            ui.label('Create Your Platform Account').classes('text-subtitle2 text-indigo-300 font-bold q-mb-md')
            
            username_input = ui.input(label='Username').classes('w-full q-mb-sm').props('outlined dark color=indigo')
            email_input = ui.input(label='Email Address').classes('w-full q-mb-sm').props('outlined dark color=indigo')
            
            password_input = ui.input(label='Password').classes('w-full q-mb-sm').props('outlined dark password color=indigo')
            confirm_password_input = ui.input(label='Confirm Password').classes('w-full q-mb-sm').props('outlined dark password color=indigo')
            
            error_label = ui.label("").classes('text-red-400 text-caption w-full text-center q-mb-md').style('display: none;')
            
            ui.button('Register', on_click=handle_register).classes('w-full glowing-btn text-white text-subtitle1 font-bold rounded-lg q-py-sm').style('text-transform: none !important;')
            
            ui.separator().classes('q-my-md w-full')
            
            with ui.row().classes('w-full justify-center text-caption text-gray-400'):
                ui.label("Already have an account?")
                ui.button('Sign In', on_click=lambda: ui.navigate.to('/login')).props('flat dense size=sm color=indigo').classes('q-ml-xs')
