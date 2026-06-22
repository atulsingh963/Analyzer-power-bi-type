import os
from nicegui import ui
from backend.main import app

# Import all page routers to register their NiceGUI route decorators (@ui.page)
import frontend.pages.login
import frontend.pages.register
import frontend.pages.forgot_password
import frontend.pages.reset_password
import frontend.pages.home
import frontend.pages.settings
import frontend.pages.ask_me
import frontend.pages.predictive
import frontend.pages.data_magnet
import frontend.pages.dashboard_center
import frontend.pages.dashboard_builder
import frontend.pages.insights
import frontend.pages.bulletin_board
import frontend.pages.admin

@ui.page('/')
def root_route():
    """
    Root route redirects to Home if active access token cookie is present,
    otherwise redirects to Login.
    """
    from frontend.components.sidebar import get_current_user_from_cookie
    user = get_current_user_from_cookie()
    if user:
        ui.navigate.to("/home")
    else:
        ui.navigate.to("/login")

# Mount NiceGUI on top of the FastAPI application instance
# NiceGUI handles websocket and page routing under the hood
ui.run_with(
    app,
    mount_path="/",
    storage_secret=os.environ.get("STORAGE_SECRET", "ANALYZER_STORAGE_SECRET_KEY_12345!")
)

if __name__ in {"__main__", "__mp_main__"}:
    import uvicorn
    print("\n" + "="*50)
    print("  LAUNCHING ANALYZER PLATFORM")
    print("  URL: http://127.0.0.1:8000")
    print("="*50 + "\n")
    uvicorn.run("run:app", host="127.0.0.1", port=8000, reload=False)
