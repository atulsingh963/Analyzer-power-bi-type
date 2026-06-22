import os
import pandas as pd
from connectors.base import BaseConnector

class FileConnector(BaseConnector):
    def connect(self) -> bool:
        path = self.params.get("file_path")
        if not path or not os.path.exists(path):
            return False
        return True

    def fetch_data(self, query_or_path: str = None) -> dict:
        path = query_or_path or self.params.get("file_path")
        if not path or not os.path.exists(path):
            return {"error": "Target file path not found"}
            
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == ".csv":
                df = pd.read_csv(path, nrows=100)
            elif ext in (".xls", ".xlsx"):
                df = pd.read_excel(path, nrows=100)
            else:
                return {"error": "Unsupported file extension"}
                
            return {
                "columns": list(df.columns),
                "data": df.values.tolist()
            }
        except Exception as e:
            return {"error": f"Failed to parse file: {str(e)}"}

    def close(self):
        pass
