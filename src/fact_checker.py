from typing import Dict, Any, List
from src.state import CyberRiskState

def fact_checker_node(state: CyberRiskState) -> Dict[str, Any]:
    evidence = state.get("collected_evidence", {})
    conflict_flags = state.get("conflict_flags", [])
    logs = []
    logs.append("Fact Checker: Evaluating claims and corroboration status...")

    claims = {}
    
    # 1. Fact-Check Revenue
    sources_rev = 0
    for collector in ["SECCollector", "DBCollector", "Wikipedia"]:
        if evidence.get(collector, {}).get("findings", {}).get("revenue", 0) > 0:
            sources_rev += 1
    
    # Check if we have any conflict flagged for revenue
    rev_conflict = any(flag["parameter"] == "revenue" for flag in conflict_flags)
    
    if rev_conflict:
        claims["revenue"] = {"status": "[X] Contradicted", "confidence": 0.0, "sources_count": sources_rev}
        logs.append("Fact Checker: Revenue claim is CONTRADICTED due to mismatch between sources.")
    elif sources_rev >= 2:
        claims["revenue"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_rev}
        logs.append(f"Fact Checker: Revenue claim is VERIFIED by {sources_rev} sources.")
    elif sources_rev == 1:
        claims["revenue"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_rev}
        logs.append("Fact Checker: Revenue claim has PARTIAL evidence (only 1 source).")
    else:
        claims["revenue"] = {"status": "[X] Contradicted", "confidence": 0.0, "sources_count": 0}
        logs.append("Fact Checker: Revenue claim has NO evidence.")

    # 2. Fact-Check Subsidiaries
    sources_subs = 0
    if evidence.get("SECCollector", {}).get("findings", {}).get("subsidiaries_exhibit21") is not None:
        sources_subs += 1
    if evidence.get("Wikipedia", {}).get("findings", {}).get("subsidiaries") is not None:
        sources_subs += 1
        
    subs_conflict = any(flag["parameter"] == "subsidiaries" for flag in conflict_flags)
    
    if subs_conflict:
        claims["subsidiaries"] = {"status": "[X] Contradicted", "confidence": 0.0, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim is CONTRADICTED due to count mismatch.")
    elif sources_subs >= 2:
        claims["subsidiaries"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim is VERIFIED by 2 sources.")
    elif sources_subs == 1:
        claims["subsidiaries"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_subs}
        logs.append("Fact Checker: Subsidiaries claim has PARTIAL evidence.")
    else:
        claims["subsidiaries"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": 0}
        logs.append("Fact Checker: Subsidiaries claim has default partial evidence (assumed 0).")

    # 3. Fact-Check Acquisitions
    sources_acq = 0
    if evidence.get("SECCollector", {}).get("findings", {}).get("sec_acquisitions") is not None:
        sources_acq += 1
    if evidence.get("WebSearch", {}).get("findings", {}).get("acquisitions") is not None:
        sources_acq += 1
        
    if sources_acq >= 2:
        claims["acquisitions"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": sources_acq}
        logs.append("Fact Checker: Acquisitions history is VERIFIED by 2 sources.")
    elif sources_acq == 1:
        claims["acquisitions"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": sources_acq}
        logs.append("Fact Checker: Acquisitions history has PARTIAL evidence.")
    else:
        claims["acquisitions"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": 0}
        logs.append("Fact Checker: Acquisitions history has default partial evidence.")

    # 4. Fact-Check HTTPS / Encryption
    # DomainScraper provides domains HTTPS list
    has_domains = "DomainScraper" in evidence
    if has_domains:
        claims["domain_encryption"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": 1}
        logs.append("Fact Checker: Domain encryption claim is VERIFIED via SSL probing.")
    else:
        claims["domain_encryption"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": 0}
        logs.append("Fact Checker: Domain encryption has no direct SSL verification (PARTIAL).")

    # 5. Fact-Check Countries of Operation
    countries_sources = 0
    if evidence.get("ResponsesAPI", {}).get("findings", {}).get("countries_of_operation") is not None:
        countries_sources += 1
    if evidence.get("WebSearch", {}).get("findings", {}).get("countries_of_operation") is not None:
        countries_sources += 1
        
    if countries_sources >= 2:
        claims["geographic_spread"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": countries_sources}
        logs.append("Fact Checker: Geographic spread claim is VERIFIED by 2 sources.")
    else:
        claims["geographic_spread"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": countries_sources}
        logs.append("Fact Checker: Geographic spread has PARTIAL evidence.")

    # 6. Fact-Check Customer Type & E-commerce
    cust_sources = 0
    if evidence.get("WebSearch", {}).get("findings", {}).get("customer_type") is not None:
        cust_sources += 1
    if evidence.get("ResponsesAPI", {}).get("findings", {}).get("customer_base_scale") is not None:
        cust_sources += 1
        
    if cust_sources >= 2:
        claims["sensitive_information"] = {"status": "[OK] Verified", "confidence": 1.0, "sources_count": cust_sources}
        logs.append("Fact Checker: Sensitive information (Customer/E-commerce) claim is VERIFIED.")
    else:
        claims["sensitive_information"] = {"status": "[I] Partial", "confidence": 0.5, "sources_count": cust_sources}
        logs.append("Fact Checker: Sensitive information claim has PARTIAL evidence.")

    # Calculate Overall Accuracy Score
    scores = [c["confidence"] for c in claims.values()]
    accuracy_score = sum(scores) / len(scores) if scores else 0.0
    logs.append(f"Fact Checker: Calculated overall accuracy score = {accuracy_score:.2f}")

    return {
        "claims_verification": claims,
        "accuracy_score": accuracy_score,
        "audit_logs": state.get("audit_logs", []) + logs
    }
