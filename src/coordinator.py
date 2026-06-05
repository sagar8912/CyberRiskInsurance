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
    wikidata_findings = evidence.get("Wikidata", {}).get("findings", {})

    # Trust Ranking: SEC > DBCollector (GLEIF) > DomainScraper > Wikidata > Wikipedia > WebSearch
    
    # 1. Reconcile Revenue: SEC > GLEIF > Wikidata > Wikipedia
    sec_rev = sec_findings.get("revenue")
    if sec_rev is None and sec_findings.get("quarterly_revenue"):
        sec_rev = sum(sec_findings.get("quarterly_revenue"))
        
    db_rev = db_findings.get("revenue")
    wiki_rev = wiki_findings.get("revenue")
    wikidata_rev = wikidata_findings.get("revenue")
    
    if sec_rev is not None and sec_rev > 0:
        reconciled["revenue"] = sec_rev
        reconciled["revenue_source"] = "SEC"
        logs.append(f"Coordinator: Reconciled Revenue = ${sec_rev:,} (Source: SEC)")
    elif db_rev is not None and db_rev > 0:
        reconciled["revenue"] = db_rev
        reconciled["revenue_source"] = "GLEIF"
        logs.append(f"Coordinator: Reconciled Revenue = ${db_rev:,} (Source: GLEIF)")
    elif wikidata_rev is not None and wikidata_rev > 0:
        reconciled["revenue"] = wikidata_rev
        reconciled["revenue_source"] = "Wikidata"
        logs.append(f"Coordinator: Reconciled Revenue = ${wikidata_rev:,} (Source: Wikidata)")
    elif wiki_rev is not None and wiki_rev > 0:
        reconciled["revenue"] = wiki_rev
        reconciled["revenue_source"] = "Wikipedia"
        logs.append(f"Coordinator: Reconciled Revenue = ${wiki_rev:,} (Source: Wikipedia)")
    else:
        reconciled["revenue"] = None
        reconciled["revenue_source"] = "Not Available"
        logs.append("Coordinator: Reconciled Revenue = None (No source available)")

    # Conflict check on revenue
    raw_revenues = {"SEC": sec_rev, "GLEIF": db_rev, "Wikidata": wikidata_rev, "Wikipedia": wiki_rev}
    explicit_zeros = {k: v for k, v in raw_revenues.items() if v == 0}
    valid_revs = {k: v for k, v in raw_revenues.items() if v is not None and v > 0}
    
    is_contradicted = False
    contradiction_msg = ""
    
    # 1. Zero vs Very Large
    if len(valid_revs) >= 1 and len(explicit_zeros) >= 1:
        if max(valid_revs.values()) > 1000000:
            is_contradicted = True
            contradiction_msg = "One source reported 0 while another reported > $1M"

    # 2. Difference > 5x
    if len(valid_revs) > 1 and not is_contradicted:
        max_val = max(valid_revs.values())
        min_val = min(valid_revs.values())
        if min_val > 0 and max_val > 5 * min_val:
            is_contradicted = True
            contradiction_msg = f"Values differ by >5x (Max: {max_val}, Min: {min_val})"

    # 3. Fiscal year mismatch
    if not is_contradicted:
        fy_list = []
        if sec_findings.get("fiscal_year"): fy_list.append(int(sec_findings["fiscal_year"]))
        if db_findings.get("fiscal_year"): fy_list.append(int(db_findings["fiscal_year"]))
        if len(fy_list) >= 2 and (max(fy_list) - min(fy_list)) > 2:
            is_contradicted = True
            contradiction_msg = f"Fiscal years differ significantly: {fy_list}"
            
    # Emit flags
    if is_contradicted:
        conflict_flags.append({
            "parameter": "revenue",
            "message": f"Revenue contradiction: {contradiction_msg}. Sources: {raw_revenues}"
        })
        logs.append(f"Coordinator Warning: Revenue contradiction detected: {contradiction_msg}")
    elif len(valid_revs) > 1:
        max_val = max(valid_revs.values())
        min_val = min(valid_revs.values())
        if min_val > 0 and (max_val - min_val) / min_val > 0.2:
            conflict_flags.append({
                "parameter": "revenue_partial",
                "message": f"Revenue variance within 5x: {valid_revs}"
            })
            logs.append(f"Coordinator Warning: Revenue variance (partial match): {valid_revs}")

    # 2. Reconcile Subsidiaries: SEC > Wikidata + Wikipedia
    sec_subs = sec_findings.get("subsidiaries_exhibit21")
    wiki_subs = wiki_findings.get("subsidiaries", [])
    wikidata_subs = wikidata_findings.get("subsidiaries", [])
    
    # Combine Wikipedia and Wikidata subsidiaries if SEC is not available
    combined_wiki_subs = list(set(wiki_subs + wikidata_subs))
    
    if sec_subs is not None and len(sec_subs) > 0:
        reconciled["subsidiaries"] = sec_subs
        logs.append(f"Coordinator: Reconciled Subsidiaries count = {len(sec_subs)} (Source: SEC Exhibit 21)")
    elif combined_wiki_subs:
        reconciled["subsidiaries"] = combined_wiki_subs
        logs.append(f"Coordinator: Reconciled Subsidiaries count = {len(combined_wiki_subs)} (Source: Wikidata/Wikipedia)")
    else:
        reconciled["subsidiaries"] = []
        logs.append("Coordinator: Reconciled Subsidiaries count = 0")

    # Conflict check on subsidiaries
    if sec_subs is not None and combined_wiki_subs:
        sec_len = len(sec_subs)
        wiki_len = len(combined_wiki_subs)
        if sec_len == 0 and wiki_len > 10:
            conflict_flags.append({
                "parameter": "subsidiaries",
                "message": f"Subsidiaries contradiction: SEC=0 while Wiki={wiki_len}"
            })
            logs.append(f"Coordinator Warning: Subsidiaries contradiction (0 vs large): SEC=0, Wiki={wiki_len}")
        elif sec_len > 0 and wiki_len > 0 and sec_len != wiki_len:
            conflict_flags.append({
                "parameter": "subsidiaries_partial",
                "message": f"Subsidiaries partial variance: SEC={sec_len}, Wiki={wiki_len}"
            })
            logs.append(f"Coordinator Warning: Subsidiaries variance (partial match): SEC={sec_len}, Wiki={wiki_len}")

    # 3. Reconcile Acquisitions: deduplicate SEC and WebSearch
    sec_acq = sec_findings.get("sec_acquisitions", [])
    web_acq = web_findings.get("acquisitions", [])
    
    acq_set = set(sec_acq)
    acq_set.update(web_acq)
    
    if acq_set:
        reconciled["acquisitions"] = list(acq_set)
        logs.append(f"Coordinator: Reconciled Acquisitions count = {len(acq_set)} (Deduplicated)")
    else:
        reconciled["acquisitions"] = []
        logs.append("Coordinator: Reconciled Acquisitions count = 0")

    # 4. Reconcile Customer Type & E-commerce
    reconciled["customer_type"] = web_findings.get("customer_type") or resp_findings.get("customer_base_scale") or "B2B"
    reconciled["has_ecommerce"] = web_findings.get("has_ecommerce", False) or resp_findings.get("has_ecommerce", False)

    # 5. Reconcile Domain HTTPS status
    reconciled["domains"] = domain_findings.get("domains", [{"url": state.get("domain"), "https_encrypted": False}])
    reconciled["privacy_policy_published"] = domain_findings.get("privacy_policy_published", False)
    reconciled["compliance_mentions"] = domain_findings.get("compliance_mentions", [])

    # 6. Reconcile Geographic operations - Deduplication
    countries = set()
    if wiki_findings.get("country"):
        countries.add(wiki_findings.get("country"))
    if wikidata_findings.get("country"):
        countries.add(wikidata_findings.get("country"))
    if resp_findings.get("countries_of_operation"):
        countries.update(resp_findings.get("countries_of_operation"))
    if web_findings.get("countries_of_operation"):
        countries.update(web_findings.get("countries_of_operation"))
        
    if not countries:
        countries = {"USA"}
        
    reconciled["countries_of_operation"] = list(countries)
    reconciled["continent_spread"] = resp_findings.get("continent_spread") or ["North America"]
    reconciled["usa_presence"] = resp_findings.get("usa_presence") or ("USA" in reconciled["countries_of_operation"] or "United States" in reconciled["countries_of_operation"])
    logs.append(f"Coordinator: Reconciled Countries of Operation = {reconciled['countries_of_operation']}")

    # 6.5. Official Website Validation
    wikidata_website = wikidata_findings.get("official_website")
    if wikidata_website:
        provided_domain = state.get("domain", "").lower()
        # Extract domain from wikidata URL
        import urllib.parse
        parsed = urllib.parse.urlparse(wikidata_website)
        wiki_domain = parsed.netloc.lower()
        if wiki_domain.startswith("www."):
            wiki_domain = wiki_domain[4:]
            
        if provided_domain and provided_domain not in wiki_domain and wiki_domain not in provided_domain:
            conflict_flags.append({
                "parameter": "domain",
                "message": f"Provided domain '{provided_domain}' does not match Wikidata official website '{wikidata_website}'"
            })
            logs.append(f"Coordinator Warning: Domain mismatch. Provided: {provided_domain}, Wikidata: {wiki_domain}")

    # 7. Internet Footprint
    reconciled["internet_exposure_domains"] = resp_findings.get("internet_exposure_domains", len(reconciled["domains"]))
    reconciled["customer_base_scale"] = resp_findings.get("customer_base_scale", "SMB (<1k)")
    reconciled["services_appetite"] = resp_findings.get("services_appetite", "medium_risk")
    
    # 8. Volatility & Seasonality details
    reconciled["quarterly_revenue"] = sec_findings.get("quarterly_revenue") or web_findings.get("quarterly_revenue") or []
    reconciled["sic_codes"] = db_findings.get("sic_codes", [])
    reconciled["digital_exposure"] = web_findings.get("digital_exposure") or 3
    reconciled["disruption_speed"] = web_findings.get("disruption_speed") or 3
    reconciled["recovery_complexity"] = web_findings.get("recovery_complexity") or 3

    logs.append("Coordinator: Reconciled profile generated successfully.")

    return {
        "reconciled_profile": reconciled,
        "conflict_flags": conflict_flags,
        "audit_logs": state.get("audit_logs", []) + logs
    }
