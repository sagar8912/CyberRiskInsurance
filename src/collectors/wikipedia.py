import json
import urllib.request
import urllib.parse
from typing import Dict, Any
from src.collectors.base import BaseCollector

class WikipediaCollector(BaseCollector):
    def __init__(self):
        super().__init__("Wikipedia")

    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        query = urllib.parse.quote(company_name)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json"
        
        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': 'CyberRiskAgent/1.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            search_results = data.get("query", {}).get("search", [])
            
            if not search_results:
                return {
                    "source": self.name,
                    "status": "skipped",
                    "is_mock": False,
                    "message": "No Wikipedia article found.",
                    "findings": {}
                }
                
            title = urllib.parse.quote(search_results[0]["title"])
            
            summary_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro&titles={title}&format=json"
            req2 = urllib.request.Request(summary_url, headers={'User-Agent': 'CyberRiskAgent/1.0'})
            with urllib.request.urlopen(req2, timeout=5) as response2:
                summary_data = json.loads(response2.read().decode())
            
            pages = summary_data.get("query", {}).get("pages", {})
            page = list(pages.values())[0] if pages else {}
            extract = page.get("extract", "").lower()
            
            findings = {}
            if "subsidiary" in extract or "subsidiaries" in extract:
                findings["subsidiaries"] = ["Detected via Wikipedia summary"]
            
            if "united states" in extract or "american" in extract:
                findings["country"] = "USA"
            elif "india" in extract or "indian" in extract:
                findings["country"] = "India"
                
            # Try to grab revenue from mock as Wikipedia extract usually doesn't have a parseable revenue
            # but we will just provide what we can
            return {
                "source": self.name,
                "status": "success",
                "is_mock": False,
                "findings": findings
            }
            
        except Exception as e:
            return {
                "source": self.name,
                "status": "error",
                "is_mock": False,
                "error": str(e),
                "findings": {}
            }
