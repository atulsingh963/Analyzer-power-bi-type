import os
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models.models import Base, Role, User, Workspace, Dataset, Dashboard, Widget

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(DATA_DIR, "db")
LAKEHOUSE_DIR = os.path.join(DATA_DIR, "lakehouse")

# Create folders if they do not exist
os.makedirs(DB_DIR, exist_ok=True)
for layer in ["raw", "clean", "curated"]:
    os.makedirs(os.path.join(LAKEHOUSE_DIR, layer), exist_ok=True)

# Database connection URL (SQLite by default)
DATABASE_URL = f"sqlite:///{os.path.join(DB_DIR, 'analyzer.db')}"

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Necessary for SQLite and FastAPI multi-threading
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    # Create all tables in the database
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if roles are already seeded
        if db.query(Role).count() == 0:
            print("Seeding database roles...")
            roles = [
                Role(name="Admin", permissions=["all"]),
                Role(name="Analyst", permissions=["read", "write", "visualize", "forecast"]),
                Role(name="Viewer", permissions=["read"]),
                Role(name="Developer", permissions=["read", "write", "etl", "develop"])
            ]
            db.add_all(roles)
            db.commit()
            
        # Get admin role
        admin_role = db.query(Role).filter_by(name="Admin").first()
        
        # Check if default admin user is seeded
        if db.query(User).filter_by(username="admin").count() == 0:
            print("Seeding default admin user...")
            password = "admin123"
            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            
            admin_user = User(
                username="admin",
                email="admin@analyzer.local",
                hashed_password=hashed_pw,
                role_id=admin_role.id,
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            
            # Create a default workspace for the admin user
            admin_user = db.query(User).filter_by(username="admin").first()
            default_workspace = Workspace(
                name="Default Workspace",
                description="Your default workspace for dashboarding and data analytics.",
                owner_id=admin_user.id
            )
            db.add(default_workspace)
            db.commit()
            
            # Seed default datasets if they exist and are not registered
            sales_path = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "raw", "store_sales.parquet"))
            web_path = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "raw", "web_metrics.parquet"))
            
            # Check if file exists to register it
            if os.path.exists(sales_path):
                db.add(Dataset(
                    name="Store Sales",
                    file_path=sales_path,
                    file_type="parquet",
                    schema_info={"columns": [
                        {"name": "transaction_id", "type": "Int64"},
                        {"name": "date", "type": "String"},
                        {"name": "store_id", "type": "Int64"},
                        {"name": "store_name", "type": "String"},
                        {"name": "product_category", "type": "String"},
                        {"name": "unit_price", "type": "Float64"},
                        {"name": "units_sold", "type": "Int64"},
                        {"name": "sales_amount", "type": "Float64"},
                        {"name": "customer_gender", "type": "String"},
                        {"name": "customer_age", "type": "Int64"}
                    ]},
                    workspace_id=default_workspace.id
                ))
            if os.path.exists(web_path):
                db.add(Dataset(
                    name="Web Metrics",
                    file_path=web_path,
                    file_type="parquet",
                    schema_info={"columns": [
                        {"name": "session_id", "type": "String"},
                        {"name": "timestamp", "type": "String"},
                        {"name": "visitor_id", "type": "String"},
                        {"name": "page_path", "type": "String"},
                        {"name": "device", "type": "String"},
                        {"name": "traffic_source", "type": "String"},
                        {"name": "session_duration_sec", "type": "Float64"},
                        {"name": "is_bounce", "type": "Boolean"}
                    ]},
                    workspace_id=default_workspace.id
                ))
            db.commit()
            
            # Seed default dashboard and widgets
            if db.query(Dashboard).count() == 0:
                print("Seeding default Executive Sales Summary dashboard...")
                sales_ds = db.query(Dataset).filter_by(name="Store Sales").first()
                if sales_ds:
                    default_dashboard = Dashboard(
                        name="Executive Sales Summary",
                        description="Pre-built executive dashboard showing daily revenue trends and category performance.",
                        workspace_id=default_workspace.id,
                        is_shared=True,
                        layout={},
                        version=1
                    )
                    db.add(default_dashboard)
                    db.commit()
                    db.refresh(default_dashboard)
                    
                    widget1 = Widget(
                        dashboard_id=default_dashboard.id,
                        name="Daily Sales Trend",
                        type="line",
                        query_config={
                            "use_custom_sql": False,
                            "dataset_id": sales_ds.id,
                            "x_col": "date",
                            "y_col": "sales_amount"
                        },
                        visual_config={}
                    )
                    widget2 = Widget(
                        dashboard_id=default_dashboard.id,
                        name="Category Breakdown",
                        type="bar",
                        query_config={
                            "use_custom_sql": False,
                            "dataset_id": sales_ds.id,
                            "x_col": "product_category",
                            "y_col": "sales_amount"
                        },
                        visual_config={}
                    )
                    db.add_all([widget1, widget2])
                    db.commit()
            print("Seeding complete.")
            
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
