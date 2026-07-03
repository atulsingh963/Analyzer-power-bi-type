import os
from datetime import datetime, timezone
import polars as pl
from sqlalchemy.orm import Session
from backend.models.models import Dataset, ETLJob, Workspace
from database.db import SessionLocal, LAKEHOUSE_DIR

class ETLEngine:
    def execute_nodes(self, definition: dict, db: Session) -> pl.DataFrame:
        """
        Executes a series of ETL pipeline operations using Polars.
        Supported Nodes:
        1. source: Reads raw Parquet/CSV dataset
        2. filter: Filters data based on comparisons (>, <, ==, contains)
        3. select: Retains a subset of columns
        4. groupby: Aggregates values using functions (sum, mean, count, max, min)
        """
        nodes = definition.get("nodes", [])
        df = None
        
        for node in nodes:
            node_type = node.get("type")
            config = node.get("config", {})
            
            if node_type == "source":
                ds_id = config.get("dataset_id")
                dataset = db.query(Dataset).filter_by(id=ds_id).first()
                if not dataset:
                    raise Exception(f"Source dataset with ID {ds_id} not found")
                
                if dataset.file_type.lower() == "parquet":
                    df = pl.read_parquet(dataset.file_path)
                else:
                    df = pl.read_csv(dataset.file_path)
                    
            elif node_type == "filter":
                if df is None:
                    raise Exception("Pipeline Error: Filter node ran before Source node")
                
                col = config.get("column")
                op = config.get("operator")
                val = config.get("value")
                
                if col not in df.columns:
                    raise Exception(f"Pipeline Error: Column '{col}' not found in dataset")
                
                # Apply filters safely
                if op == ">":
                    df = df.filter(pl.col(col) > float(val))
                elif op == "<":
                    df = df.filter(pl.col(col) < float(val))
                elif op == "==":
                    try:
                        fval = float(val)
                        df = df.filter(pl.col(col) == fval)
                    except ValueError:
                        df = df.filter(pl.col(col) == str(val))
                elif op == "contains":
                    df = df.filter(pl.col(col).str.contains(str(val)))
                else:
                    raise Exception(f"Pipeline Error: Unsupported filter operator '{op}'")
                    
            elif node_type == "select":
                if df is None:
                    raise Exception("Pipeline Error: Select node ran before Source node")
                
                cols = config.get("columns", [])
                # Ensure requested columns exist
                valid_cols = [c for c in cols if c in df.columns]
                if valid_cols:
                    df = df.select(valid_cols)
                    
            elif node_type == "groupby":
                if df is None:
                    raise Exception("Pipeline Error: Group By node ran before Source node")
                
                groupby_cols = config.get("groupby_cols", [])
                agg_col = config.get("agg_col")
                agg_func = config.get("agg_func", "sum").lower()
                
                # Validation
                missing_cols = [c for c in groupby_cols if c not in df.columns]
                if missing_cols:
                    raise Exception(f"Pipeline Error: Group By columns {missing_cols} not found")
                if agg_col not in df.columns:
                    raise Exception(f"Pipeline Error: Aggregate column '{agg_col}' not found")
                    
                # Create Polars aggregation expression
                if agg_func == "sum":
                    agg_expr = pl.col(agg_col).sum().alias(f"sum_{agg_col}")
                elif agg_func in ("mean", "avg"):
                    agg_expr = pl.col(agg_col).mean().alias(f"mean_{agg_col}")
                elif agg_func == "count":
                    agg_expr = pl.col(agg_col).count().alias(f"count_{agg_col}")
                elif agg_func == "max":
                    agg_expr = pl.col(agg_col).max().alias(f"max_{agg_col}")
                elif agg_func == "min":
                    agg_expr = pl.col(agg_col).min().alias(f"min_{agg_col}")
                else:
                    raise Exception(f"Pipeline Error: Unsupported aggregation function '{agg_func}'")
                    
                df = df.group_by(groupby_cols).agg(agg_expr)
                
        if df is None:
            raise Exception("Pipeline Error: No output generated")
            
        return df

    def run_job(self, job_id: int) -> dict:
        """
        Loads the ETLJob, executes the transformation steps, writes output to 
        Parquet Lakehouse (clean layer), and updates SQLite registries.
        """
        db = SessionLocal()
        job = db.query(ETLJob).filter_by(id=job_id).first()
        if not job:
            db.close()
            return {"success": False, "error": "Job not found"}
            
        try:
            job.status = "Running"
            db.commit()
            
            df = self.execute_nodes(job.definition, db)
            
            # Format output file
            clean_name = job.name.lower().strip().replace(" ", "_").replace("-", "_")
            output_path = os.path.abspath(os.path.join(LAKEHOUSE_DIR, "clean", f"{clean_name}.parquet"))
            
            # Write Polars DataFrame to Parquet
            df.write_parquet(output_path)
            
            # Fetch target Workspace (first available workspace)
            ws = db.query(Workspace).first()
            ws_id = ws.id if ws else 1
            
            # Generate schema information
            columns = [{"name": col, "type": str(dtype)} for col, dtype in df.schema.items()]
            schema_info = {"columns": columns}
            
            # Register or update dataset in SQLite
            dataset = db.query(Dataset).filter_by(name=job.name).first()
            if dataset:
                dataset.file_path = output_path
                dataset.schema_info = schema_info
            else:
                new_ds = Dataset(
                    name=job.name,
                    file_path=output_path,
                    file_type="parquet",
                    schema_info=schema_info,
                    workspace_id=ws_id
                )
                db.add(new_ds)
                
            job.status = "Success"
            job.last_run = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return {"success": True, "dataset_name": job.name, "rows": df.height}
            
        except Exception as e:
            db.rollback()
            job.status = "Failed"
            job.last_run = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return {"success": False, "error": str(e)}
        finally:
            db.close()

# Global instance
etl_engine = ETLEngine()
