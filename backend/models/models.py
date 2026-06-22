from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # Admin, Analyst, Viewer, Developer
    permissions = Column(JSON, nullable=True)  # JSON list of permission strings
    
    users = relationship("User", back_populates="role")

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    role = relationship("Role", back_populates="users")
    workspaces = relationship("Workspace", back_populates="owner")
    audit_logs = relationship("AuditLog", back_populates="user")

class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    owner = relationship("User", back_populates="workspaces")
    dashboards = relationship("Dashboard", back_populates="workspace")
    datasets = relationship("Dataset", back_populates="workspace")

class Dashboard(Base):
    __tablename__ = "dashboards"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    layout = Column(JSON, nullable=True)  # JSON representation of grid layout & widget references
    is_shared = Column(Boolean, default=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="dashboards")
    widgets = relationship("Widget", back_populates="dashboard", cascade="all, delete-orphan")

class Widget(Base):
    __tablename__ = "widgets"
    id = Column(Integer, primary_key=True, index=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # KPI, Bar, Line, Pie, Plotly, etc.
    query_config = Column(JSON, nullable=True)  # SQL queries or dataset field mapping
    visual_config = Column(JSON, nullable=True)  # Colors, dimensions, formatting parameters
    
    dashboard = relationship("Dashboard", back_populates="widgets")

class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # CSV/Parquet
    schema_info = Column(JSON, nullable=True)  # Column names, types, description
    workspace_id = Column(Integer, ForeignKey("workspaces.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("Workspace", back_populates="datasets")

class DataSource(Base):
    __tablename__ = "datasources"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # PostgreSQL, MySQL, CSV, Excel, etc.
    connection_params = Column(Text, nullable=True)  # Encrypted connection string parameters JSON
    created_at = Column(DateTime, default=datetime.utcnow)

class ETLJob(Base):
    __tablename__ = "etl_jobs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    definition = Column(JSON, nullable=False)  # Nodes and edges mapping the data transforms
    status = Column(String(20), default="Idle")  # Idle, Running, Success, Failed
    last_run = Column(DateTime, nullable=True)
    schedule = Column(String(50), nullable=True)  # Cron syntax string (e.g. "0 0 * * *")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    target_type = Column(String(50), nullable=True)
    target_id = Column(Integer, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")

class AIInsight(Base):
    __tablename__ = "ai_insights"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, nullable=False)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)  # Markdown text explaining findings
    category = Column(String(50), nullable=False)  # alert, prediction, opportunity, risk
    created_at = Column(DateTime, default=datetime.utcnow)

class Forecast(Base):
    __tablename__ = "forecasts"
    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, nullable=False)
    target_column = Column(String(100), nullable=False)
    date_column = Column(String(100), nullable=False)
    forecast_data = Column(JSON, nullable=False)  # Historic + predicted data values
    parameters = Column(JSON, nullable=True)  # Parameters used in ARIMA/Holt-Winters execution
    created_at = Column(DateTime, default=datetime.utcnow)
