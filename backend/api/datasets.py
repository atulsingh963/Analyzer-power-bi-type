import os
import shutil
import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from database.db import get_db_session, LAKEHOUSE_DIR
from backend.models.models import Dataset, Workspace, User
from backend.auth.security import get_current_user
from etl.quality import get_dataset_quality_metrics

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

@router.get("")
def list_datasets(db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    # In a multi-tenant workspace architecture, we fetch datasets in the user's workspaces
    # For now, list all datasets in workspace(s) owned by user, or all if admin
    if current_user.role.name == "Admin":
        datasets = db.query(Dataset).all()
    else:
        # Fetch workspaces owned by user
        workspaces = db.query(Workspace).filter_by(owner_id=current_user.id).all()
        workspace_ids = [w.id for w in workspaces]
        datasets = db.query(Dataset).filter(Dataset.workspace_id.in_(workspace_ids)).all()
        
    return [
        {
            "id": ds.id,
            "name": ds.name,
            "file_path": ds.file_path,
            "file_type": ds.file_type,
            "schema_info": ds.schema_info,
            "workspace_id": ds.workspace_id,
            "created_at": ds.created_at.isoformat()
        }
        for ds in datasets
    ]

@router.post("/upload")
async def upload_dataset(
    name: str = Form(...),
    workspace_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    # Verify workspace exists and user has access
    workspace = db.query(Workspace).filter_by(id=workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to upload to this workspace")
        
    # Check file extension
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".csv", ".parquet"]:
        raise HTTPException(status_code=400, detail="Only CSV and Parquet files are supported")
        
    file_type = "parquet" if ext == ".parquet" else "csv"
    
    # Save the file to the raw lakehouse layer
    save_dir = os.path.join(LAKEHOUSE_DIR, "raw")
    os.makedirs(save_dir, exist_ok=True)
    
    # Clean filename
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (".", "_", "-")).strip()
    file_path = os.path.abspath(os.path.join(save_dir, safe_filename))
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
    # Infer schema using Polars
    try:
        if file_type == "parquet":
            df = pl.read_parquet(file_path, n_rows=5)
        else:
            df = pl.read_csv(file_path, n_rows=5)
            
        columns = [{"name": col, "type": str(dtype)} for col, dtype in df.schema.items()]
        schema_info = {"columns": columns}
    except Exception as e:
        # Cleanup file on schema inference failure
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid file content or format: {str(e)}")
        
    # Register dataset in SQLite
    new_dataset = Dataset(
        name=name,
        file_path=file_path,
        file_type=file_type,
        schema_info=schema_info,
        workspace_id=workspace_id
    )
    
    db.add(new_dataset)
    db.commit()
    db.refresh(new_dataset)
    
    return {
        "id": new_dataset.id,
        "name": new_dataset.name,
        "file_type": new_dataset.file_type,
        "schema_info": new_dataset.schema_info,
        "file_path": new_dataset.file_path,
        "message": "Dataset successfully uploaded and registered"
    }

@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int, db: Session = Depends(get_db_session), current_user: User = Depends(get_current_user)):
    dataset = db.query(Dataset).filter_by(id=dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # Verify owner permission or admin bypass
    workspace = db.query(Workspace).filter_by(id=dataset.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to delete this dataset")
        
    # Remove file from disk
    if os.path.exists(dataset.file_path):
        try:
            os.remove(dataset.file_path)
        except Exception as e:
            print(f"Warning: failed to delete file {dataset.file_path}: {e}")
            
    # Delete from database
    db.delete(dataset)
    db.commit()
    
    return {"message": "Dataset successfully deleted"}

@router.get("/{dataset_id}/quality")
def get_dataset_quality(
    dataset_id: int,
    db: Session = Depends(get_db_session),
    current_user: User = Depends(get_current_user)
):
    dataset = db.query(Dataset).filter_by(id=dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
        
    # Verify owner permission or admin bypass
    workspace = db.query(Workspace).filter_by(id=dataset.workspace_id).first()
    if current_user.role.name != "Admin" and workspace.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden to view this dataset's quality metrics")
        
    metrics = get_dataset_quality_metrics(dataset.file_path, dataset.file_type)
    if "error" in metrics:
        raise HTTPException(status_code=500, detail=metrics["error"])
        
    return metrics
