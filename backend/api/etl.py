from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from database.db import get_db_session
from backend.models.models import ETLJob, User
from backend.auth.security import get_current_user
from etl.engine import etl_engine

router = APIRouter(prefix="/api/etl", tags=["etl"])

# Pydantic Schemas
class ETLJobCreate(BaseModel):
    name: str
    definition: Dict[str, Any]  # Nodes & Config
    schedule: Optional[str] = None

class ETLJobUpdate(BaseModel):
    name: Optional[str] = None
    definition: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None

class ETLJobResponse(BaseModel):
    id: int
    name: str
    definition: Dict[str, Any]
    status: str
    last_run: Optional[Any] = None
    schedule: Optional[str] = None
    class Config:
        from_attributes = True

@router.get("/jobs", response_model=List[ETLJobResponse])
def list_jobs(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    jobs = db.query(ETLJob).all()
    return jobs

@router.post("/jobs", response_model=ETLJobResponse)
def create_job(
    job_data: ETLJobCreate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.name not in ("Admin", "Analyst", "Developer"):
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges to create ETL jobs")
        
    new_job = ETLJob(
        name=job_data.name,
        definition=job_data.definition,
        schedule=job_data.schedule,
        status="Idle"
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job

@router.get("/jobs/{job_id}", response_model=ETLJobResponse)
def get_job(job_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    job = db.query(ETLJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
    return job

@router.put("/jobs/{job_id}", response_model=ETLJobResponse)
def update_job(
    job_id: int,
    job_data: ETLJobUpdate,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.name not in ("Admin", "Analyst", "Developer"):
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges to modify ETL jobs")
        
    job = db.query(ETLJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
        
    if job_data.name is not None:
        job.name = job_data.name
    if job_data.definition is not None:
        job.definition = job_data.definition
    if job_data.schedule is not None:
        job.schedule = job_data.schedule
        
    db.commit()
    db.refresh(job)
    return job

@router.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    if current_user.role.name not in ("Admin", "Analyst", "Developer"):
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges to delete ETL jobs")
        
    job = db.query(ETLJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
        
    db.delete(job)
    db.commit()
    return {"message": "ETL job successfully deleted"}

def run_etl_background(job_id: int):
    # Execute ETL job
    res = etl_engine.run_job(job_id)
    print(f"Background ETL execution for job {job_id} complete. Result: {res}")

@router.post("/jobs/{job_id}/run")
def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.name not in ("Admin", "Analyst", "Developer"):
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient privileges to execute ETL jobs")
        
    job = db.query(ETLJob).filter_by(id=job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="ETL Job not found")
        
    # Mark job as running
    job.status = "Running"
    db.commit()
    
    # Enqueue execution as background task
    background_tasks.add_task(run_etl_background, job_id)
    
    return {"message": "ETL job run started in the background", "status": "Running"}
