from nicegui import app, ui

def apply_theme():
    # Retrieve user preference (default to dark mode)
    dark_mode_active = app.storage.user.get('dark_mode', True)
    
    # Configure Quasar dark mode
    dark = ui.dark_mode()
    if dark_mode_active:
        dark.enable()
    else:
        dark.disable()

    # Define layout color styling variables
    if dark_mode_active:
        bg = "#0B0F19"
        text = "#F3F4F6"
        text_muted = "#9CA3AF"
        glass_bg = "rgba(17, 24, 39, 0.7)"
        glass_card = "rgba(30, 41, 59, 0.45)"
        border = "rgba(255, 255, 255, 0.08)"
        shadow = "0 4px 6px -1px rgba(0, 0, 0, 0.2)"
        hshadow = "0 10px 25px rgba(99, 102, 241, 0.15)"
        hborder = "rgba(99, 102, 241, 0.3)"
        sidebar = "rgba(11, 15, 25, 0.9)"
        header = "rgba(11, 15, 25, 0.8)"
    else:
        bg = "#F8FAFC"
        text = "#0F172A"
        text_muted = "#64748B"
        glass_bg = "rgba(255, 255, 255, 0.85)"
        glass_card = "rgba(255, 255, 255, 0.9)"
        border = "rgba(0, 0, 0, 0.08)"
        shadow = "0 4px 6px -1px rgba(0, 0, 0, 0.05)"
        hshadow = "0 10px 25px rgba(99, 102, 241, 0.1)"
        hborder = "rgba(99, 102, 241, 0.2)"
        sidebar = "rgba(255, 255, 255, 0.95)"
        header = "rgba(248, 250, 252, 0.8)"

    THEME_CSS = f"""
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
    
    body, input, button, select, textarea, .q-btn, .q-field, .q-item, .q-card {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }}
    
    body {{
        background-color: {bg} !important;
        color: {text} !important;
        margin: 0;
        padding: 0;
    }}
    
    .glass-panel {{
        background: {glass_bg} !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid {border} !important;
        border-radius: 16px !important;
    }}
    
    .glass-card {{
        background: {glass_card} !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid {border} !important;
        border-radius: 12px !important;
        box-shadow: {shadow} !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    
    .glass-card:hover {{
        transform: translateY(-3px);
        box-shadow: {hshadow} !important;
        border-color: {hborder} !important;
    }}
    
    .bg-gradient-primary {{
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
    }}
    
    .bg-gradient-accent {{
        background: linear-gradient(135deg, #EC4899 0%, #8B5CF6 100%) !important;
    }}
    
    .text-gradient {{
        background: linear-gradient(90deg, #818CF8, #EC4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
    }}

    .text-main {{
        color: {text} !important;
    }}

    .text-muted {{
        color: {text_muted} !important;
    }}
    
    /* Scrollbars */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}
    ::-webkit-scrollbar-track {{
        background: rgba(11, 15, 25, 0.05);
    }}
    ::-webkit-scrollbar-thumb {{
        background: rgba(99, 102, 241, 0.3);
        border-radius: 3px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: rgba(99, 102, 241, 0.6);
    }}
    
    /* Animations */
    @keyframes fadeInUp {{
        from {{
            opacity: 0;
            transform: translateY(15px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
    
    .animate-fade-in {{
        animation: fadeInUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }}
    
    .hover-glow {{
        transition: all 0.2s ease-in-out;
    }}
    .hover-glow:hover {{
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.5) !important;
    }}
    """
    ui.add_head_html(f"<style>{THEME_CSS}</style>")
    return dark_mode_active
