from typing import Dict, Any
from src.state import CyberRiskState
from src.utils.cache_manager import CacheManager

# Hardcoded mismatch detection signals
WRONG_ENTITY_KEYWORDS = {
    "amazon": ["river", "forest", "rainforest"],
    "apple": ["fruit", "orchard", "pie", "cider"],
    "microsoft": ["microbiology", "softball"],
}

def supervisor_node(state: CyberRiskState) -> Dict[str, Any]:
    name = state.get("company_name", "").strip()
    domain = state.get("domain", "").strip()
    
    logs = []
    logs.append(f"Supervisor: Validating input - Name: '{name}', Domain: '{domain}'")
    
    # 1. Validation check
    if not name or not domain or "." not in domain:
        logs.append("Supervisor Reject: Invalid company name or domain format.")
        return {
            "valid": False,
            "mismatch_flag": False,
            "cache_hit": False,
            "enrichment": {},
            "audit_logs": state.get("audit_logs", []) + logs
        }
        
    # 2. Enrich Domain / Country & TLD
    tld = domain.split(".")[-1].lower()
    country = "USA"  # Default
    if tld == "ca":
        country = "Canada"
    elif tld == "uk":
        country = "UK"
    elif tld == "de":
        country = "Germany"
    elif tld == "in":
        country = "India"
        
    enrichment = {
        "tld": tld,
        "country_detected": country
    }
    logs.append(f"Supervisor: Enriched TLD: '{tld}', Detected Country: '{country}'")

    # 3. Mismatch Detection via API
    mismatch_flag = False
    entity_status = "Match"
    entity_resolution_confidence = "High"
    
    import urllib.request
    import urllib.parse
    import json
    
    domain_lower = domain.lower()
    expected_domain = None
    
    # Check Wikipedia
    try:
        query = urllib.parse.quote(name)
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extlinks&titles={query}&format=json"
        req = urllib.request.Request(url, headers={'User-Agent': 'CyberRiskBot/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            pages = data.get("query", {}).get("pages", {})
            for page_id, page_data in pages.items():
                extlinks = page_data.get("extlinks", [])
                
                # Check if provided domain is in Wikipedia links
                found_match = False
                for link in extlinks:
                    url_str = link.get("*", "").lower()
                    if domain_lower in url_str:
                        found_match = True
                        break
                        
                if not found_match and extlinks:
                    # Try to extract a plausible domain
                    ignore_domains = ["twitter.com", "facebook.com", "linkedin.com", "youtube.com", "instagram.com", "bloomberg.com", "reuters.com"]
                    for link in extlinks:
                        url_str = link.get("*", "").lower()
                        parts = urllib.parse.urlparse(url_str)
                        netloc = parts.netloc.lower()
                        if netloc.startswith("www."):
                            netloc = netloc[4:]
                        if not any(ig in netloc for ig in ignore_domains):
                            expected_domain = netloc
                            break
    except Exception:
        pass
        
    if expected_domain is None:
        expected_domain = f"{name.lower().replace(' ', '')}.com"
        
    # Heuristic: if domain provided is completely unrelated to the name and expected domain
    name_slug = name.lower().replace(" ", "")
    if name_slug not in domain_lower and domain_lower not in expected_domain and not any(part in domain_lower for part in name.lower().split()):
        mismatch_flag = True
        entity_status = "Mismatch"
        entity_resolution_confidence = "Low"
        logs.append(f"Supervisor: Domain mismatch detected.\nExpected domain: {expected_domain}\nProvided domain: {domain}")

    # 4. Cache Lookup
    cache_mgr = CacheManager()
    cache_entry = cache_mgr.lookup(name, domain)
    cache_hit = cache_entry is not None
    
    collected_evidence = {}
    if cache_hit:
        logs.append("Supervisor: Collector Cache Hit. Loading cached collector evidence.")
        logs.append("Collectors: Skipped network calls due to collector cache.")
        collected_evidence = cache_entry.get("collected_evidence", {})
    else:
        logs.append("Supervisor: Cache Miss. Proceeding to Revenue Router.")

    return {
        "valid": True,
        "enrichment": enrichment,
        "mismatch_flag": mismatch_flag,
        "entity_status": entity_status,
        "entity_resolution_confidence": entity_resolution_confidence,
        "cache_hit": cache_hit,
        "cache_data": cache_entry if cache_hit else None,
        "collected_evidence": collected_evidence,
        "audit_logs": state.get("audit_logs", []) + logs
    }
