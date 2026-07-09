import os
import json
from typing import Dict, Any, Optional

class CacheManager:
    def __init__(self, cache_path: str = "data/cache/company_cache.json", enabled: bool = True):
        self.cache_path = cache_path
        self.enabled = enabled
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
            if cached_name == company_name_clean or (len(company_name_clean) > 3 and company_name_clean in cached_name) or (len(cached_name) > 3 and cached_name in company_name_clean):
                return entry

        # 3. Domain Match
        for key, entry in cache.items():
            if entry.get("domain", "").lower().strip() == domain_clean:
                return entry

        return None

    def write(self, company_name: str, domain: str, profile_data: Dict[str, Any]):
        cache = self._load_cache()
        key = f"{company_name} ({domain})"
        cache[key] = {
            "name": company_name,
            "domain": domain,
            **profile_data
        }
        self._save_cache(cache)

_cache_instance = None

def get_cache_manager() -> CacheManager:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = CacheManager()
    return _cache_instance

class CachingCollectorWrapper:
    def __init__(self, base_collector: Any, source_type: str, rule_id: str, cache_manager: CacheManager):
        self.base_collector = base_collector
        self.source_type = source_type
        self.rule_id = rule_id
        self.cache_manager = cache_manager

    async def collect(self, company_name: str, domain: str, *args, **kwargs) -> Dict[str, Any]:
        from src.utils.logger import get_agent_logger
        agent_name = getattr(self.base_collector.config, 'name', self.source_type)
        logger = get_agent_logger(agent_name)
        
        logger.info(f"[{agent_name}] Starting data collection for {company_name} ({domain})")
        
        if self.cache_manager and self.cache_manager.enabled:
            cached = self.cache_manager.lookup(company_name, domain)
            if cached:
                evidence = cached.get("collected_evidence", {})
                source_mapping = {
                    "wikipedia": "Wikipedia",
                    "wikidata": "Wikidata",
                    "sec": "SECCollector",
                    "dnb": "DBCollector",
                    "domain": "DomainScraper",
                    "responses": "ResponsesAPI"
                }
                mapped_name = source_mapping.get(self.source_type, self.source_type)
                if mapped_name in evidence:
                    logger.info(f"[{agent_name}] Cache hit. Restored cached findings.")
                    res = evidence[mapped_name]
                    logger.info(f"[{agent_name}] Extraction complete (cached): status={res.get('status', 'success')}, findings={res.get('findings')}")
                    return res
                    
        logger.info(f"[{agent_name}] Cache miss. Executing live harvesting in background threadpool...")
        import asyncio
        def _runner():
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(self.base_collector.collect(company_name, domain, *args, **kwargs))
            finally:
                loop.close()
        result = await asyncio.to_thread(_runner)
        logger.info(f"[{agent_name}] Extraction complete: status={result.get('status')}, findings={result.get('findings')}")
        return result
