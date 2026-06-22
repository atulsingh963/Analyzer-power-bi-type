from nicegui import ui
from frontend.components.sidebar import Layout, require_nicegui_auth
from frontend.components.charts import render_chart
from database.db import SessionLocal
from ai.agents.sql_agent import ai_agent
from analytics.engine import analytics_engine

@ui.page('/ask')
@require_nicegui_auth
def ask_me_page(q: str = None):
    # State values
    messages = []
    history_items = [
        "What are the total sales by store name?",
        "Show visitor sessions by device category",
        "Show sales amount by product category",
        "Find the average bounce rate of sessions"
    ]
    
    # Selected dataset context
    selected_ds = "Store Sales"
    
    # Suggested prompts mapping by dataset
    suggestions_map = {
        "Store Sales": [
            "Show total sales by product category",
            "What is the average customer age by store location?",
            "List top 5 stores with highest transactions"
        ],
        "Web Metrics": [
            "Show total web sessions by device category",
            "What is the average bounce rate by referrer channel?",
            "Compare session durations over time"
        ]
    }
    
    chat_container = None
    input_box = None
    suggestions_container = None
    
    def refresh_chat():
        chat_container.clear()
        with chat_container:
            if not messages:
                with ui.column().classes('w-full items-center justify-center q-pa-xl bg-gray-900/5 dark:bg-white/5 rounded-lg border border-dashed border-gray-800 q-mt-xl'):
                    ui.icon('smart_toy', size='56px', color='indigo-400')
                    ui.label("I am your AI Copilot Assistant.").classes('text-subtitle1 text-white font-bold')
                    ui.label("Select a dataset context and type a question or select a suggestion on the right.").classes('text-caption text-gray-400 text-center')
                return
                
            for msg in messages:
                if msg["sender"] == "user":
                    with ui.row().classes('w-full justify-end q-mb-md'):
                        with ui.card().classes('q-pa-md bg-indigo-600 text-white rounded-lg').style('max-width: 70%; border-bottom-right-radius: 2px; border: none;'):
                            ui.label(msg["text"]).classes('text-body1')
                else:
                    with ui.row().classes('w-full justify-start q-mb-lg'):
                        with ui.card().classes('q-pa-lg glass-panel rounded-lg').style('max-width: 90%; border-top-left-radius: 2px;'):
                            with ui.row().classes('items-center gap-xs q-mb-sm text-indigo-400 font-bold'):
                                ui.icon('smart_toy', size='22px')
                                ui.label("Analyzer Copilot")
                                
                            if msg.get("error"):
                                ui.label("SQL Execution Error").classes('text-red-400 font-bold text-caption')
                                ui.code(msg["sql"]).classes('w-full q-my-xs text-caption').props('dark')
                                ui.label(msg["error"]).classes('text-caption text-red-300 bg-red-950/40 q-pa-sm rounded')
                            else:
                                with ui.expansion('Show Generated SQL Query', icon='code').classes('w-full text-caption bg-gray-900/20 text-gray-400 q-mb-md rounded'):
                                    ui.code(msg["sql"]).classes('w-full').props('dark')
                                    
                                if msg.get("data"):
                                    with ui.row().classes('w-full q-my-md items-center justify-center bg-gray-900/10 q-pa-md rounded-lg border border-gray-800/20'):
                                        render_chart(
                                            columns=msg["data"]["columns"],
                                            data=msg["data"]["data"],
                                            chart_type=msg["data"]["visualization"]
                                        )
                                        
                                ui.markdown(msg["text"]).classes('text-body1 text-gray-300 q-mt-md')
            
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight);")

    async def execute_question(question_text: str):
        if not question_text.strip():
            return
            
        messages.append({"sender": "user", "text": question_text})
        if question_text not in history_items:
            history_items.insert(0, question_text)
            
        refresh_chat()
        
        with chat_container:
            loader = ui.row().classes('w-full justify-start q-mb-md animate-pulse')
            with loader:
                with ui.card().classes('q-pa-md glass-panel items-center text-indigo-300'):
                    with ui.row().classes('items-center gap-sm'):
                        ui.spinner(size='md', color='indigo')
                        ui.label("Consulting schemas and executing DuckDB analytical models...")
            ui.run_javascript("window.scrollTo(0, document.body.scrollHeight);")
            
        db = SessionLocal()
        try:
            sql = ai_agent.generate_sql(question_text, db)
            if not sql:
                messages.append({
                    "sender": "ai",
                    "text": "Failed to translate prompt to SQL query. Ensure schemas are seeded.",
                    "sql": "",
                    "error": "SQL Generation Failure"
                })
            else:
                res = analytics_engine.execute_query(sql, db)
                if not res.get("success"):
                    messages.append({
                        "sender": "ai",
                        "text": "",
                        "sql": sql,
                        "error": res.get("error")
                    })
                else:
                    columns = res.get("columns", [])
                    data = res.get("data", [])
                    visualization = ai_agent.suggest_visualization(columns, data)
                    insights = ai_agent.generate_narrative(question_text, sql, columns, data)
                    
                    messages.append({
                        "sender": "ai",
                        "text": insights,
                        "sql": sql,
                        "data": {
                            "columns": columns,
                            "data": data,
                            "visualization": visualization
                        }
                    })
        except Exception as e:
            messages.append({
                "sender": "ai",
                "text": "",
                "sql": "",
                "error": f"Internal Copilot Error: {str(e)}"
            })
        finally:
            db.close()
            
        loader.delete()
        refresh_chat()

    def handle_submit():
        question = input_box.value.strip()
        if question:
            input_box.value = ""
            ui.timer(0.1, lambda: execute_question(question), once=True)

    def select_suggestion(suggestion: str):
        ui.notify(f"Selected: '{suggestion}'", type='info')
        ui.timer(0.1, lambda: execute_question(suggestion), once=True)

    def on_ds_change(e):
        nonlocal selected_ds
        selected_ds = e.value
        refresh_suggestions()

    def refresh_suggestions():
        suggestions_container.clear()
        with suggestions_container:
            for prompt in suggestions_map.get(selected_ds, []):
                with ui.row().classes('w-full justify-between items-center q-pa-sm border-b border-gray-800/30 hover:bg-indigo-950/20 rounded cursor-pointer transition-colors q-mb-xs'):
                    ui.label(prompt).classes('text-caption text-gray-300 font-bold col').on('click', lambda p=prompt: select_suggestion(p))
                    ui.icon('chevron_right', color='indigo-400', size='20px')

    with Layout("AI Copilot Assistant"):
        # Header title
        with ui.row().classes('w-full justify-between items-center q-mb-md border-b border-gray-800/30 pb-xs'):
            with ui.column():
                ui.label("Ask Me AI Copilot").classes('text-h4 font-bold text-white')
                ui.label("Conversational RAG agent converting normal questions to optimized DuckDB SQL queries.").classes('text-caption text-gray-400')
            ui.button('Clear Conversation', on_click=lambda: (messages.clear(), refresh_chat())).props('flat dense color=red-4 icon=delete_sweep')

        # Outer Row containing 3-panels
        with ui.row().classes('w-full gap-md items-stretch').style('height: calc(100vh - 280px);'):
            # Panel 1: Conversation History (Left)
            with ui.column().classes('glass-panel q-pa-md justify-start gt-sm').style('width: 250px;'):
                ui.label("Query History").classes('text-caption text-indigo-400 font-bold uppercase tracking-wider q-mb-md')
                with ui.column().classes('w-full gap-sm overflow-y-auto grow'):
                    for item in history_items:
                        with ui.row().classes('w-full items-center gap-xs cursor-pointer hover:text-indigo-400 transition-colors border-b border-gray-800/10 pb-xs').on('click', lambda it=item: select_suggestion(it)):
                            ui.icon('history', size='16px', color='gray-500')
                            ui.label(item).classes('text-caption text-gray-300 truncate').style('max-width: 190px;')

            # Panel 2: Chat Interface (Center)
            with ui.column().classes('col relative-position').style('display: flex; flex-direction: column;'):
                # Scrolling Messages Zone
                chat_container = ui.column().classes('w-full q-pa-sm grow').style('overflow-y: auto; max-height: calc(100vh - 400px); min-height: 200px;')
                
                # Bottom Input Container
                with ui.column().classes('w-full q-mt-auto gap-xs q-pt-md border-t border-gray-800/40'):
                    with ui.row().classes('w-full gap-sm items-center'):
                        # Context selector
                        ui.label("Context:").classes('text-caption text-gray-400')
                        ui.select(
                            options=["Store Sales", "Web Metrics"],
                            value=selected_ds,
                            on_change=on_ds_change
                        ).classes('w-44 text-white').props('dense outlined color=indigo dark')
                        
                    with ui.row().classes('w-full items-center gap-sm'):
                        input_box = ui.input(
                            placeholder="Type a query (e.g. show sales by category)..."
                        ).classes('col').props('outlined dark rounded color=indigo').style('font-size: 0.95rem;')
                        input_box.on('keydown.enter', handle_submit)
                        
                        # Voice Input placeholder button
                        ui.button(icon='mic', on_click=lambda: ui.notify("Voice input listening... (Demo context)", type='info')).classes('bg-gray-800 text-white').props('round flat size=md')
                        ui.button(on_click=handle_submit, icon='send').classes('bg-gradient-primary text-white q-pa-md').props('round flat')

            # Panel 3: Suggestions & Insights (Right)
            with ui.column().classes('glass-panel q-pa-md justify-start gt-xs').style('width: 320px;'):
                ui.label("Suggested Prompts").classes('text-caption text-indigo-400 font-bold uppercase tracking-wider q-mb-md')
                suggestions_container = ui.column().classes('w-full gap-xs q-mb-md overflow-y-auto')
                refresh_suggestions()
                
                ui.separator().classes('q-my-md')
                
                ui.label("Visual Recommendations").classes('text-caption text-indigo-400 font-bold uppercase tracking-wider q-mb-sm')
                ui.markdown("""
                * **KPI Visuals**: Auto-suggested for single values (e.g., *Total Revenue*).
                * **Col/Line Charts**: Suggested for groupings with multiple records.
                * **Pie Charts**: Recommended for smaller cohorts (e.g., *Device Share*).
                """).classes('text-caption text-gray-400 q-px-sm')
                
        # Handle initial query parameter triggers
        if q:
            messages.clear()
            ui.timer(0.2, lambda: execute_question(q), once=True)
        else:
            refresh_chat()
