from connectors.base import BaseConnector

class DatabaseConnector(BaseConnector):
    def connect(self) -> bool:
        # If no host is provided, operate in mock mode
        if not self.params.get("host"):
            print(f"DatabaseConnector: Mock connection established for target parameters.")
            self.connection = "mock_connection_ref"
            return True
            
        # Actual engine setup (e.g. pg8000, pymysql) would occur here
        self.connection = "established"
        return True

    def fetch_data(self, query: str) -> dict:
        if self.connection == "mock_connection_ref":
            # Mock data return
            return {
                "columns": ["id", "source_name", "value_metric"],
                "data": [
                    [1, "Mock DB Segment A", 120.5],
                    [2, "Mock DB Segment B", 450.2],
                    [3, "Mock DB Segment C", 89.0]
                ]
            }
        return {"columns": [], "data": []}

    def close(self):
        self.connection = None

class PostgreSQLConnector(DatabaseConnector):
    pass

class MySQLConnector(DatabaseConnector):
    pass

class SnowflakeConnector(DatabaseConnector):
    pass
