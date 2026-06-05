from typing import Dict, Any, List
from src.state import CyberRiskState

def fact_checker_node(state: CyberRiskState) -> Dict[str, Any]:
    evidence = state.get("collected_evidence", {})
    conflict_flags = state.get("conflict_flags", [])
    logs = []
    logs.append("Fact Checker: Evaluating claims and corroboration status...")

    claims = {}
    
    # Check Supervisor Entity Status
    if state.get("entity_status") == "Mismatch":
        conflict_flags.append({
            "parameter": "entity_resolution",
            "message": "Domain mismatch detected by Supervisor."
        })
        logs.append("Fact Checker Warning: ENTITY MISMATCH detected. Claims may be invalid.")
    
    # Unresolved Entity Detection
    sec_status = evidence.get("SECCollector", {}).get("status")
    db_status = evidence.get("DBCollector", {}).get("status")
    if sec_status in ["skipped", "error"] and db_status in ["skipped", "error"]:
        conflict_flags.append({
            "parameter": "entity_resolution",
            "message": "Unresolved Entity: Neither SEC nor GLEIF could locate this company."
        })
        logs.append("Fact Checker Warning: UNRESOLVED ENTITY detected.")
    
    def is_valid(src_name: str, key: str, is_revenue: bool = False) -> bool:
        val = evidence.get(src_name, {}).get("findings", {}).get(key)
        if val is None:
            return False
        if isinstance(val, list) and len(val) == 0:
            return False
        if is_revenue and isinstance(val, (int, float)) and val <= 0:
            return False
        if isinstance(val, str) and not val.strip():
            return False
        return True

    # 1. Fact-Check Revenue
    sources_rev = sum(1 for src in ["SECCollector", "DBCollector", "Wikipedia", "Wikidata"] if is_valid(src, "revenue", True))
    
    rev_conflict = any(flag["parameter"] == "revenue" for flag in conflict_flags)
    rev_partial = any(flag["parameter"] == "revenue_partial" for flag in conflict_flags)
    
    if rev_conflict:
        claims["revenue"] = {"status": "[X] Contradicted", "confidence": 0.0, "sources_count": sources_rev}
        logs.append("Fact Checker: Revenue claim is CONTRADICTED due to mismatch between sources.")
    elif rev_partial:
        claims["revenue"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_rev}
        logs.append("Fact Checker: Revenue claim has PARTIAL evidence (sources differ by <5x).")
    elif sources_rev >= 2:
        claims["revenue"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_rev}
        logs.append(f"Fact Checker: Revenue claim is VERIFIED by {sources_rev} sources.")
    elif sources_rev == 1:
        claims["revenue"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_rev}
        logs.append("Fact Checker: Revenue claim has PARTIAL evidence (only 1 source).")
    else:
        claims["revenue"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Revenue claim has NO evidence (Unsupported).")

    # 2. Fact-Check Subsidiaries
    sources_subs = sum(1 for src, key in [
        ("SECCollector", "subsidiaries_exhibit21"),
        ("Wikipedia", "subsidiaries"),
        ("Wikidata", "subsidiaries"),
        ("DBCollector", "parent_relationships")
    ] if is_valid(src, key))
        
    subs_conflict = any(flag["parameter"] == "subsidiaries" for flag in conflict_flags)
    subs_partial = any(flag["parameter"] == "subsidiaries_partial" for flag in conflict_flags)
    
    if subs_conflict:
        claims["subsidiaries"] = {"status": "[X] Contradicted", "confidence": 0.0, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim is CONTRADICTED due to count mismatch.")
    elif subs_partial:
        claims["subsidiaries"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim has PARTIAL evidence (counts vary but both >0).")
    elif sources_subs >= 2:
        claims["subsidiaries"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim is VERIFIED by 2 sources.")
    elif sources_subs == 1:
        claims["subsidiaries"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim has PARTIAL evidence.")
    else:
        claims["subsidiaries"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Subsidiaries claim has NO evidence (Unsupported).")

    # 3. Fact-Check Acquisitions
    sources_acq = sum(1 for src, key in [
        ("SECCollector", "sec_acquisitions"),
        ("WebSearch", "acquisitions"),
        ("Wikidata", "acquisitions"),
        ("Wikipedia", "acquisitions")
    ] if is_valid(src, key))
        
    if sources_acq >= 2:
        claims["acquisitions"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_acq}
        logs.append("Fact Checker: Acquisitions history is VERIFIED by 2 sources.")
    elif sources_acq == 1:
        claims["acquisitions"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_acq}
        logs.append("Fact Checker: Acquisitions history has PARTIAL evidence.")
    else:
        claims["acquisitions"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Acquisitions history has NO evidence (Unsupported).")

    # 4. Fact-Check HTTPS / Encryption
    has_domains = "DomainScraper" in evidence and evidence["DomainScraper"].get("status") == "success"
    if has_domains:
        claims["domain_encryption"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": 1}
        logs.append("Fact Checker: Domain encryption claim is VERIFIED via SSL probing.")
    else:
        claims["domain_encryption"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Domain encryption has no direct SSL verification (Unsupported).")

    # 5. Fact-Check Countries of Operation
    countries_sources = sum(1 for src, key in [
        ("ResponsesAPI", "countries_of_operation"),
        ("WebSearch", "countries_of_operation"),
        ("Wikipedia", "country"),
        ("Wikidata", "country"),
        ("DBCollector", "country")
    ] if is_valid(src, key))
        
    if countries_sources >= 2:
        claims["geographic_spread"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": countries_sources}
        logs.append("Fact Checker: Geographic spread claim is VERIFIED by 2 sources.")
    elif countries_sources == 1:
        claims["geographic_spread"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": countries_sources}
        logs.append("Fact Checker: Geographic spread has PARTIAL evidence.")
    else:
        claims["geographic_spread"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Geographic spread has NO evidence (Unsupported).")

    # 6. Fact-Check Customer Type & E-commerce
    cust_sources = sum(1 for src, key in [
        ("WebSearch", "customer_type"),
        ("ResponsesAPI", "customer_base_scale")
    ] if is_valid(src, key))
        
    if cust_sources >= 2:
        claims["sensitive_information"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": cust_sources}
        logs.append("Fact Checker: Sensitive information (Customer/E-commerce) claim is VERIFIED.")
    elif cust_sources == 1:
        claims["sensitive_information"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": cust_sources}
        logs.append("Fact Checker: Sensitive information claim has PARTIAL evidence.")
    else:
        claims["sensitive_information"] = {"status": "[X] Unsupported", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Sensitive information claim has NO evidence (Unsupported).")

    # Calculate Overall Accuracy Score
    scores = [c["confidence"] for c in claims.values()]
    accuracy_score = sum(scores) / len(scores) if scores else 0.0
    logs.append(f"Fact Checker: Calculated overall accuracy score = {accuracy_score:.2f}")

    return {
        "claims_verification": claims,
        "accuracy_score": accuracy_score,
        "conflict_flags": conflict_flags,
        "audit_logs": state.get("audit_logs", []) + logs
    }
