from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database.db import get_db_session
from backend.models.models import Dashboard, Widget, Workspace, User
from backend.auth.security import get_current_user

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])

# Pydantic schemas
class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = None
    workspace_id: int
    is_shared: Optional[bool] = False

class DashboardUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    layout: Optional[Dict[str, Any]] = None
    is_shared: Optional[bool] = None
    version: Optional[int] = None

class WidgetCreate(BaseModel):
    name: str
    type: str  # KPI, Bar, Line, Pie, Plotly, Table, etc.
    query_config: Optional[Dict[str, Any]] = None
    visual_config: Optional[Dict[str, Any]] = None

class WidgetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    query_config: Optional[Dict[str, Any]] = None
    visual_config: Optional[Dict[str, Any]] = None

class WidgetResponse(BaseModel):
    id: int
    dashboard_id: int
    name: str
    type: str
    query_config: Optional[Dict[str, Any]] = None
    visual_config: Optional[Dict[str, Any]] = None
    class Config:
        from_attributes = True

class DashboardDetailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    workspace_id: int
    layout: Optional[Dict[str, Any]] = None
    is_shared: bool
    version: int
    widgets: List[WidgetResponse] = []
    class Config:
        from_attributes = True

# Dashboard Endpoints
@router.get("")
def list_dashboards(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    # Admin gets all, others get owned workspaces or shared dashboards
    if current_user.role.name == "Admin":
        dashboards = db.query(Dashboard).all()
    else:
        workspaces = db.query(Workspace).filter_by(owner_id=current_user.id).all()
        workspace_ids = [w.id for w in workspaces]
        dashboards = db.query(Dashboard).filter(
            (Dashboard.workspace_id.in_(workspace_ids)) | (Dashboard.is_shared == True)
        ).all()
        
    return [
        {
            "id": d.id,
            "name": d.name,
            "description": d.description,
            "workspace_id": d.workspace_id,
            "is_shared": d.is_shared,
            "version": d.version,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat()
        }
        for d in dashboards
    ]

@router.post("", response_model=DashboardDetailResponse)
def create_dashboard(
    dashboard_data: DashboardCreate, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    workspace = db.query(Workspace).filter_by(id=dashboard_data.workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to create dashboards in this workspace")
        
    new_dashboard = Dashboard(
        name=dashboard_data.name,
        description=dashboard_data.description,
        workspace_id=dashboard_data.workspace_id,
        is_shared=dashboard_data.is_shared,
        layout={},
        version=1
    )
    
    db.add(new_dashboard)
    db.commit()
    db.refresh(new_dashboard)
    return new_dashboard

@router.get("/{dashboard_id}", response_model=DashboardDetailResponse)
def get_dashboard(
    dashboard_id: int, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    # Check access permission
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id and not dashboard.is_shared:
        raise HTTPException(status_code=403, detail="Forbidden to access this dashboard")
        
    return dashboard

@router.put("/{dashboard_id}", response_model=DashboardDetailResponse)
def update_dashboard(
    dashboard_id: int, 
    dashboard_data: DashboardUpdate, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to edit this dashboard")
        
    # Apply updates
    if dashboard_data.name is not None:
        dashboard.name = dashboard_data.name
    if dashboard_data.description is not None:
        dashboard.description = dashboard_data.description
    if dashboard_data.layout is not None:
        dashboard.layout = dashboard_data.layout
    if dashboard_data.is_shared is not None:
        dashboard.is_shared = dashboard_data.is_shared
        
    dashboard.version += 1
    db.commit()
    db.refresh(dashboard)
    return dashboard

@router.delete("/{dashboard_id}")
def delete_dashboard(
    dashboard_id: int, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to delete this dashboard")
        
    db.delete(dashboard)
    db.commit()
    return {"message": "Dashboard successfully deleted"}

# Widget Endpoints
@router.post("/{dashboard_id}/widgets", response_model=WidgetResponse)
def add_widget(
    dashboard_id: int, 
    widget_data: WidgetCreate, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    dashboard = db.query(Dashboard).filter_by(id=dashboard_id).first()
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
        
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to add widgets to this dashboard")
        
    new_widget = Widget(
        dashboard_id=dashboard_id,
        name=widget_data.name,
        type=widget_data.type,
        query_config=widget_data.query_config or {},
        visual_config=widget_data.visual_config or {}
    )
    
    db.add(new_widget)
    # Increment dashboard version
    dashboard.version += 1
    db.commit()
    db.refresh(new_widget)
    return new_widget

@router.put("/widgets/{widget_id}", response_model=WidgetResponse)
def update_widget(
    widget_id: int, 
    widget_data: WidgetUpdate, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    widget = db.query(Widget).filter_by(id=widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    dashboard = db.query(Dashboard).filter_by(id=widget.dashboard_id).first()
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to update this widget")
        
    if widget_data.name is not None:
        widget.name = widget_data.name
    if widget_data.type is not None:
        widget.type = widget_data.type
    if widget_data.query_config is not None:
        widget.query_config = widget_data.query_config
    if widget_data.visual_config is not None:
        widget.visual_config = widget_data.visual_config
        
    dashboard.version += 1
    db.commit()
    db.refresh(widget)
    return widget

@router.delete("/widgets/{widget_id}")
def delete_widget(
    widget_id: int, 
    db: Session = Depends(get_db_session), 
    current_user: User = Depends(get_current_user)
):
    widget = db.query(Widget).filter_by(id=widget_id).first()
    if not widget:
        raise HTTPException(status_code=404, detail="Widget not found")
        
    dashboard = db.query(Dashboard).filter_by(id=widget.dashboard_id).first()
    workspace = db.query(Workspace).filter_by(id=dashboard.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to delete this widget")
        
    db.delete(widget)
    dashboard.version += 1
    db.commit()
    return {"message": "Widget successfully deleted"}
