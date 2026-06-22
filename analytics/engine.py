import os
import datetime
from decimal import Decimal
import duckdb
from sqlalchemy.orm import Session
from backend.models.models import Dataset

class AnalyticsEngine:
    def __init__(self):
        # Initialize an in-memory DuckDB database
        self.conn = duckdb.connect(database=":memory:")
        self.registered_tables = set()

    def get_clean_table_name(self, name: str) -> str:
        # Slugify name to make it a valid SQL table name
        return name.lower().strip().replace(" ", "_").replace("-", "_").replace(".", "_")

    def refresh_views(self, db: Session):
        """
        Queries SQLite to retrieve all registered datasets and maps their Parquet paths
        as views in DuckDB.
        """
        try:
            datasets = db.query(Dataset).all()
            current_tables = set()
            for ds in datasets:
                if os.path.exists(ds.file_path):
                    table_name = self.get_clean_table_name(ds.name)
                    # Create or replace views in DuckDB
                    # Use read_parquet for parquet, read_csv_auto for CSV
                    if ds.file_type.lower() == "parquet":
                        query = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{ds.file_path}')"
                    else:  # CSV fallback
                        query = f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{ds.file_path}')"
                    
                    self.conn.execute(query)
                    self.registered_tables.add(table_name)
                    current_tables.add(table_name)
            
            # Clean up views that are no longer in SQLite
            for old_table in list(self.registered_tables - current_tables):
                try:
                    self.conn.execute(f"DROP VIEW IF EXISTS {old_table}")
                    self.registered_tables.remove(old_table)
                except Exception:
                    pass
        except Exception as e:
            print(f"Error refreshing analytical views: {e}")

    def execute_query(self, query: str, db: Session = None):
        """
        Executes a SQL query in DuckDB. Automatically refreshes views if session is provided.
        """
        if db:
            self.refresh_views(db)
            
        try:
            rel = self.conn.execute(query)
            columns = [desc[0] for desc in rel.description]
            raw_rows = rel.fetchall()
            
            # Convert any non-serializable objects (datetime, Decimal, numpy types) to standard types
            formatted_data = []
            for row in raw_rows:
                formatted_data.append([self._format_value(val) for val in row])
                
            return {
                "success": True,
                "columns": columns,
                "data": formatted_data
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_table_schema(self, table_name: str) -> list:
        """
        Returns column name and data type for a registered table.
        """
        try:
            res = self.conn.execute(f"DESCRIBE {table_name}").fetchall()
            return [{"column_name": r[0], "data_type": r[1]} for r in res]
        except Exception:
            return []

    def _format_value(self, val):
        if val is None:
            return None
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.isoformat()
        if isinstance(val, Decimal):
            return float(val)
        # Handle numpy data types if numpy is returned
        if hasattr(val, "item") and callable(getattr(val, "item")):
            return val.item()
        return val

# Global instance
analytics_engine = AnalyticsEngine()
