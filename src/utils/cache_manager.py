import os
import json
from typing import Dict, Any, Optional

class CacheManager:
    def __init__(self, cache_path: str = "data/cache/company_cache.json"):
        self.cache_path = cache_path
        self._ensure_cache_exists()

    def _ensure_cache_exists(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        if not os.path.exists(self.cache_path):
            with open(self.cache_path, "w") as f:
                json.dump({}, f)

    def _load_cache(self) -> Dict[str, Any]:
        try:
            with open(self.cache_path, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, cache_data: Dict[str, Any]):
        with open(self.cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)

    def lookup(self, company_name: str, domain: str) -> Optional[Dict[str, Any]]:
        """
        3-tier lookup: Exact match > Fuzzy match > Domain match.
        """
        cache = self._load_cache()
        company_name_clean = company_name.lower().strip()
        domain_clean = domain.lower().strip()

        # 1. Exact Match (Name & Domain)
        for key, entry in cache.items():
            if entry.get("name", "").lower().strip() == company_name_clean and entry.get("domain", "").lower().strip() == domain_clean:
                return entry

        # 2. Fuzzy Match (Name similarity)
        for key, entry in cache.items():
            cached_name = entry.get("name", "").lower().strip()
            # Simple substring matching or exact equality of name
            if cached_name == company_name_clean or (len(company_name_clean) > 3 and company_name_clean in cached_name) or (len(cached_name) > 3 and cached_name in company_name_clean):
                return entry

        # 3. Domain Match
        for key, entry in cache.items():
            if entry.get("domain", "").lower().strip() == domain_clean:
                return entry

        return None

    def write(self, company_name: str, domain: str, profile_data: Dict[str, Any]):
        """Write or update a cache entry."""
        cache = self._load_cache()
        # Use company_name + domain as key
        key = f"{company_name} ({domain})"
        cache[key] = {
            "name": company_name,
            "domain": domain,
            **profile_data
        }
        self._save_cache(cache)
