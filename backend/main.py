from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.db import init_db
from backend.api.auth import router as auth_router
from backend.api.datasets import router as datasets_router
from backend.api.dashboards import router as dashboards_router
from backend.api.etl import router as etl_router
from backend.api.ai import router as ai_router

# Initialize FastAPI App
app = FastAPI(
    title="Analyzer API",
    description="REST API Backend for Analyzer BI & AI Platform",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event to initialize SQLite tables & seed
@app.on_event("startup")
def startup_event():
    print("Starting Analyzer Platform backend...")
    init_db()

# Include Routers
app.include_router(auth_router)
app.include_router(datasets_router)
app.include_router(dashboards_router)
app.include_router(etl_router)
app.include_router(ai_router)

@app.get("/api/health")
def health_check():
    return {"status": "healthy", "service": "analyzer-api"}
