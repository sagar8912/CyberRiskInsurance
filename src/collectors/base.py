import os
import json
from typing import Dict, Any

class BaseCollector:
    def __init__(self, name: str):
        self.name = name
        self.mock_db_path = "data/mock_sources/mock_companies.json"

    def _get_mock_company_data(self, company_name: str) -> Dict[str, Any]:
        """Loads and returns mock data for the company if it exists, otherwise empty dict."""
        if os.path.exists(self.mock_db_path):
            try:
                with open(self.mock_db_path, "r") as f:
                    db = json.load(f)
                    return db.get(company_name, {})
            except Exception:
                pass
        return {}

    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        """
        Main collection execution method. Should be overridden by subclasses.
        Returns a dictionary representing the evidence report.
        """
        raise NotImplementedError("Subclasses must implement the collect method.")
