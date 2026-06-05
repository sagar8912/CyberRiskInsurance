from typing import Dict, Any, List
from src.state import CyberRiskState

def coordinator_node(state: CyberRiskState) -> Dict[str, Any]:
    evidence = state.get("collected_evidence", {})
    logs = []
    logs.append("Coordinator: Starting priority merge and conflict detection...")
    
    conflict_flags = []
    reconciled = {}

    # Extract collector results safely
    web_findings = evidence.get("WebSearch", {}).get("findings", {})
    domain_findings = evidence.get("DomainScraper", {}).get("findings", {})
    wiki_findings = evidence.get("Wikipedia", {}).get("findings", {})
    db_findings = evidence.get("DBCollector", {}).get("findings", {})
    sec_findings = evidence.get("SECCollector", {}).get("findings", {})
    resp_findings = evidence.get("ResponsesAPI", {}).get("findings", {})

    # 1. Reconcile Revenue: SEC > D&B > Wikipedia
    sec_rev = sec_findings.get("revenue")
    if sec_rev is None and sec_findings.get("quarterly_revenue"):
        # Sum quarterly revenues if available
        sec_rev = sum(sec_findings.get("quarterly_revenue"))
        
    db_rev = db_findings.get("revenue", 0)
    wiki_rev = wiki_findings.get("revenue", 0)
    
    if sec_rev is not None and sec_rev > 0:
        reconciled["revenue"] = sec_rev
        logs.append(f"Coordinator: Reconciled Revenue = ${sec_rev:,} (Source: SEC)")
    elif db_rev > 0:
        reconciled["revenue"] = db_rev
        logs.append(f"Coordinator: Reconciled Revenue = ${db_rev:,} (Source: D&B)")
    else:
        reconciled["revenue"] = wiki_rev
        logs.append(f"Coordinator: Reconciled Revenue = ${wiki_rev:,} (Source: Wikipedia)")

    # Conflict check on revenue
    revenues = {"SEC": sec_rev or 0, "D&B": db_rev, "Wikipedia": wiki_rev}
    valid_revs = {k: v for k, v in revenues.items() if v > 0}
    if len(valid_revs) > 1:
        vals = list(valid_revs.values())
        max_val = max(vals)
        min_val = min(vals)
        if min_val > 0 and (max_val - min_val) / min_val > 0.2:
            conflict_flags.append({
                "parameter": "revenue",
                "message": f"Revenue mismatch between sources: {valid_revs}"
            })
            logs.append(f"Coordinator Warning: Significant revenue mismatch detected across sources: {valid_revs}")

    # 2. Reconcile Subsidiaries: SEC > Wikipedia > D&B
    sec_subs = sec_findings.get("subsidiaries_exhibit21")
    wiki_subs = wiki_findings.get("subsidiaries")
    
    if sec_subs is not None:
        reconciled["subsidiaries"] = sec_subs
        logs.append(f"Coordinator: Reconciled Subsidiaries count = {len(sec_subs)} (Source: SEC Exhibit 21)")
    elif wiki_subs is not None:
        reconciled["subsidiaries"] = wiki_subs
        logs.append(f"Coordinator: Reconciled Subsidiaries count = {len(wiki_subs)} (Source: Wikipedia)")
    else:
        reconciled["subsidiaries"] = []
        logs.append("Coordinator: Reconciled Subsidiaries count = 0")

    # Conflict check on subsidiaries
    if sec_subs is not None and wiki_subs is not None:
        if abs(len(sec_subs) - len(wiki_subs)) > 5:
            conflict_flags.append({
                "parameter": "subsidiaries",
                "message": f"Subsidiary count mismatch: SEC={len(sec_subs)}, Wiki={len(wiki_subs)}"
            })
            logs.append(f"Coordinator Warning: Subsidiary count mismatch: SEC={len(sec_subs)}, Wiki={len(wiki_subs)}")

    # 3. Reconcile Acquisitions: SEC > WebSearch
    sec_acq = sec_findings.get("sec_acquisitions")
    web_acq = web_findings.get("acquisitions")
    
    if sec_acq is not None and len(sec_acq) > 0:
        reconciled["acquisitions"] = sec_acq
        logs.append(f"Coordinator: Reconciled Acquisitions count = {len(sec_acq)} (Source: SEC)")
    elif web_acq is not None:
        reconciled["acquisitions"] = web_acq
        logs.append(f"Coordinator: Reconciled Acquisitions count = {len(web_acq)} (Source: WebSearch)")
    else:
        reconciled["acquisitions"] = []
        logs.append("Coordinator: Reconciled Acquisitions count = 0")

    # 4. Reconcile Customer Type & E-commerce: WebSearch > ResponsesAPI
    reconciled["customer_type"] = web_findings.get("customer_type") or resp_findings.get("customer_base_scale") or "B2B"
    reconciled["has_ecommerce"] = web_findings.get("has_ecommerce", False) or resp_findings.get("has_ecommerce", False)
    logs.append(f"Coordinator: Reconciled Customer Type = '{reconciled['customer_type']}', Has E-commerce = {reconciled['has_ecommerce']}")

    # 5. Reconcile Domain HTTPS status: DomainScraper
    reconciled["domains"] = domain_findings.get("domains", [{"url": state.get("domain"), "https_encrypted": True}])
    reconciled["privacy_policy_published"] = domain_findings.get("privacy_policy_published", False)
    reconciled["compliance_mentions"] = domain_findings.get("compliance_mentions", [])
    logs.append(f"Coordinator: Reconciled Domains Count = {len(reconciled['domains'])}")

    # 6. Reconcile Geographic operations: ResponsesAPI > WebSearch
    reconciled["countries_of_operation"] = resp_findings.get("countries_of_operation") or web_findings.get("countries_of_operation") or ["USA"]
    reconciled["continent_spread"] = resp_findings.get("continent_spread") or ["North America"]
    reconciled["usa_presence"] = resp_findings.get("usa_presence") or (reconciled["countries_of_operation"] and "USA" in reconciled["countries_of_operation"])
    logs.append(f"Coordinator: Reconciled Countries of Operation = {reconciled['countries_of_operation']}")

    # 7. Internet Footprint, Customer Scale, and Services
    reconciled["internet_exposure_domains"] = resp_findings.get("internet_exposure_domains", len(reconciled["domains"]))
    reconciled["customer_base_scale"] = resp_findings.get("customer_base_scale", "SMB (<1k)")
    reconciled["services_appetite"] = resp_findings.get("services_appetite", "medium_risk")
    
    # 8. Volatility & Seasonality details
    reconciled["quarterly_revenue"] = sec_findings.get("quarterly_revenue") or web_findings.get("quarterly_revenue") or []
    reconciled["sic_codes"] = db_findings.get("sic_codes", ["7372"])
    reconciled["digital_exposure"] = web_findings.get("digital_exposure") or 3
    reconciled["disruption_speed"] = web_findings.get("disruption_speed") or 3
    reconciled["recovery_complexity"] = web_findings.get("recovery_complexity") or 3

    logs.append("Coordinator: Reconciled profile generated successfully.")

    return {
        "reconciled_profile": reconciled,
        "conflict_flags": conflict_flags,
        "audit_logs": state.get("audit_logs", []) + logs
    }
