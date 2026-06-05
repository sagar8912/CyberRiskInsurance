import os
from typing import Dict, Any
from src.collectors.base import BaseCollector

class WebSearchCollector(BaseCollector):
    def __init__(self):
        super().__init__("WebSearch")

    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        if not os.environ.get("BING_API_KEY"):
            return {
                "source": self.name,
                "status": "skipped",
                "is_mock": False,
                "message": "BING_API_KEY not found. WebSearch skipped.",
                "findings": {}
            }

        return {
            "source": self.name,
            "status": "skipped",
            "is_mock": False,
            "message": "BING_API_KEY found, but real Bing search is not implemented yet.",
            "findings": {}
        }
