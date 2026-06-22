import pandas as pd
from nicegui import app, ui
import plotly.graph_objects as go
from frontend.components.sidebar import Layout, require_nicegui_auth
from database.db import SessionLocal
from analytics.engine import analytics_engine
from analytics.forecasting import generate_forecast, calculate_churn_classification

@ui.page('/predictive')
@require_nicegui_auth
def predictive_page():
    # Page state references
    category_selector = None
    growth_slider = None
    forecast_chart_container = None
    churn_metrics_container = None
    churn_table_container = None
    
    categories = ["All Categories", "Electronics", "Apparel", "Home & Kitchen", "Groceries", "Books"]
    
    def run_sales_forecast():
        selected_cat = category_selector.value
        growth_factor = growth_slider.value if growth_slider else 1.0
        
        db = SessionLocal()
        try:
            if selected_cat == "All Categories":
                query = "SELECT date, SUM(sales_amount) FROM store_sales GROUP BY date ORDER BY date ASC"
            else:
                query = f"SELECT date, SUM(sales_amount) FROM store_sales WHERE product_category = '{selected_cat}' GROUP BY date ORDER BY date ASC"
                
            res = analytics_engine.execute_query(query, db)
        except Exception as e:
            res = {"success": False, "error": str(e)}
        finally:
            db.close()
            
        forecast_chart_container.clear()
        
        if not res["success"] or not res["data"]:
            with forecast_chart_container:
                ui.label("Error querying database or no data matches category selection.").classes('text-red-400')
            return
            
        dates = [r[0] for r in res["data"]]
        values = [float(r[1]) for r in res["data"]]
        
        # Generate 30 days daily forecast
        forecast_res = generate_forecast(dates, values, steps=30)
        
        if "error" in forecast_res:
            with forecast_chart_container:
                ui.label(forecast_res["error"]).classes('text-red-400')
            return
            
        hist_len = min(60, len(dates))
        chart_dates = dates[-hist_len:] + forecast_res["dates"]
        
        hist_series = [float(v) for v in values[-hist_len:]]
        
        # Scenario Multipliers applied to predictions
        fc_series = [hist_series[-1]] + [float(v) * growth_factor for v in forecast_res["values"]]
        lower_series = [hist_series[-1]] + [float(v) * growth_factor for v in forecast_res["lower_bound"]]
        upper_series = [hist_series[-1]] + [float(v) * growth_factor for v in forecast_res["upper_bound"]]
        
        # Retrieve layout theme configurations
        dark_active = app.storage.user.get('dark_mode', True)
        text_color = "#F3F4F6" if dark_active else "#0F172A"
        grid_color = "rgba(255,255,255,0.08)" if dark_active else "rgba(0,0,0,0.08)"
        
        # Construct Plotly Forecasting Chart with Confidence Interval shading
        fig = go.Figure()
        
        # 1. Historical Data trace
        fig.add_trace(go.Scatter(
            x=chart_dates[:hist_len],
            y=hist_series,
            mode='lines',
            line=dict(color='#6366F1', width=3),
            name="Historical Sales (Last 60 Days)"
        ))
        
        # 2. Upper Interval bound trace (transparent)
        fig.add_trace(go.Scatter(
            x=chart_dates[hist_len-1:],
            y=upper_series,
            mode='lines',
            line=dict(width=0),
            showlegend=False
        ))
        
        # 3. Lower Interval bound trace with fill
        fig.add_trace(go.Scatter(
            x=chart_dates[hist_len-1:],
            y=lower_series,
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(236, 72, 153, 0.15)',
            name="95% Confidence Interval"
        ))
        
        # 4. Projected sales projection trace
        fig.add_trace(go.Scatter(
            x=chart_dates[hist_len-1:],
            y=fc_series,
            mode='lines',
            line=dict(color='#EC4899', width=3, dash='dash'),
            name="Projected Sales (30 Days)"
        ))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color=text_color,
            font_family='Plus Jakarta Sans',
            margin=dict(l=40, r=20, t=30, b=40),
            xaxis=dict(
                gridcolor=grid_color,
                tickangle=-45,
                tickfont=dict(color=text_color)
            ),
            yaxis=dict(
                gridcolor=grid_color,
                tickfont=dict(color=text_color)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color=text_color)
            )
        )
        
        with forecast_chart_container:
            ui.plotly(fig).classes('w-full h-96')

    def run_churn_analytics():
        db = SessionLocal()
        try:
            res = analytics_engine.execute_query("SELECT * FROM store_sales", db)
        except Exception:
            res = {"success": False}
        finally:
            db.close()
            
        churn_metrics_container.clear()
        churn_table_container.clear()
        
        if not res["success"] or not res["data"]:
            with churn_metrics_container:
                ui.label("Failed to load store sales transactions dataset.").classes('text-red-400')
            return
            
        columns = res["columns"]
        data = res["data"]
        df_sales = pd.DataFrame(data, columns=columns)
        
        churn_res = calculate_churn_classification(df_sales)
        
        if "error" in churn_res:
            with churn_metrics_container:
                ui.label(churn_res["error"]).classes('text-red-400')
            return
            
        with churn_metrics_container:
            with ui.row().classes('w-full justify-around bg-gray-900/20 q-pa-md rounded-lg border border-gray-800/40'):
                with ui.column().classes('items-center'):
                    ui.label("Analyzed Segments").classes('text-caption text-gray-400')
                    ui.label(f"{churn_res['total_segments_analyzed']:,}").classes('text-h5 font-black text-white dark:text-white text-indigo-950')
                with ui.column().classes('items-center'):
                    ui.label("High-Risk Segments").classes('text-caption text-gray-400')
                    ui.label(f"{churn_res['churned_segments']:,}").classes('text-h5 font-black text-yellow-500')
                with ui.column().classes('items-center'):
                    ui.label("Churn Probability Rate").classes('text-caption text-gray-400')
                    ui.label(f"{churn_res['overall_churn_rate']}%").classes('text-h5 font-black text-pink-500')
                    
        with churn_table_container:
            ui.label("Highest Churn-Risk Customer Cohorts").classes('text-subtitle1 text-white dark:text-indigo-950 font-bold q-mb-sm')
            
            cols_def = [
                {"name": "profile_id", "label": "Cohort Group (Store + Gender + Age)", "field": "profile_id", "align": "left"},
                {"name": "frequency", "label": "Purchases", "field": "frequency", "align": "center"},
                {"name": "total_spend", "label": "Total Spent", "field": "total_spend", "align": "right"},
                {"name": "recency_days", "label": "Inactive Days", "field": "recency_days", "align": "center"},
                {"name": "risk_probability", "label": "Churn Risk %", "field": "risk_probability", "align": "right"}
            ]
            
            rows_def = []
            for p in churn_res["top_risk_profiles"]:
                display_id = f"{p['store'].split(' ')[0]} • {p['gender']} • Age {p['age']}"
                rows_def.append({
                    "profile_id": display_id,
                    "frequency": p["frequency"],
                    "total_spend": f"${p['total_spend']:,.2f}",
                    "recency_days": p["recency_days"],
                    "risk_probability": f"{p['risk_probability']}%"
                })
                
            ui.table(columns=cols_def, rows=rows_def).classes('w-full').props('dark flat bordered' if app.storage.user.get('dark_mode', True) else 'flat bordered')

    with Layout("Predictive Analytics"):
        # Header Info
        with ui.row().classes('w-full q-mb-md justify-between items-center'):
            with ui.column():
                ui.label("Predictive Analytics").classes('text-h4 font-bold text-white')
                ui.label("Time-series sales forecasting simulations and customer churn classification models.").classes('text-caption text-gray-400')
                
        with ui.tabs().classes('w-full bg-transparent text-indigo-300') as tabs:
            forecasting_tab = ui.tab('Revenue Forecasting', icon='show_chart')
            churn_tab = ui.tab('Churn & Classification', icon='psychology')
            
        with ui.tab_panels(tabs, value=forecasting_tab).classes('w-full bg-transparent q-mt-md'):
            # Tab 1: Forecasting Panel
            with ui.tab_panel(forecasting_tab).classes('q-pa-none gap-md'):
                with ui.column().classes('glass-panel q-pa-lg w-full'):
                    with ui.row().classes('w-full justify-between items-center q-mb-md gap-md'):
                        ui.label("Revenue Forecasting Simulation").classes('text-h5 font-bold text-white')
                        
                        # Selection toolbar controls
                        with ui.row().classes('items-center gap-md'):
                            ui.label("Product:").classes('text-body2 text-gray-400')
                            category_selector = ui.select(
                                options=categories, 
                                value=categories[0],
                                on_change=lambda _: run_sales_forecast()
                            ).classes('w-44 text-white').props('dense outlined color=indigo dark' if app.storage.user.get('dark_mode', True) else 'dense outlined color=indigo')
                            
                            ui.label("Scenario multiplier:").classes('text-body2 text-gray-400')
                            growth_slider = ui.slider(
                                min=0.5, max=2.0, step=0.1, value=1.0,
                                on_change=lambda _: run_sales_forecast()
                            ).classes('w-36')
                            ui.badge('', color='indigo').bind_text_from(growth_slider, 'value', backward=lambda v: f"{v:.1f}x")
                            
                    # Graph rendering area
                    forecast_chart_container = ui.column().classes('w-full q-py-md items-center justify-center')
                    
            # Tab 2: Churn Panel
            with ui.tab_panel(churn_tab).classes('q-pa-none gap-md'):
                with ui.row().classes('w-full gap-lg items-stretch'):
                    with ui.column().classes('glass-panel q-pa-lg').style('flex: 1; min-width: 300px;'):
                        ui.label("ML Classification Summary").classes('text-h5 font-bold text-white q-mb-md')
                        churn_metrics_container = ui.column().classes('w-full gap-md q-mb-md')
                        ui.markdown("""
                        ### **Random Forest Model**
                        * **Inputs**: Purchase frequency, age, store locations, and spending indicators.
                        * **Confidence Bands**: High-risk cohorts show recency inactivity > 45 days.
                        """).classes('text-caption text-gray-400')
                        
                    with ui.column().classes('glass-panel q-pa-lg').style('flex: 2; min-width: 400px;'):
                        churn_table_container = ui.column().classes('w-full gap-sm')
                        
        # Trigger Inital Data Loads
        run_sales_forecast()
        run_churn_analytics()
