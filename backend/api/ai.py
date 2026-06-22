from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database.db import get_db_session
from backend.models.models import User
from backend.auth.security import get_current_user
from ai.agents.sql_agent import ai_agent
from analytics.engine import analytics_engine

router = APIRouter(prefix="/api/ai", tags=["ai"])

# Pydantic Schemas
class AskRequest(BaseModel):
    question: str

class AskResponse(BaseModel):
    success: bool
    sql: str
    columns: Optional[List[str]] = None
    data: Optional[List[List[Any]]] = None
    visualization: Optional[str] = None  # kpi, bar, line, pie, table
    insights: Optional[str] = None
    error: Optional[str] = None

@router.post("/ask", response_model=AskResponse)
def ask_ai(
    req: AskRequest,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    """
    Main Natural Language interface for Analyzer.
    Translates question to SQL, runs in DuckDB analytical engine, selects charts, and writes narrative insights.
    """
    # 1. Generate SQL from question
    sql = ai_agent.generate_sql(req.question, db)
    
    if not sql:
        return {
            "success": False,
            "sql": "",
            "error": "Failed to translate natural language question to SQL. Schema metadata could be missing."
        }
        
    # 2. Execute SQL against DuckDB
    query_result = analytics_engine.execute_query(sql, db)
    
    if not query_result.get("success"):
        return {
            "success": False,
            "sql": sql,
            "error": query_result.get("error")
        }
        
    columns = query_result.get("columns", [])
    data = query_result.get("data", [])
    
    # 3. Suggest best visualization type
    visualization = ai_agent.suggest_visualization(columns, data)
    
    # 4. Generate narrative explanation and business insights
    insights = ai_agent.generate_narrative(req.question, sql, columns, data)
    
    return {
        "success": True,
        "sql": sql,
        "columns": columns,
        "data": data,
        "visualization": visualization,
        "insights": insights
    }
