import plotly.graph_objects as go
from nicegui import app, ui

def render_chart(columns: list, data: list, chart_type: str):
    """
    Renders a highly polished interactive Plotly visual inside NiceGUI based on dataset and type.
    Conforms layout styling to dynamic light/dark theme preference automatically.
    """
    if not columns or not data:
        ui.label("No visual data to render.").classes('text-gray-400 text-caption')
        return
        
    num_cols = len(columns)
    
    # 1. KPI Card Visual
    if chart_type == "kpi":
        val = data[0][0]
        label = columns[0]
        if len(data[0]) > 1:
            label = str(data[0][0])
            val = data[0][1]
            
        val_str = f"${val:,.2f}" if isinstance(val, (int, float)) and val > 100 else f"{val:,}" if isinstance(val, (int, float)) else str(val)
        
        with ui.card().classes('glass-card q-pa-lg items-center text-center justify-center w-64 animate-fade-in'):
            ui.icon('speed', size='40px', color='indigo-400')
            ui.label(label.upper()).classes('text-caption text-indigo-300 font-bold tracking-wider q-mt-xs')
            ui.label(val_str).classes('text-h3 font-black text-white dark:text-white text-indigo-950 q-mt-sm')
        return

    # Extract categories and values
    categories = [str(row[0]) for row in data]
    
    # Extract numerical values
    values = []
    for row in data:
        val = row[1] if len(row) > 1 else 0.0
        try:
            values.append(float(val) if val is not None else 0.0)
        except ValueError:
            values.append(0.0)

    # 2. Retrieve theme styling variables
    dark_active = app.storage.user.get('dark_mode', True)
    text_color = "#F3F4F6" if dark_active else "#0F172A"
    grid_color = "rgba(255,255,255,0.08)" if dark_active else "rgba(0,0,0,0.08)"
    color_palette = ["#6366F1", "#EC4899", "#10B981", "#3B82F6", "#F59E0B"]
    
    fig = go.Figure()
    
    # Configure graph type
    if chart_type == "bar":
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=color_palette[0],
            name=columns[1] if len(columns) > 1 else "Metric"
        ))
        
    elif chart_type == "line":
        fig.add_trace(go.Scatter(
            x=categories,
            y=values,
            mode='lines+markers',
            line=dict(color=color_palette[1], width=3),
            marker=dict(size=8, color=color_palette[0]),
            name=columns[1] if len(columns) > 1 else "Metric"
        ))
        
    elif chart_type in ("pie", "donut"):
        is_donut = chart_type == "donut"
        fig.add_trace(go.Pie(
            labels=categories,
            values=values,
            hole=0.4 if is_donut else 0.0,
            marker=dict(colors=color_palette),
            textinfo='percent+label' if len(categories) < 8 else 'percent'
        ))
        
    elif chart_type == "treemap":
        fig.add_trace(go.Treemap(
            labels=categories,
            parents=[""] * len(categories),
            values=values,
            marker=dict(colors=color_palette)
        ))
        
    elif chart_type == "heatmap":
        # expects a grid matrix or single rows array
        fig.add_trace(go.Heatmap(
            z=[values],
            x=categories,
            y=[columns[1]] if len(columns) > 1 else ["Metric"],
            colorscale='Viridis'
        ))
        
    elif chart_type == "sankey":
        fig.add_trace(go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=categories + [columns[1] if len(columns) > 1 else "Metric"],
                color=color_palette[0]
            ),
            link=dict(
                source=list(range(len(categories))),
                target=[len(categories)] * len(categories),
                value=values
            )
        ))
        
    elif chart_type == "waterfall":
        fig.add_trace(go.Waterfall(
            name="Waterfall",
            orientation="v",
            x=categories,
            y=values,
            connector=dict(line=dict(color=color_palette[0]))
        ))
        
    elif chart_type == "maps":
        fig.add_trace(go.Scattergeo(
            locations=categories,
            locationmode='USA-states' if any(len(c) == 2 for c in categories) else 'country names',
            text=categories,
            marker=dict(
                size=[min(max(v / (max(values) or 1) * 35, 8), 45) for v in values] if values else 12,
                color=color_palette[0],
                line=dict(width=1, color='rgba(0,0,0,0.5)')
            )
        ))
        
    else:  # Table Fallback
        columns_def = [{"name": c, "label": c, "field": c, "align": "left"} for c in columns]
        rows_def = []
        for r in data:
            row_dict = {}
            for col_idx, col_name in enumerate(columns):
                row_dict[col_name] = r[col_idx]
            rows_def.append(row_dict)
            
        ui.table(columns=columns_def, rows=rows_def).classes('w-full').props('dark flat bordered' if dark_active else 'flat bordered')
        return

    # Update common layout attributes for Plotly figures
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font_color=text_color,
        font_family='Plus Jakarta Sans',
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis=dict(
            gridcolor=grid_color,
            tickfont=dict(color=text_color),
            title=dict(font=dict(color=text_color))
        ) if chart_type not in ("pie", "donut", "treemap", "sankey", "maps") else None,
        yaxis=dict(
            gridcolor=grid_color,
            tickfont=dict(color=text_color),
            title=dict(font=dict(color=text_color))
        ) if chart_type not in ("pie", "donut", "treemap", "sankey", "maps") else None,
        legend=dict(font=dict(color=text_color)),
        geo=dict(
            bgcolor='rgba(0,0,0,0)',
            lakecolor='rgba(0,0,0,0)',
            landcolor='rgba(99,102,241,0.05)',
            subunitcolor='rgba(255,255,255,0.1)',
            showlakes=True,
            showcountries=True
        ) if chart_type == "maps" else None
    )
    
    ui.plotly(fig).classes('w-full h-80 bg-transparent')
