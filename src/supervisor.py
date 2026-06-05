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

    # 3. Mismatch Detection
    mismatch_flag = False
    name_lower = name.lower()
    domain_lower = domain.lower()
    
    # Heuristic mismatch check
    for keyword, wrong_indicators in WRONG_ENTITY_KEYWORDS.items():
        if keyword in name_lower:
            for indicator in wrong_indicators:
                if indicator in domain_lower:
                    mismatch_flag = True
                    logs.append(f"Supervisor Warning: Entity mismatch detected! Name has '{keyword}' but domain '{domain}' suggests '{indicator}'.")
                    break

    # 4. Cache Lookup
    cache_mgr = CacheManager()
    cache_entry = cache_mgr.lookup(name, domain)
    cache_hit = cache_entry is not None
    
    if cache_hit:
        logs.append("Supervisor: 3-Tier Cache Hit! Exact/Fuzzy/Domain record found.")
    else:
        logs.append("Supervisor: Cache Miss. Proceeding to Revenue Router.")

    return {
        "valid": True,
        "enrichment": enrichment,
        "mismatch_flag": mismatch_flag,
        "cache_hit": cache_hit,
        "cache_data": cache_entry if cache_hit else None,
        "audit_logs": state.get("audit_logs", []) + logs
    }
