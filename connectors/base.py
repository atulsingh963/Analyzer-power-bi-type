from abc import ABC, abstractmethod

class BaseConnector(ABC):
    def __init__(self, connection_params: dict):
        self.params = connection_params
        self.connection = None

    @abstractmethod
    def connect(self) -> bool:
        """Establishes connection to the target source."""
        pass

    @abstractmethod
    def fetch_data(self, query_or_path: str) -> dict:
        """Fetches data from source and returns columns and row list."""
        pass

    @abstractmethod
    def close(self):
        """Closes the connection."""
        pass
