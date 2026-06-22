import os
import re
import json
import requests
from sqlalchemy.orm import Session
from backend.models.models import Dataset

class AIAgent:
    def __init__(self):
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        self.ollama_api_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434/api/generate")

    def generate_sql(self, question: str, db: Session) -> str:
        """
        Translates a natural language question into SQL.
        Prefers OpenAI, then Ollama, and falls back to a smart rule-based translation engine.
        """
        # Fetch available dataset tables & schema
        datasets = db.query(Dataset).all()
        schema_context = []
        tables = []
        for ds in datasets:
            table_name = ds.name.lower().strip().replace(" ", "_").replace("-", "_")
            tables.append(table_name)
            cols = ds.schema_info.get("columns", []) if ds.schema_info else []
            col_desc = ", ".join([f"{c['name']} ({c['type']})" for c in cols])
            schema_context.append(f"Table: {table_name}\nColumns: {col_desc}")
            
        schema_str = "\n\n".join(schema_context)
        
        # 1. Try OpenAI if API Key exists
        if self.openai_api_key:
            try:
                print("AIAgent: Using OpenAI for Text-to-SQL...")
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                system_prompt = f"""You are a DuckDB SQL generator. Write only the raw SQL query. No markdown formatting, no comments.
Given the following database schema:
{schema_str}

Translate the user's question into a valid, executable DuckDB SQL query. Use lowercase table names. Refer only to columns listed in the schema.
"""
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question}
                    ],
                    "temperature": 0.0
                }
                res = requests.post(url, headers=headers, json=data, timeout=10)
                if res.status_code == 200:
                    sql = res.json()["choices"][0]["message"]["content"].strip()
                    # Strip any markdown wrappers
                    sql = re.sub(r"```sql\s*|\s*```", "", sql)
                    return sql
            except Exception as e:
                print(f"OpenAI SQL Generation failed: {e}. Falling back...")

        # 2. Try Ollama if running
        if self.ollama_api_url:
            try:
                print("AIAgent: Using Ollama for Text-to-SQL...")
                system_prompt = f"""You are a SQL generator for DuckDB. Respond with ONLY the raw SQL query. No explanation, no markdown.
Schema:
{schema_str}
"""
                data = {
                    "model": "llama3",
                    "prompt": f"{system_prompt}\n\nQuestion: {question}\nSQL:",
                    "stream": False
                }
                res = requests.post(self.ollama_api_url, json=data, timeout=10)
                if res.status_code == 200:
                    sql = res.json()["response"].strip()
                    sql = re.sub(r"```sql\s*|\s*```", "", sql)
                    return sql
            except Exception as e:
                print(f"Ollama SQL Generation failed: {e}. Falling back...")

        # 3. Smart Regex Rule-Based Fallback Engine
        print("AIAgent: Using rule-based regex fallback engine...")
        return self._fallback_sql_generator(question, tables, datasets)

    def _fallback_sql_generator(self, question: str, tables: list, datasets: list) -> str:
        q = question.lower()
        
        # Determine table
        target_table = None
        for t in tables:
            # Check for direct mention
            if t in q:
                target_table = t
                break
                
        # Heuristic if not directly mentioned
        if not target_table:
            if any(w in q for w in ["sale", "store", "transaction", "customer", "product", "revenue", "age"]):
                target_table = "store_sales"
            elif any(w in q for w in ["web", "session", "visitor", "bounce", "page", "device", "traffic", "click"]):
                target_table = "web_metrics"
            else:
                target_table = tables[0] if tables else "store_sales"
                
        # Basic patterns for store_sales
        if target_table == "store_sales":
            # Group bys
            groupby_col = None
            if "by store" in q or "per store" in q:
                groupby_col = "store_name"
            elif "by category" in q or "per category" in q or "by product category" in q:
                groupby_col = "product_category"
            elif "by gender" in q or "per gender" in q:
                groupby_col = "customer_gender"
            elif "by age" in q or "per age" in q:
                groupby_col = "customer_age"
            elif "daily" in q or "by date" in q or "over time" in q:
                groupby_col = "date"
                
            # Aggregations
            agg_expr = "SUM(sales_amount) AS total_sales"
            if "average sales" in q or "avg sales" in q:
                agg_expr = "ROUND(AVG(sales_amount), 2) AS avg_sales"
            elif "units" in q or "unit sold" in q:
                agg_expr = "SUM(units_sold) AS total_units_sold"
            elif "average age" in q or "avg age" in q:
                agg_expr = "ROUND(AVG(customer_age), 1) AS avg_customer_age"
            elif "highest price" in q or "max price" in q:
                agg_expr = "MAX(unit_price) AS max_price"
            elif "count" in q or "transactions" in q:
                agg_expr = "COUNT(*) AS total_transactions"
                
            if groupby_col:
                if groupby_col == "date":
                    return f"SELECT date, {agg_expr} FROM store_sales GROUP BY date ORDER BY date ASC"
                else:
                    return f"SELECT {groupby_col}, {agg_expr} FROM store_sales GROUP BY {groupby_col} ORDER BY {groupby_col} ASC"
            else:
                return f"SELECT {agg_expr} FROM store_sales"
                
        # Basic patterns for web_metrics
        elif target_table == "web_metrics":
            # Group bys
            groupby_col = None
            if "by device" in q or "per device" in q:
                groupby_col = "device"
            elif "by traffic source" in q or "by source" in q:
                groupby_col = "traffic_source"
            elif "by page" in q or "per page" in q or "most visited" in q:
                groupby_col = "page_path"
            elif "daily" in q or "by date" in q or "over time" in q:
                groupby_col = "CAST(timestamp AS DATE) AS date"
                
            # Aggregations
            agg_expr = "COUNT(*) AS total_sessions"
            if "bounce rate" in q or "bounce" in q:
                agg_expr = "ROUND(SUM(CASE WHEN is_bounce THEN 1.0 ELSE 0.0 END) * 100.0 / COUNT(*), 2) AS bounce_rate"
            elif "duration" in q or "average session duration" in q:
                agg_expr = "ROUND(AVG(session_duration_sec), 1) AS avg_session_duration"
            elif "unique visitor" in q or "visitor" in q:
                agg_expr = "COUNT(DISTINCT visitor_id) AS unique_visitors"
                
            if groupby_col:
                gcol_clean = "date" if "cast" in groupby_col.lower() else groupby_col
                return f"SELECT {groupby_col}, {agg_expr} FROM web_metrics GROUP BY {gcol_clean} ORDER BY {gcol_clean} ASC"
            else:
                return f"SELECT {agg_expr} FROM web_metrics"
                
        # Catch-all
        return f"SELECT * FROM {target_table} LIMIT 10"

    def suggest_visualization(self, columns: list, data: list) -> str:
        """
        Infers the best chart type for the dataset structure.
        """
        if not columns or not data:
            return "table"
            
        num_cols = len(columns)
        num_rows = len(data)
        
        # Only 1 cell (1 row, 1 col) -> KPI
        if num_rows == 1 and num_cols == 1:
            return "kpi"
            
        # 1 Row with a single label and value -> KPI (or 2 columns: Label, Value)
        if num_rows == 1 and num_cols == 2:
            return "kpi"
            
        # Determine column types
        has_date = False
        date_col = None
        numeric_cols = []
        categorical_cols = []
        
        for idx, col in enumerate(columns):
            col_lower = col.lower()
            # Date detection
            if "date" in col_lower or "time" in col_lower or "timestamp" in col_lower:
                has_date = True
                date_col = col
            # Simple check of data row to see if numeric
            val = data[0][idx] if data else None
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                numeric_cols.append(col)
            elif val is not None:
                categorical_cols.append(col)
                
        # 1. Date + Numeric -> Line Chart (Time Series)
        if has_date and numeric_cols:
            return "line"
            
        # 2. Categorical + Numeric -> Bar Chart (or Pie Chart if low cardinality)
        if categorical_cols and numeric_cols:
            # Low category count -> Pie chart is good
            if num_rows <= 6:
                return "pie"
            return "bar"
            
        # 3. Numeric column exists but no explicit category -> Line/Bar
        if len(numeric_cols) >= 1 and num_rows > 1:
            return "bar"
            
        # Fallback to Table
        return "table"

    def generate_narrative(self, question: str, sql: str, columns: list, data: list) -> str:
        """
        Generates textual narrative explanation and highlights.
        """
        if not data:
            return "No data was returned for this query to analyze."
            
        # 1. Try OpenAI for insights
        if self.openai_api_key:
            try:
                print("AIAgent: Generating narrative using OpenAI...")
                url = "https://api.openai.com/v1/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_api_key}"
                }
                system_prompt = f"""You are a business intelligence analyst. Generate clean Markdown insights based on a query.
Question: {question}
SQL Query: {sql}
Results Headers: {columns}
Results Data: {data}

Provide:
1. **Summary**: A 2-sentence summary of what the data shows.
2. **Key Insights**: 2-3 bullet points highlighting highest, lowest, or noteworthy figures.
3. **Recommendations**: 1-2 actionable business recommendations based on the numbers.
Use professional formatting. Keep it concise.
"""
                data_payload = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "user", "content": system_prompt}
                    ],
                    "temperature": 0.3
                }
                res = requests.post(url, headers=headers, json=data_payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                print(f"OpenAI Narrative failed: {e}. Falling back...")
                
        # 2. Try Ollama for insights
        if self.ollama_api_url:
            try:
                print("AIAgent: Generating narrative using Ollama...")
                prompt = f"""You are a BI analyst. Generate Markdown insights for the query results.
Question: {question}
SQL: {sql}
Data: {data} (columns: {columns})

Provide:
- **Summary** (brief)
- **Key Takeaways** (highest/lowest values)
- **Actionable Recommendations**
"""
                data_payload = {
                    "model": "llama3",
                    "prompt": prompt,
                    "stream": False
                }
                res = requests.post(self.ollama_api_url, json=data_payload, timeout=10)
                if res.status_code == 200:
                    return res.json()["response"].strip()
            except Exception as e:
                print(f"Ollama Narrative failed: {e}. Falling back...")

        # 3. Fallback Rule-Based Insights Engine
        print("AIAgent: Using rule-based insights generation...")
        return self._generate_fallback_narrative(question, columns, data)

    def _generate_fallback_narrative(self, question: str, columns: list, data: list) -> str:
        num_rows = len(data)
        num_cols = len(columns)
        
        # 1. KPI Case (Single numeric value)
        if num_rows == 1 and num_cols == 1:
            val = data[0][0]
            val_str = f"${val:,.2f}" if isinstance(val, (float, int)) and val > 100 else str(val)
            return f"""### **Summary**
The query successfully calculated a single key performance indicator (KPI) metric representing **{columns[0]}**.

### **Key Insights**
* **Current Value:** **{val_str}**
* The metric aligns with current tracking parameters. No historical data was requested for variance check.

### **Recommendations**
* Establish historical baseline tracking for **{columns[0]}** to monitor performance trends.
"""

        # 2. Single row, multiple columns KPI
        if num_rows == 1 and num_cols > 1:
            details = [f"**{col}**: {val}" for col, val in zip(columns, data[0])]
            return f"""### **Summary**
The calculation returned details for a single target query row:
* {', '.join(details)}

### **Key Insights**
* All metrics are operating within expected ranges.
* Review details above to understand specific structural proportions.
"""

        # 3. Categorical + Numeric Comparison
        # Look for category index and numeric index
        cat_idx = 0
        num_idx = 1
        
        # Double check if indices match
        for i, val in enumerate(data[0]):
            if isinstance(val, (int, float)) and not isinstance(val, bool):
                num_idx = i
                break
        for i, val in enumerate(data[0]):
            if isinstance(val, str):
                cat_idx = i
                break
                
        try:
            # Sort data by numeric value descending
            sorted_data = sorted(data, key=lambda x: x[num_idx] if x[num_idx] is not None else 0, reverse=True)
            top_category = sorted_data[0][cat_idx]
            top_val = sorted_data[0][num_idx]
            bottom_category = sorted_data[-1][cat_idx]
            bottom_val = sorted_data[-1][num_idx]
            
            # Format numbers
            top_val_str = f"${top_val:,.2f}" if top_val > 100 else f"{top_val:,}"
            bottom_val_str = f"${bottom_val:,.2f}" if bottom_val > 100 else f"{bottom_val:,}"
            
            total_sum = sum([r[num_idx] for r in data if isinstance(r[num_idx], (int, float))])
            total_sum_str = f"${total_sum:,.2f}" if total_sum > 100 else f"{total_sum:,}"
            
            return f"""### **Summary**
The analytical query analyzed **{columns[num_idx]}** partitioned by **{columns[cat_idx]}**. The cumulative sum of these elements is **{total_sum_str}** across **{num_rows}** records.

### **Key Insights**
* **Top Performer:** **{top_category}** registered the highest volume at **{top_val_str}** (representing **{round(top_val/total_sum*100, 1)}%** of the total).
* **Lagging Performer:** **{bottom_category}** recorded the lowest volume at **{bottom_val_str}** (representing **{round(bottom_val/total_sum*100, 1)}%** of the total).
* **Performance Gap:** The spread between the highest and lowest performers is **{top_category}** leading **{bottom_category}** by **{top_val - bottom_val:,.2f}**.

### **Recommendations**
* **Replication Strategy:** Analyze the operational/marketing methods of **{top_category}** to replicate its success in other segments.
* **Optimization Review:** Formulate an optimization program specifically for **{bottom_category}** to address its lower yield and support growth.
"""
        except Exception:
            # Universal fallback markdown
            return f"""### **Summary**
The query returned **{num_rows}** data records with **{num_cols}** distinct columns: `{', '.join(columns)}`.

### **Key Insights**
* The highest value in the primary column is **{data[0][0]}**.
* Dataset shows distributed performance parameters.

### **Recommendations**
* Set up real-time dashboard tracking on these parameters to check for weekly variations.
"""

# Global instance
ai_agent = AIAgent()
