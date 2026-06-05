import json
import urllib.request
import urllib.parse
from typing import Dict, Any
from src.collectors.base import BaseCollector

class DBCollector(BaseCollector):
    def __init__(self):
        super().__init__("DBCollector")

    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        query = urllib.parse.quote(company_name)
        url = f"https://api.gleif.org/api/v1/fuzzycompletions?field=entity.legalName&q={query}"
        
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                
            if data.get("data") and len(data["data"]) > 0:
                item = data["data"][0]
                attrs = item.get("attributes", {})
                entity = attrs.get("entity", {})
                
                legal_name = entity.get("legalName", {}).get("name")
                lei = attrs.get("lei")
                entity_status = entity.get("status")
                
                legal_address = entity.get("legalAddress", {})
                headquarters_address = entity.get("headquartersAddress", {})
                country = legal_address.get("country") or headquarters_address.get("country")
                
                registration_authority = entity.get("registrationAuthority", {})
                legal_form = entity.get("legalForm", {})
                
                parent_relationships = item.get("relationships", {})
                
                return {
                    "source": self.name,
                    "status": "success",
                    "is_mock": False,
                    "source_type": "gleif",
                    "source_weight": 0.95,
                    "findings": {
                        "legal_name": legal_name,
                        "lei": lei,
                        "entity_status": entity_status,
                        "country": country,
                        "legal_address": legal_address,
                        "headquarters_address": headquarters_address,
                        "registration_authority": registration_authority,
                        "legal_form": legal_form,
                        "parent_relationships": parent_relationships,
                        "sic_codes": [],
                        "sic_source": "not_available_in_gleif",
                        "revenue": None,
                        "revenue_source": "not_available_in_gleif",
                        "employees": None
                    }
                }
            else:
                return {
                    "source": self.name,
                    "status": "skipped",
                    "is_mock": False,
                    "message": "No GLEIF entity found",
                    "findings": {}
                }
        except Exception as e:
            return {
                "source": self.name,
                "status": "error",
                "is_mock": False,
                "error": str(e),
                "findings": {}
            }
