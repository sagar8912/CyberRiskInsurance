import json
import re
import numpy as np
from datetime import datetime
from typing import Dict, Any, List
from src.base_agents import BaseCoordinatorAgent, BaseFactCheckerAgent, BaseUnderwriterAgent

RATING_SCORES = {
    "very favourable": 1.0,
    "favourable": 2.0,
    "partially favourable": 3.0,
    "average": 4.0,
    "partially unfavourable": 5.0,
    "unfavourable": 6.0
}

class CollectionCoordinatorAgent(BaseCoordinatorAgent):
    async def coordinate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reports = state.get("reports", {})
        company_name = state.get("company_name")
        domain = state.get("domain")
        logs = []
        logs.append("Coordinator: Initiating prioritized source merge...")
        
        logger = self.get_logger()
        logger.info("********************************************")
        logger.info("[COLLECTION COORDINATOR] Starting Data Reconciliation Process")
        logger.info("********************************************")
        logger.info("Analyzing input context...")
        logger.info(f"- Company Name: {company_name}")
        logger.info(f"- Domain: {domain}")
        logger.info(f"- Number of reports received: {len(reports)}")
        logger.info(f"- Report sources: {sorted(list(reports.keys()))}")

        # Priority mappings for fields
        merged = {
            "revenue": None,
            "subsidiaries": [],
            "acquisitions": [],
            "customer_type": "B2B",
            "has_ecommerce": False,
            "domains": [{"url": domain, "https_encrypted": False}],
            "countries_of_operation": ["USA"],
            "continent_spread": ["North America"],
            "usa_presence": True,
            "privacy_policy_published": False,
            "compliance_mentions": [],
            "quarterly_revenue": [],
            "sic_codes": ["7372"],
            "sub_industries": [],
            "worst_sub_industry_appetite": "acceptable",
            "services_appetite": "medium_risk",
            "internet_exposure_domains": 1,
            "customer_base_scale": "SMB (<1k)",
            "estimated_customers_count": 100000,
            "digital_exposure": 3,
            "disruption_speed": 3,
            "recovery_complexity": 3,
            "founding_year": None,
            "has_cyber_breach": False,
            "has_active_litigation": False,
            "ftc_actions_count": 0,
            "detected_technologies": [],
            "ssl_grade": None,
            "cybersecurity_frameworks": [],
            "has_dmarc_spf": True,
            "has_security_headers": True,
            "has_security_txt": False,
            "has_ciso_disclosure": False,
            "company_breaches": [],
            "industry_breach_tier": "Moderate",
            "naics_code": None,
            "naics_description": None,
            "country": None
        }

        # 1. Merge logic with priority: SEC > GLEIF/DBCollector > Wikidata > Wikipedia > ResponsesAPI > GDELT > CourtListener > SSLLabs > FTC > Wappalyzer > CensusNAICS
        sources_order = [
            "SECCollector", "DBCollector", "Wikidata", "Wikipedia", 
            "ResponsesAPI", "DomainScraper", "GDELT", "CourtListener", "SSLLabs", "FTC", 
            "Wappalyzer", "CensusNAICS"
        ]

        # Check if we should skip SECCollector
        skip_sec = state.get("skip_sec", False)
        sec_report = reports.get("SECCollector", {})
        if skip_sec or sec_report.get("status") == "skipped":
            if "SECCollector" in sources_order:
                sources_order.remove("SECCollector")
                logs.append("Coordinator: SECCollector skipped/missing — removed from sources priority list.")

        conflict_flags = []

        # Helper to get field from source findings
        def get_val(source_name, field_name):
            report = reports.get(source_name, {})
            if report.get("status") == "success":
                findings = report.get("findings", {})
                return findings.get(field_name)
            return None

        # Revenue Priority
        for src in sources_order:
            val = get_val(src, "revenue")
            if val is not None:
                merged["revenue"] = val
                break

        # Subsidiaries Priority — check both 'subsidiaries' and SEC-specific 'subsidiaries_list'
        for src in sources_order:
            val = get_val(src, "subsidiaries_list")  # SEC returns this as a named list
            if val and isinstance(val, list) and len(val) > 0:
                merged["subsidiaries"] = val
                break
            val = get_val(src, "subsidiaries")
            if val and isinstance(val, list) and len(val) > 0:
                merged["subsidiaries"] = val
                break
            val_count = get_val(src, "subsidiaries_count")
            if val_count is not None and int(val_count) > 0:
                merged["subsidiaries"] = ["Exhibit 21 Subsidiary"] * int(val_count)
                break


        # Acquisitions Priority — merge from all sources to maximize coverage
        all_acquisitions = []
        seen_acq_names = set()
        for src in sources_order:
            val = get_val(src, "acquisitions")
            if val and isinstance(val, list):
                for acq in val:
                    name = str(acq.get("name", acq) if isinstance(acq, dict) else acq).lower().strip()
                    if name and name not in seen_acq_names:
                        seen_acq_names.add(name)
                        all_acquisitions.append(acq)
            # Also check acquisitions_mentions (SEC format — list of strings)
            mentions = get_val(src, "acquisitions_mentions")
            if mentions and isinstance(mentions, list):
                for m in mentions:
                    name = str(m).lower().strip()
                    if name and name not in seen_acq_names:
                        seen_acq_names.add(name)
                        all_acquisitions.append({
                            "name": m,
                            "deal_type": "minor acquisition",
                            "recency_years": 5.0
                        })
        if all_acquisitions:
            merged["acquisitions"] = all_acquisitions

        # Customer Type / Ecommerce / Countries
        for src in sources_order:
            val = get_val(src, "customer_type")
            if val:
                merged["customer_type"] = val
                break
        for src in sources_order:
            val = get_val(src, "has_ecommerce")
            if val is not None:
                merged["has_ecommerce"] = val
                break
        # Countries of operation — aggregate from all sources for full global coverage
        all_countries = []
        seen_countries = set()
        for src in sources_order:
            val = get_val(src, "countries_of_operation")
            if val and isinstance(val, list):
                for c in val:
                    c_norm = str(c).strip()
                    if c_norm and c_norm.lower() not in seen_countries:
                        seen_countries.add(c_norm.lower())
                        all_countries.append(c_norm)
            # Also merge SEC's geographic_revenue_or_regions
            sec_geo = get_val(src, "geographic_revenue_or_regions")
            if sec_geo and isinstance(sec_geo, list):
                for g in sec_geo:
                    g_norm = str(g).strip()
                    if g_norm and g_norm.lower() not in seen_countries:
                        seen_countries.add(g_norm.lower())
                        all_countries.append(g_norm)
        if all_countries:
            merged["countries_of_operation"] = all_countries

        for src in sources_order:
            val = get_val(src, "privacy_policy_published")
            if val is not None:
                merged["privacy_policy_published"] = val
                break
        for src in sources_order:
            val = get_val(src, "compliance_mentions")
            if val:
                merged["compliance_mentions"] = val
                break
        for src in sources_order:
            val = get_val(src, "quarterly_revenue")
            if val:
                merged["quarterly_revenue"] = val
                break
        for src in sources_order:
            val = get_val(src, "sic_codes")
            if val:
                merged["sic_codes"] = val
                break
        for src in sources_order:
            val = get_val(src, "sub_industries") or get_val(src, "cyber_sub_industries")
            if val:
                merged["sub_industries"] = val if isinstance(val, list) else [val]
                break
        for src in sources_order:
            val = get_val(src, "worst_sub_industry_appetite") or get_val(src, "services_appetite")
            if val:
                merged["worst_sub_industry_appetite"] = val
                merged["services_appetite"] = val
                break
        for src in sources_order:
            val = get_val(src, "internet_exposure_domains")
            if val is not None:
                merged["internet_exposure_domains"] = val
                break
        for src in sources_order:
            val = get_val(src, "customer_base_scale")
            if val:
                merged["customer_base_scale"] = val
                break
        for src in sources_order:
            val = get_val(src, "estimated_customers_count") or get_val(src, "customer_count") or get_val(src, "customers_count")
            if val is not None:
                merged["estimated_customers_count"] = val
                break
        for src in sources_order:
            val = get_val(src, "founding_year")
            if val is not None:
                merged["founding_year"] = val
                break
        for src in sources_order:
            val = get_val(src, "has_cyber_breach")
            if val is not None:
                merged["has_cyber_breach"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "has_active_litigation")
            if val is not None:
                merged["has_active_litigation"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "ftc_actions_count")
            if val is not None:
                try:
                    merged["ftc_actions_count"] = int(val)
                except ValueError:
                    merged["ftc_actions_count"] = 0
                break
        for src in sources_order:
            val = get_val(src, "detected_technologies")
            if val and isinstance(val, list):
                merged["detected_technologies"] = val
                break
        for src in sources_order:
            val = get_val(src, "ssl_grade")
            if val is not None:
                merged["ssl_grade"] = str(val).strip()
                break
        for src in sources_order:
            val = get_val(src, "cybersecurity_frameworks")
            if val and isinstance(val, list):
                merged["cybersecurity_frameworks"] = val
                break
        for src in sources_order:
            val = get_val(src, "has_dmarc_spf")
            if val is not None:
                merged["has_dmarc_spf"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "has_security_headers")
            if val is not None:
                merged["has_security_headers"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "has_security_txt")
            if val is not None:
                merged["has_security_txt"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "has_ciso_disclosure")
            if val is not None:
                merged["has_ciso_disclosure"] = bool(val)
                break
        for src in sources_order:
            val = get_val(src, "company_breaches") or get_val(src, "sec_cyber_incidents")
            if val and isinstance(val, list):
                merged["company_breaches"] = val
                break
        for src in sources_order:
            val = get_val(src, "industry_breach_tier")
            if val is not None:
                merged["industry_breach_tier"] = str(val).strip()
                break
        for src in sources_order:
            val = get_val(src, "naics_code")
            if val is not None and str(val).strip() and str(val).strip().lower() != "n/a":
                naics_str = str(val).strip()
                merged["naics_code"] = naics_str
                # Dynamic reverse lookup 4-digit SIC code from config/naics_sic_map.json
                if not merged.get("sic_codes") or any(len(str(s)) > 4 for s in merged.get("sic_codes", [])):
                    try:
                        with open("config/naics_sic_map.json", "r") as f:
                            n_s_map = json.load(f)
                        
                        mapped_sic = None
                        # 1. Exact match
                        for s_code, info in n_s_map.items():
                            if info.get("naics") == naics_str:
                                mapped_sic = s_code
                                break
                        # 2. Dynamic prefix match (5, 4, 3, 2 digits)
                        if not mapped_sic:
                            for p_len in range(min(5, len(naics_str)), 1, -1):
                                pfx = naics_str[:p_len]
                                for s_code, info in n_s_map.items():
                                    if info.get("naics", "").startswith(pfx):
                                        mapped_sic = s_code
                                        break
                                if mapped_sic:
                                    break
                        if mapped_sic:
                            merged["sic_codes"] = [mapped_sic]
                    except Exception:
                        pass
                break
        for src in sources_order:
            val = get_val(src, "naics_description")
            if val is not None:
                merged["naics_description"] = str(val).strip()
                break
        for src in sources_order:
            val = get_val(src, "country")
            if val is not None:
                merged["country"] = str(val).strip()
                break

        # Domains / HTTPS — first take what DomainScraper found
        for src in sources_order:
            val = get_val(src, "domains")
            if val:
                merged["domains"] = val
                break

        # Cybersecurity Info deterministic reconciliation
        has_dmarc_spf_found = False
        has_sec_headers_found = False
        has_sec_txt_found = False
        has_ciso_found = False
        fw_set = set()

        for src in sources_order:
            if get_val(src, "has_dmarc_spf") is True:
                has_dmarc_spf_found = True
            if get_val(src, "has_security_headers") is True:
                has_sec_headers_found = True
            if get_val(src, "has_security_txt") is True:
                has_sec_txt_found = True
            if get_val(src, "has_ciso_disclosure") is True:
                has_ciso_found = True
            fws = get_val(src, "cybersecurity_frameworks")
            if fws and isinstance(fws, list):
                fw_set.update(fws)

        merged["has_dmarc_spf"] = has_dmarc_spf_found
        merged["has_security_headers"] = has_sec_headers_found
        merged["has_security_txt"] = has_sec_txt_found
        # Enterprise default for Public / Mega Enterprise companies (SEC 10-K required CISO governance)
        is_large_public = (merged.get("revenue") or 0) >= 1000000000 or merged.get("entity_status") == "Public"
        merged["has_ciso_disclosure"] = has_ciso_found or is_large_public
        merged["cybersecurity_frameworks"] = list(fw_set)



        # Sanitize error messages before sending to LLM to prevent prompt bloat
        sanitized_reports = {}
        for src_name, report in reports.items():
            if report.get("status") == "error" and "message" in report:
                report = {**report, "message": report["message"][:200] + "..." if len(report.get("message", "")) > 200 else report.get("message", "")}
            sanitized_reports[src_name] = report

        # Call LLM to reconcile profile and write rationale
        prompt_vars = {
            "company_name": company_name,
            "domain": domain,
            "reports_json": json.dumps(sanitized_reports)
        }
        prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
        response_text = self.call_llm(prompt)
        reconciled = self.parse_json(response_text)

        # Apply LLM overrides to merged profile
        for k, v in reconciled.items():
            if k in merged and v is not None:
                if isinstance(v, list) and len(v) == 0 and isinstance(merged[k], list) and len(merged[k]) > 0:
                    continue
                merged[k] = v

        # Dynamic fallback inference for SIC codes if missing or defaulting to 7372
        final_sic = merged.get("sic_codes", [])
        if not final_sic or final_sic == ["7372"]:
            inferred_sic = self.infer_sic_codes_dynamically(company_name, reports, final_sic, conflict_flags)
            logger.info(f"[COORDINATOR] Dynamic SIC inference resolved: {inferred_sic} (original was {final_sic})")
            merged["sic_codes"] = inferred_sic

        # Re-verify USA Presence (using countries of operation + primary HQ country fallback)
        countries_lower = [c.lower() for c in merged["countries_of_operation"]]
        hq_country = str(merged.get("country", "")).lower()
        merged["usa_presence"] = (
            "usa" in countries_lower or "united states" in countries_lower or "us" in countries_lower or
            "usa" in hq_country or "united states" in hq_country or "us" in hq_country
        )

        # Detect conflicts (e.g. if SEC revenue differs significantly from Wikidata/Gleif revenue)
        revenues_found = {}
        for src in sources_order:
            r = get_val(src, "revenue")
            if r is not None:
                revenues_found[src] = r
        if len(revenues_found) > 1:
            vals = list(revenues_found.values())
            if max(vals) - min(vals) > (min(vals) * 0.2): # > 20% difference
                conflict_flags.append({
                    "parameter": "revenue",
                    "details": f"Revenue discrepancy across sources: {revenues_found}"
                })
                logs.append("Coordinator Warning: Significant revenue variance detected across sources.")

        logger.info(f"Reconciliation complete. Reconciled Profile:\n{json.dumps(merged, indent=2)}")
        logger.info(f"Conflict Flags:\n{json.dumps(conflict_flags, indent=2)}")
        
        logs.append("Coordinator: Merge and reconciliation completed.")
        return {
            "reconciled_profile": merged,
            "conflict_flags": conflict_flags,
            "audit_logs": state.get("audit_logs", []) + logs
        }

    def infer_sic_codes_dynamically(self, company_name: str, reports: Dict[str, Any], existing_sic_codes: List[str] = None, conflict_flags: List[Dict] = None) -> List[str]:
        # Gather all industry text indicators from Wikipedia, Wikidata, SEC
        indicators = []
        wiki_ind = []
        strong_ind = []
        
        # Check Wikipedia industry classification
        wiki_report = reports.get("Wikipedia", {})
        if wiki_report.get("status") == "success":
            ind_class = wiki_report.get("findings", {}).get("industry_classification", [])
            if isinstance(ind_class, list):
                wiki_ind.extend(ind_class)
                
        # Check Wikidata industry and sub_industries
        wikidata_report = reports.get("Wikidata", {})
        if wikidata_report.get("status") == "success":
            findings = wikidata_report.get("findings", {})
            ind = findings.get("industry", [])
            if isinstance(ind, list):
                strong_ind.extend(ind)
            sub_ind = findings.get("sub_industries", [])
            if isinstance(sub_ind, list):
                strong_ind.extend(sub_ind)

        # Check SEC segments/SIC codes
        sec_report = reports.get("SECCollector", {})
        if sec_report.get("status") == "success":
            findings = sec_report.get("findings", {})
            segments = findings.get("business_segments", [])
            if isinstance(segments, list):
                strong_ind.extend(segments)
            # Check if SEC already provided some SIC codes
            sec_sics = findings.get("sic_codes", [])
            if sec_sics and isinstance(sec_sics, list):
                valid_sec_sics = [str(s) for s in sec_sics if str(s).strip() and str(s).strip() != "7372"]
                if valid_sec_sics:
                    return valid_sec_sics

        # Conflict check for Wikipedia noise (e.g. Apple fruit vs Apple tech)
        wiki_text = " ".join([str(ind) for ind in wiki_ind]).lower()
        strong_text = " ".join([str(ind) for ind in strong_ind]).lower()
        
        if ("agriculture" in wiki_text or "fruit" in wiki_text) and ("software" in strong_text or "technology" in strong_text or "computing" in strong_text or "electronics" in strong_text):
            if conflict_flags is not None:
                conflict_flags.append({
                    "parameter": "industry",
                    "details": f"Wikipedia returned suspicious agricultural data '{wiki_text}'. Ignored in favor of authoritative sources."
                })
        else:
            indicators.extend(wiki_ind)
            
        indicators.extend(strong_ind)

        # Normalize indicators and company name to lowercase
        all_text = " ".join([company_name] + [str(ind) for ind in indicators]).lower()
        
        # Industry keyword mapping to standard SIC code
        # - Insurance: SIC 6331 (Fire, Marine, and Casualty Insurance)
        if any(keyword in all_text for keyword in ["insurance", "casualty", "mutual", "assurance", "reinsurance", "underwriter", "underwriting", "indemnity"]):
            return ["6331"]
        # - Banks / Finance: SIC 6021 (National Commercial Banks)
        elif any(keyword in all_text for keyword in ["bank", "finance", "credit", "lending", "capital", "financial", "securities", "banking", "investment"]):
            return ["6021"]
        # - Department stores / retail: SIC 5311
        elif any(keyword in all_text for keyword in ["retail", "store", "shop", "department store", "supermarket", "clothing", "apparel", "e-commerce"]):
            return ["5311"]
        # - Hospitals / Healthcare: SIC 8062
        elif any(keyword in all_text for keyword in ["hospital", "clinic", "medical", "healthcare", "health system", "pharma", "pharmaceutical"]):
            return ["8062"]
        # - Tech / Software: SIC 7372
        elif any(keyword in all_text for keyword in ["software", "technology", "saas", "packaged software", "it services", "computer", "application"]):
            return ["7372"]
            
        # If we have existing SIC codes and they aren't empty/default to 7372, use them
        if existing_sic_codes and len(existing_sic_codes) > 0 and existing_sic_codes != ["7372"]:
            return existing_sic_codes
            
        # Default fallback
        return ["7372"]

class FactCheckerAgent(BaseFactCheckerAgent):
    async def verify(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reconciled = state.get("reconciled_profile", {})
        reports = state.get("reports", {})
        logs = []
        logs.append("Fact Checker: Starting fact corroboration and consensus analysis...")
        
        logger = self.get_logger()
        logger.info("********************************************")
        logger.info("[FACT CHECKER] Starting Fact Verification Process")
        logger.info("********************************************")

        # Extract claims to verify
        claims = {
            "revenue": reconciled.get("revenue"),
            "subsidiaries_count": len(reconciled.get("subsidiaries", [])),
            "acquisitions_count": len(reconciled.get("acquisitions", [])),
            "customer_type": reconciled.get("customer_type"),
            "has_ecommerce": reconciled.get("has_ecommerce"),
            "privacy_policy_published": reconciled.get("privacy_policy_published")
        }

        # Format prompt for LLM fact checker
        prompt_vars = {
            "claims_json": json.dumps(claims),
            "evidence_snippets": json.dumps(reports),
            "provenance": "GLEIF, SEC EDGAR, Wikipedia API"
        }
        prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
        response_text = self.call_llm(prompt)
        verification_output = self.parse_json(response_text)

        # Calculate accuracy score
        claims_verif = verification_output.get("claims_verification", {})
        total_claims = len(claims_verif)
        verified_count = 0
        
        for k, v in claims_verif.items():
            status = v.get("status", "Unsupported").lower()
            if "partial" in status:
                verified_count += 0.5
            elif "verified" in status or "ok" in status:
                verified_count += 1

        accuracy_score = (verified_count / total_claims) if total_claims > 0 else 1.0
        logger.info(f"Fact Checker Verdict: Accuracy Score = {accuracy_score:.2f} ({verified_count}/{total_claims} corroborated claims)")
        logger.info(f"Claims Verification Details:\n{json.dumps(claims_verif, indent=2)}")
        
        logs.append(f"Fact Checker Verdict: Accuracy Score = {accuracy_score:.2f} ({verified_count}/{total_claims} corroborated claims)")

        return {
            "claims_verification": claims_verif,
            "accuracy_score": accuracy_score,
            "audit_logs": state.get("audit_logs", []) + logs
        }

class UnderwriterAgent(BaseUnderwriterAgent):
    def underwrite(self, state: Dict[str, Any]) -> Dict[str, Any]:
        underwriter_logger = self.get_logger()
        underwriter_logger.info("********************************************")
        underwriter_logger.info("[UNDERWRITER] Initiating underwriting evaluation...")
        underwriter_logger.info("********************************************")

        reconciled = state.get("reconciled_profile", {})
        accuracy = state.get("accuracy_score", 1.0)
        mismatch = state.get("mismatch_flag", False)
        conflicts = state.get("conflict_flags", [])
        logs = []
        logs.append("Underwriter: Applying configuration-driven prompts and mathematical rules...")

        # 1. Format LLM underwriter prompt
        prompt_vars = {
            "business_rule": self.config.business_rule,
            "inputs_json": json.dumps(reconciled),
            "fact_check_summary": f"Claims Accuracy: {accuracy*100:.1f}%. Discrepancies count: {len(conflicts)}"
        }
        prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
        response_text = self.call_llm(prompt)
        assessment = self.parse_json(response_text)

        # 2. Strict mathematical validation
        revenue = reconciled.get("revenue") or 0
        modifier_scores = {}
        underwriting_rationale = {}

        from src.utils.logger import get_agent_logger
        from datetime import datetime

        def get_rev_tier_name(r):
            if r >= 1000000000: return "Mega Enterprise (>= $1B)"
            if r >= 250000000: return "Large Enterprise (>= $250M)"
            if r >= 50000000: return "Mid-Market (>= $50M)"
            return "SMB (< $50M)"
            
        def get_rev_tier_short(r):
            if r >= 1000000000: return "Mega Enterprise"
            if r >= 250000000: return "Large Enterprise"
            if r >= 50000000: return "Mid-Market"
            return "SMB"

        rev_tier = get_rev_tier_name(revenue)
        rev_tier_short = get_rev_tier_short(revenue)
        
        
        def generate_reason(category, inputs, bucket, desc):
            bullets = ""
            for k, v in inputs.items():
                bullets += f"- {k} is {v}\n"
            return f"This modifier was assigned {category} because:\n{bullets}- These values satisfy {bucket}\n\nTherefore, {desc[0].lower() + desc[1:]}"

        def get_impacts(base_impact, rating):
            rat = rating.lower()
            if "unfavourable" in rat:
                return [f"Increased severity for {base_impact.lower()}", "Higher potential financial liability", "Stricter underwriting limits recommended"]
            elif "favourable" in rat:
                return [f"Reduced exposure from {base_impact.lower()}", "Positive indicator of mature risk management", "Supports favorable pricing conditions"]
            return [f"Average exposure regarding {base_impact.lower()}", "Standard underwriting conditions apply"]

        # --- 1. Mergers and Acquisitions ---
        ma_logger = get_agent_logger("Mergers and Acquisitions")
        try:
            acqs = reconciled.get("acquisitions", [])
            ma_points = 0.0
            valid_acq_count = 0
            for i, acq in enumerate(acqs):
                d_name_raw = str(acq.get("name", acq) if isinstance(acq, dict) else acq).lower()
                if any(kw in d_name_raw for kw in ["sold", "divest", "spinoff", "sale of"]):
                    continue
                valid_acq_count += 1
                deal_type = str(acq.get("deal_type", "minor acquisition") if isinstance(acq, dict) else "minor acquisition").lower()
                pts = 1.0
                if "trans" in deal_type: pts = 4.0
                elif "material" in deal_type: pts = 3.0
                elif "minor" in deal_type: pts = 2.0
            
                recency = acq.get("recency_years", 5.0) if isinstance(acq, dict) else 5.0
                if recency > 1900: recency = datetime.now().year - recency
            
                mult = 0.0
                if recency < 1.0: mult = 2.0
                elif recency < 2.0: mult = 1.5
                elif recency < 5.0: mult = 1.0
                elif recency <= 10.0: mult = 0.5
                ma_points += pts * mult

            ma_rating = "average"
            bucket = ""
            rule_matched = []
            range_str = ""
            if revenue >= 1000000000:
                rule_matched.append("Revenue >= $1,000,000,000")
                if ma_points <= 5: ma_rating, bucket, range_str = "very favourable", "MA-01", "<= 5.0"
                elif ma_points <= 10: ma_rating, bucket, range_str = "favourable", "MA-02", "<= 10.0"
                elif ma_points <= 15: ma_rating, bucket, range_str = "partially favourable", "MA-03", "<= 15.0"
                elif ma_points <= 20: ma_rating, bucket, range_str = "average", "MA-04", "<= 20.0"
                elif ma_points <= 30: ma_rating, bucket, range_str = "partially unfavourable", "MA-05", "<= 30.0"
                else: ma_rating, bucket, range_str = "unfavourable", "MA-06", "> 30.0"
            elif revenue >= 250000000:
                rule_matched.append("Revenue >= $250,000,000")
                if ma_points <= 3: ma_rating, bucket, range_str = "very favourable", "MA-07", "<= 3.0"
                elif ma_points <= 6: ma_rating, bucket, range_str = "favourable", "MA-08", "<= 6.0"
                elif ma_points <= 10: ma_rating, bucket, range_str = "partially favourable", "MA-09", "<= 10.0"
                elif ma_points <= 15: ma_rating, bucket, range_str = "average", "MA-10", "<= 15.0"
                elif ma_points <= 20: ma_rating, bucket, range_str = "partially unfavourable", "MA-11", "<= 20.0"
                else: ma_rating, bucket, range_str = "unfavourable", "MA-12", "> 20.0"
            elif revenue >= 50000000:
                rule_matched.append("Revenue >= $50,000,000")
                if ma_points <= 2: ma_rating, bucket, range_str = "very favourable", "MA-13", "<= 2.0"
                elif ma_points <= 4: ma_rating, bucket, range_str = "favourable", "MA-14", "<= 4.0"
                elif ma_points <= 7: ma_rating, bucket, range_str = "partially favourable", "MA-15", "<= 7.0"
                elif ma_points <= 10: ma_rating, bucket, range_str = "average", "MA-16", "<= 10.0"
                elif ma_points <= 15: ma_rating, bucket, range_str = "partially unfavourable", "MA-17", "<= 15.0"
                else: ma_rating, bucket, range_str = "unfavourable", "MA-18", "> 15.0"
            else:
                rule_matched.append("Revenue < $50,000,000")
                if ma_points <= 1: ma_rating, bucket, range_str = "very favourable", "MA-19", "<= 1.0"
                elif ma_points <= 3: ma_rating, bucket, range_str = "favourable", "MA-20", "<= 3.0"
                elif ma_points <= 5: ma_rating, bucket, range_str = "partially favourable", "MA-21", "<= 5.0"
                elif ma_points <= 7: ma_rating, bucket, range_str = "average", "MA-22", "<= 7.0"
                elif ma_points <= 10: ma_rating, bucket, range_str = "partially unfavourable", "MA-23", "<= 10.0"
                else: ma_rating, bucket, range_str = "unfavourable", "MA-24", "> 10.0"

            rule_matched.append(f"Calculated M&A Points {range_str}")
            
            p_factors, r_factors = [], []
            if "favourable" in ma_rating: p_factors.append(f"Low volume of recent material acquisitions ({ma_points:.1f} pts)")
            if "unfavourable" in ma_rating: r_factors.append(f"High volume of recent acquisitions generating technical debt ({ma_points:.1f} pts)")
            if not acqs: p_factors.append("No material acquisitions detected")

            itemized_acqs = []
            for acq in acqs:
                d_name = acq.get("name", "Unknown") if isinstance(acq, dict) else str(acq)
                if any(kw in d_name.lower() for kw in ["sold", "divest", "spinoff", "sale of"]):
                    continue
                d_type = str(acq.get("deal_type", "minor acquisition") if isinstance(acq, dict) else "minor acquisition").title()
                r_years = acq.get("recency_years", 5.0) if isinstance(acq, dict) else 5.0
                if r_years > 1900: r_years = datetime.now().year - r_years
                
                pts_val = 1.0
                if "Trans" in d_type: pts_val = 4.0
                elif "Material" in d_type: pts_val = 3.0
                elif "Minor" in d_type: pts_val = 2.0
                
                m_val = 0.0
                if r_years < 1.0: m_val = 2.0
                elif r_years < 2.0: m_val = 1.5
                elif r_years < 5.0: m_val = 1.0
                elif r_years <= 10.0: m_val = 0.5
                
                contrib = pts_val * m_val
                itemized_acqs.append({
                    "name": d_name,
                    "recency": f"{r_years:.1f} yrs",
                    "deal_type": d_type,
                    "base_pts": pts_val,
                    "multiplier": f"{m_val:.1f}x",
                    "points": contrib
                })

            modifier_scores["Mergers and Acquisitions"] = {
                "score": round(ma_points, 2),
                "rating": ma_rating,
                "confidence": "High" if valid_acq_count > 0 else "Medium",
                "reference": f"{valid_acq_count} Acquisitions ({ma_points:.1f} Pts)",
                "itemized_details": itemized_acqs
            }
            underwriting_rationale["Mergers and Acquisitions"] = {
                "decision_summary": f"M&A risk evaluated based on {len(acqs)} recent acquisition(s).",
                "rule_id": bucket,
                "rule_name": f"{rev_tier_short} - {ma_rating.title()} M&A Complexity",
                "rule_description": f"Companies in the {rev_tier_short} tier with a M&A score {range_str} are classified as {ma_rating.title()} due to the associated integration complexity.",
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Acquisitions Found": len(acqs),
                    "Calculated M&A Points": round(ma_points, 2)
                },
                "matched_bucket": bucket,
                "assigned_category": ma_rating.title(),
                "reason": generate_reason(ma_rating.title(), {"Revenue Tier": rev_tier,
                    "Acquisitions Found": len(acqs),
                    "Calculated M&A Points": round(ma_points, 2)}, bucket, f"Companies in the {rev_tier_short} tier with a M&A score {range_str} are classified as {ma_rating.title()} due to the associated integration complexity."),
                "business_impact": get_impacts("M&A IT integrations and inherited vulnerabilities", ma_rating),
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            ma_logger.error(f"Exception: {e}")

        # --- 2. Amount of sensitive information ---
        sens_logger = get_agent_logger("Amount of sensitive information")
        try:
            cust_type = str(reconciled.get("customer_type", "B2B")).upper()
            has_ecom = reconciled.get("has_ecommerce", False)

            rule_matched = []
            bucket = ""
            if "B2C" in cust_type or "MIX" in cust_type:
                rule_matched.append(f"Customer Type == '{cust_type}'")
                if has_ecom:
                    sens_rating, bucket = "partially unfavourable", "SI-01"
                    rule_matched.append("Ecommerce == True")
                    desc = "Companies serving mixed/B2C customers through ecommerce generally process larger volumes of sensitive customer information (PII/PCI)."
                else:
                    sens_rating, bucket = "average", "SI-02"
                    rule_matched.append("Ecommerce == False")
                    desc = "Consumer-facing companies without ecommerce process PII but have reduced direct PCI exposure."
            elif "B2B" in cust_type:
                rule_matched.append("Customer Type == 'B2B'")
                if has_ecom:
                    sens_rating, bucket = "partially favourable", "SI-03"
                    rule_matched.append("Ecommerce == True")
                    desc = "B2B companies with ecommerce process corporate data and B2B payments, representing moderate exposure."
                else:
                    sens_rating, bucket = "favourable", "SI-04"
                    rule_matched.append("Ecommerce == False")
                    desc = "B2B companies without direct ecommerce typically hold the lowest volume of consumer PII/PCI."
            else:
                rule_matched.append("Customer Type == 'UNKNOWN'")
                sens_rating, bucket = "partially unfavourable", "SI-05"
                desc = "Unknown customer type defaults to higher sensitivity assumption."
            
            p_factors, r_factors = [], []
            if "B2B" in cust_type and not has_ecom: p_factors.append("Low direct consumer PII collection footprint")
            if "B2C" in cust_type or "MIX" in cust_type: r_factors.append("Direct collection of consumer PII")
            if has_ecom: r_factors.append("Active e-commerce payment flows (PCI exposure)")

            modifier_scores["Amount of sensitive information"] = {
                "score": "",
                "rating": sens_rating,
                "confidence": "High",
                "reference": f"Customer: {cust_type}, E-com: {'Active' if has_ecom else 'No'}"
            }
            underwriting_rationale["Amount of sensitive information"] = {
                "decision_summary": f"Sensitivity evaluated based on customer type and ecommerce capabilities.",
                "rule_id": bucket,
                "rule_name": f"{'Consumer' if ('B2C' in cust_type or 'MIX' in cust_type) else 'B2B'} Exposure - {'E-commerce Active' if has_ecom else 'No E-commerce'}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Customer Type": cust_type,
                    "Has Ecommerce": "Yes" if has_ecom else "No"
                },
                "matched_bucket": bucket,
                "assigned_category": sens_rating.title(),
                "reason": generate_reason(sens_rating.title(), {"Customer Type": cust_type,
                    "Has Ecommerce": "Yes" if has_ecom else "No"}, bucket, desc),
                "business_impact": ["Higher privacy exposure", "Increased breach notification requirements", "Greater volume of regulatory obligations"] if "unfavourable" in sens_rating else ["Lower direct consumer privacy exposure", "Reduced individual breach notification scope"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            sens_logger.error(f"Exception: {e}")

        # --- 3. Domain Encryption ---
        enc_logger = get_agent_logger("Domain Encryption")
        try:
            domains = reconciled.get("domains", [])
            total_domains = len(domains)
            enc_count = sum(1 for d in domains if d.get("https_encrypted", False))
            
            rule_matched = []
            if total_domains > 0:
                rule_matched.append(f"Total Domains == {total_domains} (> 0)")
                if enc_count == total_domains:
                    enc_rating, bucket = "favourable", "DE-01"
                    rule_matched.append("Encrypted Domains == Total Domains (100%)")
                    desc = "100% encryption coverage across all discovered external domains signifies strong perimeter security posture."
                elif enc_count > 0:
                    enc_rating, bucket = "partially favourable", "DE-02"
                    rule_matched.append("0 < Encrypted Domains < Total Domains")
                    desc = "Partial encryption coverage indicates potential misconfigurations or legacy unencrypted infrastructure."
                else:
                    enc_rating, bucket = "average", "DE-03"
                    rule_matched.append("Encrypted Domains == 0 (0%)")
                    desc = "0% encryption coverage across discovered domains poses a significant data-in-transit risk."
            else:
                enc_rating, bucket = "average", "DE-04"
                rule_matched.append("Total Domains == 0")
                desc = "No external domains discovered. Defaulting to average baseline."
            
            p_factors, r_factors = [], []
            if enc_count == total_domains and total_domains > 0: p_factors.append(f"100% of discovered external domains ({total_domains}) utilize HTTPS")
            elif total_domains > 0: r_factors.append(f"{total_domains - enc_count} out of {total_domains} external domains lack HTTPS encryption")

            ssl_grade = reconciled.get("ssl_grade")
            if ssl_grade:
                ssl_grade_clean = str(ssl_grade).upper().strip()
                # A poor SSL grade is anything C or lower (C, D, E, F, or T)
                if ssl_grade_clean in ["C", "D", "E", "F", "T"]:
                    if enc_rating == "favourable":
                        enc_rating = "average"
                    elif enc_rating == "partially favourable":
                        enc_rating = "partially unfavourable"
                    elif enc_rating == "average":
                        enc_rating = "unfavourable"
                    
                    rule_matched.append(f"SSL Labs Grade == '{ssl_grade_clean}' (Poor SSL/TLS Configuration)")
                    desc += f" Furthermore, SSL Labs returned a poor security grade of '{ssl_grade_clean}', indicating vulnerable configurations or protocols."
                    r_factors.append(f"Insecure SSL/TLS configuration on primary domain (Grade: {ssl_grade_clean})")
                else:
                    rule_matched.append(f"SSL Labs Grade == '{ssl_grade_clean}'")
                    p_factors.append(f"Strong SSL/TLS grade on primary domain (Grade: {ssl_grade_clean})")

            modifier_scores["Domain Encryption"] = {
                "score": f"{enc_count}/{total_domains}",
                "rating": enc_rating,
                "confidence": "High" if ssl_grade else "Medium",
                "reference": f"HTTPS: {enc_count}/{total_domains} ({(enc_count/total_domains)*100:.0f}%)" if total_domains > 0 else "0 Domains",
                "ssl_grade": ssl_grade or "N/A"
            }
            underwriting_rationale["Domain Encryption"] = {
                "decision_summary": f"Encryption ratio evaluated across {total_domains} discovered domain(s).",
                "rule_id": bucket,
                "rule_name": f"Domain Encryption - {enc_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Total Domains": total_domains,
                    "Encrypted Domains (HTTPS)": enc_count,
                    "Encryption Ratio": f"{(enc_count/total_domains)*100:.0f}%" if total_domains > 0 else "N/A",
                    "SSL Labs Grade": ssl_grade or "N/A"
                },
                "matched_bucket": bucket,
                "assigned_category": enc_rating.title(),
                "reason": generate_reason(enc_rating.title(), {
                    "Total Domains": total_domains,
                    "Encrypted Domains (HTTPS)": enc_count,
                    "Encryption Ratio": f"{(enc_count/total_domains)*100:.0f}%" if total_domains > 0 else "N/A",
                    "SSL Labs Grade": ssl_grade or "N/A"
                }, bucket, desc),
                "business_impact": ["Strong protection against man-in-the-middle attacks", "Lower likelihood of credential interception"] if "favourable" in enc_rating else ["High risk of data-in-transit interception", "Increased potential for credential theft over unencrypted channels"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            enc_logger.error(f"Exception: {e}")

        # --- 4. Geographic Spread ---
        geo_logger = get_agent_logger("Geographic Spread")
        try:
            countries = reconciled.get("countries_of_operation", ["USA"])
            c_count = len(countries)
            continents = reconciled.get("continent_spread", ["North America"])
            cont_count = len(continents)
            usa_p = reconciled.get("usa_presence", True)
        
            bucket = ""
            rule_matched = []
            range_str = ""
            if revenue >= 1000000000:
                rule_matched.append("Revenue >= $1,000,000,000")
                if c_count <= 10 and cont_count == 1: geo_rating, bucket, range_str = "favourable", "GS-01", "Countries <= 10 AND Continents == 1"
                elif c_count <= 10: geo_rating, bucket, range_str = "partially favourable", "GS-02", "Countries <= 10 AND Continents > 1"
                else: geo_rating, bucket, range_str = "average", "GS-03", "Countries > 10"
            elif revenue >= 250000000:
                rule_matched.append("Revenue >= $250,000,000")
                if c_count <= 5 and cont_count == 1: geo_rating, bucket, range_str = "favourable", "GS-04", "Countries <= 5 AND Continents == 1"
                elif c_count <= 7: geo_rating, bucket, range_str = "partially favourable", "GS-05", "Countries <= 7"
                else: geo_rating, bucket, range_str = "average", "GS-06", "Countries > 7"
            elif revenue >= 50000000:
                rule_matched.append("Revenue >= $50,000,000")
                if c_count <= 3 and cont_count == 1: geo_rating, bucket, range_str = "favourable", "GS-07", "Countries <= 3 AND Continents == 1"
                elif c_count <= 5: geo_rating, bucket, range_str = "partially favourable", "GS-08", "Countries <= 5"
                else: geo_rating, bucket, range_str = "average", "GS-09", "Countries > 5"
            else:
                rule_matched.append("Revenue < $50,000,000")
                if c_count <= 2 and cont_count == 1: geo_rating, bucket, range_str = "favourable", "GS-10", "Countries <= 2 AND Continents == 1"
                elif c_count <= 10: geo_rating, bucket, range_str = "partially favourable", "GS-11", "Countries <= 10"
                else: geo_rating, bucket, range_str = "average", "GS-12", "Countries > 10"
                
            rule_matched.append(range_str)
            desc = f"Companies in the {rev_tier_short} tier operating in {range_str.split('AND')[0].strip().replace('Countries', 'countries')} exhibit {geo_rating} geographic complexity."
            
            p_factors, r_factors = [], []
            if "favourable" in geo_rating: p_factors.append(f"Concentrated geographic footprint ({c_count} countries)")
            if "unfavourable" in geo_rating or geo_rating == "average": r_factors.append(f"Broad geographic footprint ({c_count} countries across {cont_count} continents)")
            if usa_p: r_factors.append("Operations in the USA subject to stringent state-level privacy regulations (e.g. CCPA, NYDFS)")

            modifier_scores["Geographic Spread"] = {
                "score": c_count,
                "rating": geo_rating,
                "confidence": "High",
                "reference": f"{c_count} Countries, {cont_count} Continents"
            }
            underwriting_rationale["Geographic Spread"] = {
                "decision_summary": f"Geographic risk evaluated across {c_count} countr{'ies' if c_count!=1 else 'y'}.",
                "rule_id": bucket,
                "rule_name": f"{rev_tier_short} - Global Spread - {geo_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Country Count": c_count,
                    "Continent Count": cont_count,
                    "USA Presence": "Yes" if usa_p else "No"
                },
                "matched_bucket": bucket,
                "assigned_category": geo_rating.title(),
                "reason": generate_reason(geo_rating.title(), {"Revenue Tier": rev_tier,
                    "Country Count": c_count,
                    "Continent Count": cont_count,
                    "USA Presence": "Yes" if usa_p else "No"}, bucket, desc),
                "business_impact": ["Increased multi-jurisdictional compliance requirements", "Higher operational complexity in incident response", "Elevated state-sponsored threat exposure"] if c_count > 5 else ["Streamlined regulatory compliance landscape", "Centralized incident response operations"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            geo_logger.error(f"Exception: {e}")

        # --- 5. Internet Footprint ---
        foot_logger = get_agent_logger("Internet footprint")
        try:
            # Count unique web domains (D)
            domains_list = reconciled.get("domains", [])
            if isinstance(domains_list, list) and domains_list:
                domain_count = len(domains_list)
            else:
                domain_count = int(reconciled.get("domains_count") or reconciled.get("internet_exposure_domains") or 1)
            domain_count = max(1, domain_count)

            # Customer count scale & multiplier lookup (M)
            cust_count = reconciled.get("estimated_customers_count")
            if cust_count is None:
                scale = reconciled.get("customer_base_scale", "SMB (<1k)")
                if "Enterprise" in scale: cust_count = 100000000
                elif "Mid-Market" in scale: cust_count = 500000
                else: cust_count = 10000
            cust_count = int(cust_count)

            if cust_count <= 10000: mult = 1.0; cust_bracket = "<= 10k"
            elif cust_count <= 100000: mult = 1.5; cust_bracket = "10k-100k"
            elif cust_count <= 1000000: mult = 2.0; cust_bracket = "100k-1M"
            elif cust_count <= 10000000: mult = 2.5; cust_bracket = "1M-10M"
            elif cust_count <= 100000000: mult = 3.0; cust_bracket = "10M-100M"
            elif cust_count <= 1000000000: mult = 3.5; cust_bracket = "100M-1B"
            else: mult = 4.0; cust_bracket = "1B+"

            calculated_score = domain_count * mult

            # Revenue tier lookup & category evaluation
            rule_matched = []
            rule_matched.append(f"Unique Domains Count = {domain_count}")
            rule_matched.append(f"Estimated Customers = {cust_count:,} ({cust_bracket}, Multiplier x{mult})")
            rule_matched.append(f"Calculated Footprint Score = {calculated_score:.1f}")

            if revenue >= 1000000000:
                rule_matched.append("Revenue >= $1,000,000,000")
                if calculated_score <= 4: footprint_rating, bucket = "very favourable", "IF-01"
                elif calculated_score <= 9: footprint_rating, bucket = "favourable", "IF-02"
                elif calculated_score <= 14: footprint_rating, bucket = "partially favourable", "IF-03"
                else: footprint_rating, bucket = "average", "IF-04"
            elif revenue >= 250000000:
                rule_matched.append("Revenue >= $250,000,000")
                if calculated_score <= 3: footprint_rating, bucket = "very favourable", "IF-05"
                elif calculated_score <= 5: footprint_rating, bucket = "favourable", "IF-06"
                elif calculated_score <= 9: footprint_rating, bucket = "partially favourable", "IF-07"
                else: footprint_rating, bucket = "average", "IF-08"
            elif revenue >= 50000000:
                rule_matched.append("Revenue >= $50,000,000")
                if calculated_score <= 2: footprint_rating, bucket = "very favourable", "IF-09"
                elif calculated_score <= 4: footprint_rating, bucket = "favourable", "IF-10"
                elif calculated_score <= 6: footprint_rating, bucket = "partially favourable", "IF-11"
                else: footprint_rating, bucket = "average", "IF-12"
            else:
                rule_matched.append("Revenue < $50,000,000")
                if calculated_score <= 1: footprint_rating, bucket = "very favourable", "IF-13"
                elif calculated_score <= 2: footprint_rating, bucket = "favourable", "IF-14"
                elif calculated_score <= 4: footprint_rating, bucket = "partially favourable", "IF-15"
                else: footprint_rating, bucket = "average", "IF-16"

            desc = f"External attack surface score computed as {calculated_score:.1f} ({domain_count} domains x {mult} customer scale multiplier)."
            p_factors, r_factors = [], []
            if "favourable" in footprint_rating:
                p_factors.append(f"Highly consolidated external perimeter ({domain_count} domains)")
            if "unfavourable" in footprint_rating or "average" in footprint_rating:
                r_factors.append(f"Expanded external attack surface ({domain_count} domains, {cust_bracket} customer scale)")

            modifier_scores["Internet footprint"] = {
                "score": f"{calculated_score:.1f}",
                "rating": footprint_rating,
                "confidence": "High",
                "reference": f"{domain_count} Domains, {cust_bracket} (x{mult})"
            }
            underwriting_rationale["Internet footprint"] = {
                "decision_summary": f"Internet footprint exposure score calculated as {calculated_score:.1f} ({domain_count} domains x {mult} customer scale multiplier).",
                "rule_id": bucket,
                "rule_name": f"Internet Footprint - {footprint_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Discovered Domains": domain_count,
                    "Estimated Customers": f"{cust_count:,}",
                    "Customer Scale Multiplier": f"x{mult}",
                    "Calculated Footprint Score": round(calculated_score, 1)
                },
                "matched_bucket": bucket,
                "assigned_category": footprint_rating.title(),
                "reason": generate_reason(footprint_rating.title(), {
                    "Revenue Tier": rev_tier,
                    "Discovered Domains": domain_count,
                    "Estimated Customers": f"{cust_count:,}",
                    "Customer Scale Multiplier": f"x{mult}",
                    "Calculated Footprint Score": round(calculated_score, 1)
                }, bucket, desc),
                "business_impact": ["Increased likelihood of undiscovered rogue assets", "Higher vulnerability to automated mass-scanning exploits"] if "favourable" not in footprint_rating else ["Tight control over perimeter assets", "Lower likelihood of shadow IT exploitation"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            foot_logger.error(f"Exception: {e}")

        # --- 6. Nature of Services ---
        serv_logger = get_agent_logger("Nature of services")
        try:
            # Count unique predominant sub-industries (N)
            sub_industries = reconciled.get("sub_industries") or reconciled.get("cyber_sub_industries") or []
            if not isinstance(sub_industries, list):
                sub_industries = [str(sub_industries)]
            
            # Deduplicate unique predominant sub-industries
            unique_sub_industries = list(dict.fromkeys([s.strip().title() for s in sub_industries if s and str(s).strip()]))
            sub_ind_count = max(1, len(unique_sub_industries))

            # Determine worst sub-industry appetite & multiplier (M)
            worst_appetite = str(reconciled.get("worst_sub_industry_appetite", "acceptable")).lower().strip()
            if "prohibited" in worst_appetite:
                multiplier = 3.0
                appetite_label = "Prohibited"
            elif "restricted" in worst_appetite:
                multiplier = 2.0
                appetite_label = "Restricted"
            elif "target" in worst_appetite:
                multiplier = 0.1
                appetite_label = "Target"
            else:
                multiplier = 1.0
                appetite_label = "Acceptable"

            calculated_score = sub_ind_count * multiplier

            # Revenue tier lookup & category evaluation
            rule_matched = []
            rule_matched.append(f"Unique Sub-Industries Count = {sub_ind_count}")
            rule_matched.append(f"Worst Sub-Industry Appetite = {appetite_label} (Multiplier x{multiplier})")
            rule_matched.append(f"Calculated Exposure Score = {calculated_score:.1f}")

            if revenue >= 1000000000:
                rule_matched.append("Revenue >= $1,000,000,000")
                if calculated_score <= 4: services_rating, bucket = "very favourable", "NS-01"
                elif calculated_score <= 9: services_rating, bucket = "favourable", "NS-02"
                elif calculated_score <= 14: services_rating, bucket = "partially favourable", "NS-03"
                else: services_rating, bucket = "average", "NS-04"
            elif revenue >= 250000000:
                rule_matched.append("Revenue >= $250,000,000")
                if calculated_score <= 3: services_rating, bucket = "very favourable", "NS-05"
                elif calculated_score <= 5: services_rating, bucket = "favourable", "NS-06"
                elif calculated_score <= 9: services_rating, bucket = "partially favourable", "NS-07"
                else: services_rating, bucket = "average", "NS-08"
            elif revenue >= 50000000:
                rule_matched.append("Revenue >= $50,000,000")
                if calculated_score <= 2: services_rating, bucket = "very favourable", "NS-09"
                elif calculated_score <= 4: services_rating, bucket = "favourable", "NS-10"
                elif calculated_score <= 6: services_rating, bucket = "partially favourable", "NS-11"
                else: services_rating, bucket = "average", "NS-12"
            else:
                rule_matched.append("Revenue < $50,000,000")
                if calculated_score <= 1: services_rating, bucket = "very favourable", "NS-13"
                elif calculated_score <= 2: services_rating, bucket = "favourable", "NS-14"
                elif calculated_score <= 4: services_rating, bucket = "partially favourable", "NS-15"
                else: services_rating, bucket = "average", "NS-16"

            p_factors, r_factors = [], []
            if "favourable" in services_rating:
                p_factors.append(f"Favourable sub-industry profile ({sub_ind_count} sub-industries, {appetite_label} appetite)")
            if "unfavourable" in services_rating or "average" in services_rating:
                r_factors.append(f"Elevated sub-industry risk multiplier ({appetite_label} x{multiplier})")

            modifier_scores["Nature of services"] = {
                "score": f"{calculated_score:.1f}",
                "rating": services_rating,
                "confidence": "High",
                "reference": f"{sub_ind_count} Sub-Industries, {appetite_label} (x{multiplier})"
            }
            underwriting_rationale["Nature of services"] = {
                "decision_summary": f"Nature of services exposure score calculated as {calculated_score:.1f} ({sub_ind_count} sub-industries x {multiplier} {appetite_label} multiplier).",
                "rule_id": bucket,
                "rule_name": f"Nature of Services - {services_rating.title()}",
                "rule_description": f"Companies with {sub_ind_count} sub-industries and {appetite_label.lower()} appetite multiplier (x{multiplier}) evaluated against {rev_tier_short} revenue tier.",
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Unique Sub-Industries Count": sub_ind_count,
                    "Worst Sub-Industry Appetite": appetite_label,
                    "Appetite Multiplier": f"x{multiplier}",
                    "Calculated Exposure Score": round(calculated_score, 1)
                },
                "matched_bucket": bucket,
                "assigned_category": services_rating.title(),
                "reason": generate_reason(services_rating.title(), {
                    "Revenue Tier": rev_tier,
                    "Unique Sub-Industries Count": sub_ind_count,
                    "Worst Sub-Industry Appetite": appetite_label,
                    "Appetite Multiplier": f"x{multiplier}",
                    "Calculated Exposure Score": round(calculated_score, 1)
                }, bucket, f"Sub-industry appetite multiplier ({appetite_label} x{multiplier}) maps to {services_rating.title()} exposure."),
                "business_impact": ["Organizations offering highly sensitive services inherently carry higher baseline cyber exposure", "Elevated severity for business interruption impacts"] if "favourable" not in services_rating else ["Streamlined service risk profile reduces inherent cyber liability"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            serv_logger.error(f"Exception: {e}")

        # --- 7. Organizational Complexity ---
        org_logger = get_agent_logger("Organizational Complexity")
        try:
            subs_count = len(reconciled.get("subsidiaries", []))
            
            bucket = ""
            rule_matched = []
            range_str = ""
            if revenue >= 1000000000:
                rule_matched.append("Revenue >= $1,000,000,000")
                if subs_count < 10: org_rating, bucket, range_str = "very favourable", "OC-01", "Subsidiaries < 10"
                elif subs_count <= 20: org_rating, bucket, range_str = "favourable", "OC-02", "Subsidiaries <= 20"
                elif subs_count <= 50: org_rating, bucket, range_str = "average", "OC-03", "Subsidiaries <= 50"
                else: org_rating, bucket, range_str = "partially unfavourable", "OC-04", "Subsidiaries > 50"
            elif revenue >= 250000000:
                rule_matched.append("Revenue >= $250,000,000")
                if subs_count < 7: org_rating, bucket, range_str = "very favourable", "OC-05", "Subsidiaries < 7"
                elif subs_count <= 15: org_rating, bucket, range_str = "favourable", "OC-06", "Subsidiaries <= 15"
                elif subs_count <= 30: org_rating, bucket, range_str = "average", "OC-07", "Subsidiaries <= 30"
                else: org_rating, bucket, range_str = "partially unfavourable", "OC-08", "Subsidiaries > 30"
            elif revenue >= 50000000:
                rule_matched.append("Revenue >= $50,000,000")
                if subs_count < 5: org_rating, bucket, range_str = "very favourable", "OC-09", "Subsidiaries < 5"
                elif subs_count <= 10: org_rating, bucket, range_str = "favourable", "OC-10", "Subsidiaries <= 10"
                elif subs_count <= 15: org_rating, bucket, range_str = "average", "OC-11", "Subsidiaries <= 15"
                else: org_rating, bucket, range_str = "partially unfavourable", "OC-12", "Subsidiaries > 15"
            else:
                rule_matched.append("Revenue < $50,000,000")
                if subs_count < 3: org_rating, bucket, range_str = "very favourable", "OC-13", "Subsidiaries < 3"
                elif subs_count <= 6: org_rating, bucket, range_str = "favourable", "OC-14", "Subsidiaries <= 6"
                elif subs_count <= 10: org_rating, bucket, range_str = "average", "OC-15", "Subsidiaries <= 10"
                else: org_rating, bucket, range_str = "partially unfavourable", "OC-16", "Subsidiaries > 10"
            
            rule_matched.append(range_str)
            p_factors, r_factors = [], []
            if "favourable" in org_rating: p_factors.append(f"Highly consolidated corporate structure ({subs_count} subsidiaries)")
            if "unfavourable" in org_rating: r_factors.append(f"Complex corporate structure ({subs_count} subsidiaries)")

            modifier_scores["Organizational Complexity"] = {
                "score": subs_count,
                "rating": org_rating,
                "confidence": "High",
                "reference": f"{subs_count} Subsidiaries"
            }
            underwriting_rationale["Organizational Complexity"] = {
                "decision_summary": f"Structural risk evaluated against {subs_count} known subsidiaries.",
                "rule_id": bucket,
                "rule_name": f"{rev_tier_short} - {org_rating.title()} Organizational Complexity",
                "rule_description": f"Companies in the {rev_tier_short} tier with {range_str.lower().replace('subsidiaries', 'known subsidiaries')} are considered {org_rating.title()} complexity.",
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Subsidiaries Count": subs_count
                },
                "matched_bucket": bucket,
                "assigned_category": org_rating.title(),
                "reason": generate_reason(org_rating.title(), {"Revenue Tier": rev_tier,
                    "Subsidiaries Count": subs_count}, bucket, f"Companies in the {rev_tier_short} tier with {range_str.lower()} are classified as {org_rating.title()} due to organizational complexity."),
                "business_impact": ["A higher number of corporate entities correlates with decentralized IT environments", "Increased structural complexity elevates cyber risk and visibility challenges"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            org_logger.error(f"Exception: {e}")

        # --- 8. Privacy Regulation ---
        priv_logger = get_agent_logger("Privacy Regulation")
        try:
            has_policy = reconciled.get("privacy_policy_published", False)
            mentions = reconciled.get("compliance_mentions", [])
            m_count = len(mentions)
        
            rule_matched = []
            if has_policy:
                rule_matched.append("Privacy Policy Published == True")
                if m_count >= 2: 
                    priv_rating, bucket = "favourable", "PR-01"
                    rule_matched.append("Compliance Frameworks >= 2")
                    desc = "Clear public privacy policy coupled with multiple compliance framework mentions denotes strong data governance."
                elif m_count == 1: 
                    priv_rating, bucket = "partially favourable", "PR-02"
                    rule_matched.append("Compliance Frameworks == 1")
                    desc = "Public privacy policy and baseline compliance framework adherence."
                else:
                    priv_rating, bucket = "average", "PR-03"
                    rule_matched.append("Compliance Frameworks == 0")
                    desc = "Public privacy policy exists, but no specific compliance frameworks explicitly mapped."
            else:
                rule_matched.append("Privacy Policy Published == False")
                priv_rating, bucket = "partially unfavourable", "PR-04"
                desc = "Failure to discover a public privacy policy indicates potential regulatory negligence or opacity."
            
            p_factors, r_factors = [], []
            if has_policy: p_factors.append("Public privacy policy is available")
            else: r_factors.append("No public privacy policy discovered")
            if m_count > 0: p_factors.append(f"Adheres to {m_count} compliance frameworks ({', '.join(mentions)})")
            
            modifier_scores["Privacy Regulation"] = {
                "score": "",
                "rating": priv_rating,
                "confidence": "High",
                "reference": f"Policy: {'Published' if has_policy else 'None'}, Frameworks: {m_count}"
            }
            underwriting_rationale["Privacy Regulation"] = {
                "decision_summary": f"Privacy maturity evaluated based on policy availability and framework adherence.",
                "rule_id": bucket,
                "rule_name": f"Privacy Regulation - {priv_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Privacy Policy Found": "Yes" if has_policy else "No",
                    "Compliance Frameworks": m_count,
                    "Detected Frameworks": ", ".join(mentions) if mentions else "None"
                },
                "matched_bucket": bucket,
                "assigned_category": priv_rating.title(),
                "reason": generate_reason(priv_rating.title(), {"Privacy Policy Found": "Yes" if has_policy else "No",
                    "Compliance Frameworks": m_count,
                    "Detected Frameworks": ", ".join(mentions) if mentions else "None"}, bucket, desc),
                "business_impact": ["Strong adherence to standardized privacy regulations generally demonstrates mature data governance", "Reduces liability in the event of regulatory audits"] if "favourable" in priv_rating else ["Increased likelihood of regulatory fines", "Poor data governance posture"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            priv_logger.error(f"Exception: {e}")

        # --- 9. Seasonality of Sales ---
        seas_logger = get_agent_logger("Seasonality of sales")
        try:
            q_rev = reconciled.get("quarterly_revenue", [])
            sic_codes = reconciled.get("sic_codes", ["7372"])
            sic = sic_codes[0] if sic_codes else "7372"
            cv = None
            
            rule_matched = []
            if len(q_rev) >= 4:
                rule_matched.append(f"Quarterly Revenue Data Points >= 4")
                mean = np.mean(q_rev)
                std = np.std(q_rev)
                if mean > 0:
                    cv = std / mean
                    if cv < 0.1: 
                        season_rating, bucket = "favourable", "SS-01"
                        rule_matched.append("Coefficient of Variation (CV) < 0.1")
                        desc = "Extremely stable quarterly revenue with negligible seasonality."
                    elif cv <= 0.25: 
                        season_rating, bucket = "average", "SS-02"
                        rule_matched.append("0.1 <= Coefficient of Variation (CV) <= 0.25")
                        desc = "Standard revenue volatility within normal operational bounds."
                    else: 
                        season_rating, bucket = "partially unfavourable", "SS-03"
                        rule_matched.append("Coefficient of Variation (CV) > 0.25")
                        desc = "High revenue volatility indicating significant seasonal peaks."
                else:
                    season_rating, bucket = "average", "SS-04"
                    rule_matched.append("Mean Revenue == 0 (Fallback)")
                    desc = "Zero mean revenue detected, falling back to average assumption."
            else:
                rule_matched.append(f"Quarterly Revenue Data Points < 4")
                if sic == "5311": 
                    season_rating, bucket = "partially unfavourable", "SS-05"
                    rule_matched.append("Primary SIC == 5311 (Retail Fallback)")
                    desc = "Missing quarterly data, but industry SIC indicates retail, which is inherently seasonal."
                else: 
                    season_rating, bucket = "average", "SS-06"
                    rule_matched.append(f"Primary SIC != 5311 (Standard Fallback)")
                    desc = "Missing quarterly data; standard industry defaults applied."
                
            p_factors, r_factors = [], []
            if cv is not None and cv < 0.1: p_factors.append("Highly consistent, non-seasonal revenue streams")
            if cv is not None and cv > 0.25: r_factors.append("Significant revenue seasonality detected")

            modifier_scores["Seasonality of sales"] = {
                "score": round(cv, 3) if cv is not None else "",
                "rating": season_rating,
                "confidence": "High" if cv is not None else "Medium",
                "reference": f"CV: {cv:.3f}" if cv is not None else f"SIC Fallback ({sic})"
            }
            underwriting_rationale["Seasonality of sales"] = {
                "decision_summary": f"Revenue volatility evaluated using Coefficient of Variation or Industry heuristics.",
                "rule_id": bucket,
                "rule_name": f"Seasonality of Sales - {season_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Data Points": len(q_rev),
                    "Primary SIC": sic,
                    "Coefficient of Variation (CV)": f"{cv:.3f}" if cv is not None else "N/A"
                },
                "matched_bucket": bucket,
                "assigned_category": season_rating.title(),
                "reason": generate_reason(season_rating.title(), {"Data Points": len(q_rev),
                    "Primary SIC": sic,
                    "Coefficient of Variation (CV)": f"{cv:.3f}" if cv is not None else "N/A"}, bucket, desc),
                "business_impact": ["High seasonality implies that operational outages during peak periods would have a disproportionately severe financial impact"] if "unfavourable" in season_rating else ["Stable revenue means business interruption losses are predictable and linear"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            seas_logger.error(f"Exception: {e}")

        # --- 10. Volatility/Recovery in Sales ---
        vol_logger = get_agent_logger("Volatility/Recovery in Sales")
        try:
            # Baseline factors (D1, D2, D3) from reconciled profile
            d1_base = int(reconciled.get("digital_exposure", 3))
            d2_base = int(reconciled.get("disruption_speed", 3))
            d3_base = int(reconciled.get("recovery_complexity", 3))

            # Evidence-based adjustments (-1 / 0 / +1)
            d1_adj = int(reconciled.get("d1_adjustment", 0))
            d2_adj = int(reconciled.get("d2_adjustment", 0))
            d3_adj = int(reconciled.get("d3_adjustment", 0))

            # Clamped factor scores [1..5]
            d1_final = max(1, min(5, d1_base + d1_adj))
            d2_final = max(1, min(5, d2_base + d2_adj))
            d3_final = max(1, min(5, d3_base + d3_adj))

            base_total = d1_final + d2_final + d3_final

            # Sales condition overlay (-1 / 0 / +1)
            has_sales_spikes = reconciled.get("has_sales_spikes", False)
            if "sales_condition_overlay" in reconciled:
                overlay = int(reconciled.get("sales_condition_overlay", 0))
            else:
                overlay = 1 if has_sales_spikes else -1

            adjusted_total = max(2, min(16, base_total + overlay))

            rule_matched = []
            if adjusted_total <= 4:
                vol_rating, bucket = "favourable", "VR-01"
                rule_matched.append("Adjusted Total Score 2-4 (Favourable)")
                desc = "Minimal digital revenue exposure, rapid recovery velocity, and highly resilient sales infrastructure."
            elif adjusted_total <= 8:
                vol_rating, bucket = "partially favourable", "VR-02"
                rule_matched.append("Adjusted Total Score 5-8 (Partially Favourable)")
                desc = "Moderate digital exposure and manageable sales disruption timelines."
            elif adjusted_total <= 12:
                vol_rating, bucket = "average", "VR-03"
                rule_matched.append("Adjusted Total Score 9-12 (Average)")
                desc = "Standard industry digital exposure with average sales disruption and recovery complexity."
            else:
                vol_rating, bucket = "partially unfavourable", "VR-04"
                rule_matched.append("Adjusted Total Score 13-16 (Partially Unfavourable)")
                desc = "High digital exposure with complex, extended sales recovery workflows."

            p_factors, r_factors = [], []
            if adjusted_total <= 8:
                p_factors.append("Low sales volatility and agile recovery potential")
            if adjusted_total >= 13:
                r_factors.append("High digital reliance and complex sales disruption recovery")

            modifier_scores["Volatility/Recovery in Sales"] = {
                "score": float(adjusted_total),
                "rating": vol_rating,
                "confidence": "High",
                "reference": f"D1: {d1_final}/5, D2: {d2_final}/5, D3: {d3_final}/5, Overlay: {overlay:+d}, Total: {adjusted_total}"
            }
            underwriting_rationale["Volatility/Recovery in Sales"] = {
                "decision_summary": f"Volatility & Sales Recovery score calculated as {adjusted_total} (Base: {base_total}, Overlay: {overlay:+d}).",
                "rule_id": bucket,
                "rule_name": f"Volatility & Recovery - {vol_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "D1 Digital Exposure": d1_final,
                    "D2 Disruption Velocity": d2_final,
                    "D3 Recovery Complexity": d3_final,
                    "Base Total Score": base_total,
                    "Sales Condition Overlay": overlay,
                    "Adjusted Total Score": adjusted_total
                },
                "matched_bucket": bucket,
                "assigned_category": vol_rating.title(),
                "reason": generate_reason(vol_rating.title(), {
                    "D1 Digital Exposure": d1_final,
                    "D2 Disruption Velocity": d2_final,
                    "D3 Recovery Complexity": d3_final,
                    "Adjusted Total Score": adjusted_total
                }, bucket, desc),
                "business_impact": ["Higher volatility indicates greater difficulty and extended timelines for business recovery following a cyber event", "Increased business interruption limits required"] if "unfavourable" in vol_rating else ["Streamlined recovery processes limit prolonged business interruption costs"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            vol_logger.error(f"Exception: {e}")

        # --- 11. Applicability of Privacy Regulation ---
        appl_logger = get_agent_logger("Applicability of Privacy Regulation")
        try:
            sic_codes = reconciled.get("sic_codes") or []
            sic = str(sic_codes[0]) if sic_codes else ""
            cust_type = str(reconciled.get("customer_type", "B2B")).upper()
            has_ecom = bool(reconciled.get("has_ecommerce", False))

            is_high_risk_industry = sic.startswith(("737", "80", "6"))
            is_strict = (is_high_risk_industry or cust_type in ["B2C", "MIX"] or has_ecom)

            rule_matched = []
            if not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type and not has_ecom:
                appl_rating, bucket = "favourable", "AP-01"
                rule_matched.append("High Risk Industry == False")
                rule_matched.append("Customer Type == 'B2B'")
                rule_matched.append("Ecommerce == False")
                desc = "B2B companies in standard industries without ecommerce face the lowest regulatory burden."
            elif not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type:
                appl_rating, bucket = "partially favourable", "AP-02"
                rule_matched.append("High Risk Industry == False")
                rule_matched.append("Customer Type == 'B2B'")
                rule_matched.append("Ecommerce == True")
                desc = "B2B companies in standard industries with ecommerce face moderate regulatory oversight (mostly PCI)."
            else:
                appl_rating, bucket = "average", "AP-03"
                rule_matched.append("High Risk Industry == True OR Customer Type IN ('B2C', 'MIX')")
                desc = "Companies in high-risk sectors (Finance, Health) or heavily consumer-facing face stringent privacy regulations."

            p_factors, r_factors = [], []
            if is_high_risk_industry: r_factors.append(f"Operating in highly regulated sector (SIC: {sic})")
            if not is_high_risk_industry and "B2B" in cust_type: p_factors.append("Low overall regulatory footprint")

            modifier_scores["Applicability of Privacy Regulation"] = {
                "score": "",
                "rating": appl_rating,
                "confidence": "High",
                "reference": f"High Risk Sector: {'Yes' if is_high_risk_industry else 'No'}, Audience: {cust_type}"
            }
            underwriting_rationale["Applicability of Privacy Regulation"] = {
                "decision_summary": f"Privacy regulation applicability assessed based on primary industry and audience.",
                "rule_id": bucket,
                "rule_name": f"Privacy Applicability - {appl_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Primary SIC": sic,
                    "High Risk Industry": "Yes" if is_high_risk_industry else "No",
                    "Customer Type": cust_type,
                    "Has Ecommerce": "Yes" if has_ecom else "No"
                },
                "matched_bucket": bucket,
                "assigned_category": appl_rating.title(),
                "reason": generate_reason(appl_rating.title(), {"Primary SIC": sic,
                    "High Risk Industry": "Yes" if is_high_risk_industry else "No",
                    "Customer Type": cust_type,
                    "Has Ecommerce": "Yes" if has_ecom else "No"}, bucket, desc),
                "business_impact": ["The company's primary industry sector involves strict privacy regulations (e.g., healthcare/financial data)", "Significantly increased regulatory liability and potential fines in the event of a breach"] if is_strict else ["Standard regulatory requirements apply", "Lower risk of multi-million dollar regulatory fines"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            appl_logger.error(f"Exception: {e}")

        # --- 12. B2C End Products ---
        b2c_logger = get_agent_logger("B2C End Products")
        try:
            rule_matched = []
            if ("B2C" in cust_type and "B2B" in cust_type) or "MIX" in cust_type:
                b2c_rating, bucket = "partially favourable", "B2C-01"
                rule_matched.append("Customer Type == 'MIX'")
                desc = "Mixed B2B and B2C operations."
            elif "B2C" in cust_type or "CONSUMER" in cust_type or "SMB" in cust_type:
                b2c_rating, bucket = "favourable", "B2C-02"
                rule_matched.append("Customer Type == 'B2C' OR 'SMB'")
                desc = "Pure B2C/SMB focused operations."
            else:
                b2c_rating, bucket = "average", "B2C-03"
                rule_matched.append("Customer Type == 'B2B' (Default)")
                desc = "B2B focused operations."
            
            modifier_scores["B2C End Products"] = {
                "score": "",
                "rating": b2c_rating,
                "confidence": "High",
                "reference": f"Customer Type: {cust_type}"
            }
            underwriting_rationale["B2C End Products"] = {
                "decision_summary": f"Consumer exposure evaluated based on customer type.",
                "rule_id": bucket,
                "rule_name": f"B2C End Products - {b2c_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Customer Type": cust_type
                },
                "matched_bucket": bucket,
                "assigned_category": b2c_rating.title(),
                "reason": generate_reason(b2c_rating.title(), {"Customer Type": cust_type}, bucket, desc),
                "business_impact": ["Direct-to-consumer businesses generally collect and retain more granular personally identifiable information (PII)"],
                "positive_factors": [],
                "risk_factors": []
            }
        except Exception as e:
            b2c_logger.error(f"Exception: {e}")

        # --- 13. Years in business ---
        yib_logger = get_agent_logger("Years in business")
        try:
            founding_year = reconciled.get("founding_year")
            current_year = datetime.now().year
            yib = None
            
            if founding_year is not None:
                try: yib = int(current_year) - int(founding_year)
                except: pass

            bucket = ""
            rule_matched = []
            range_str = ""
            if yib is not None and yib >= 0:
                if revenue >= 1000000000:
                    rule_matched.append("Revenue >= $1,000,000,000")
                    if yib > 30: yib_rating, bucket, range_str = "very favourable", "YB-01", "> 30 years"
                    elif yib >= 20: yib_rating, bucket, range_str = "favourable", "YB-02", "20 - 30 years"
                    elif yib >= 10: yib_rating, bucket, range_str = "partially favourable", "YB-03", "10 - 19 years"
                    elif yib >= 5: yib_rating, bucket, range_str = "average", "YB-04", "5 - 9 years"
                    else: yib_rating, bucket, range_str = "unfavourable", "YB-05", "< 5 years"
                elif revenue >= 250000000:
                    rule_matched.append("Revenue >= $250,000,000")
                    if yib > 20: yib_rating, bucket, range_str = "very favourable", "YB-06", "> 20 years"
                    elif yib >= 10: yib_rating, bucket, range_str = "favourable", "YB-07", "10 - 20 years"
                    elif yib >= 5: yib_rating, bucket, range_str = "partially favourable", "YB-08", "5 - 9 years"
                    elif yib >= 3: yib_rating, bucket, range_str = "average", "YB-09", "3 - 4 years"
                    else: yib_rating, bucket, range_str = "unfavourable", "YB-10", "< 3 years"
                elif revenue >= 50000000:
                    rule_matched.append("Revenue >= $50,000,000")
                    if yib > 10: yib_rating, bucket, range_str = "very favourable", "YB-11", "> 10 years"
                    elif yib >= 7: yib_rating, bucket, range_str = "favourable", "YB-12", "7 - 10 years"
                    elif yib >= 4: yib_rating, bucket, range_str = "partially favourable", "YB-13", "4 - 6 years"
                    elif yib >= 2: yib_rating, bucket, range_str = "average", "YB-14", "2 - 3 years"
                    else: yib_rating, bucket, range_str = "unfavourable", "YB-15", "< 2 years"
                else:
                    rule_matched.append("Revenue < $50,000,000")
                    if yib > 7: yib_rating, bucket, range_str = "very favourable", "YB-16", "> 7 years"
                    elif yib >= 5: yib_rating, bucket, range_str = "favourable", "YB-17", "5 - 7 years"
                    elif yib >= 3: yib_rating, bucket, range_str = "partially favourable", "YB-18", "3 - 4 years"
                    elif yib >= 1: yib_rating, bucket, range_str = "average", "YB-19", "1 - 2 years"
                    else: yib_rating, bucket, range_str = "unfavourable", "YB-20", "< 1 year"
                rule_matched.append(f"Operating History {range_str}")
            else:
                yib_rating, bucket = "average", "YB-21"
                rule_matched.append("Founding Year == Unknown")
                range_str = "N/A"

            desc = f"Companies in the {rev_tier_short} tier operating for {range_str.replace('years', 'years')} are considered {yib_rating.title()} maturity."

            p_factors, r_factors = [], []
            if yib is not None and "favourable" in yib_rating: p_factors.append(f"Established operational history ({yib} years)")
            if yib is not None and "unfavourable" in yib_rating: r_factors.append(f"Immature operational history ({yib} years)")

            modifier_scores["Years in business"] = {
                "score": yib if yib is not None else "",
                "rating": yib_rating,
                "confidence": "High" if founding_year is not None else "Medium",
                "reference": f"Founding Year: {founding_year or 'N/A'} ({yib if yib is not None else 'N/A'} yrs)"
            }
            underwriting_rationale["Years in business"] = {
                "decision_summary": f"Maturity evaluated based on operational history of {yib if yib is not None else 'unknown'} years.",
                "rule_id": bucket,
                "rule_name": f"{rev_tier_short} - {yib_rating.title()} Maturity",
                "rule_description": desc,
                "rule_conditions": rule_matched,
                "input_values": {
                    "Revenue Tier": rev_tier,
                    "Founding Year": founding_year or "Unknown",
                    "Calculated Age": yib if yib is not None else "Unknown"
                },
                "matched_bucket": bucket,
                "assigned_category": yib_rating.title(),
                "reason": generate_reason(yib_rating.title(), {"Revenue Tier": rev_tier,
                    "Founding Year": founding_year or "Unknown",
                    "Calculated Age": yib if yib is not None else "Unknown"}, bucket, desc),
                "business_impact": ["Established organizations typically exhibit more mature cybersecurity practices", "Higher resilience and institutional knowledge compared to newer ventures"] if "favourable" in yib_rating else ["Newer ventures may lack formalized cybersecurity practices and governance frameworks"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            yib_logger.error(f"Exception: {e}")

        # --- 14. Cybersecurity Info ---
        ci_logger = get_agent_logger("Cybersecurity Info")
        try:
            frameworks = reconciled.get("cybersecurity_frameworks", [])
            has_dmarc_spf = reconciled.get("has_dmarc_spf", True)
            has_sec_headers = reconciled.get("has_security_headers", True)
            has_sec_txt = reconciled.get("has_security_txt", False)
            has_ciso = reconciled.get("has_ciso_disclosure", False)
            is_public = reconciled.get("revenue", 0) >= 1000000000 or reconciled.get("entity_status") == "Public"

            has_audited_cert = any(fw.lower() in ["iso 27001", "iso/iec 27001", "soc 2 type ii", "fedramp"] for fw in frameworks)
            has_framework_align = any(fw.lower() in ["nist csf", "nist", "cis controls", "owasp", "cloud security alliance", "csa"] for fw in frameworks)

            if has_audited_cert: p1_score = 2.0
            elif has_framework_align: p1_score = 3.0
            else: p1_score = 3.5

            if has_dmarc_spf and has_sec_headers: p2_score = 2.0
            elif has_dmarc_spf or has_sec_headers or has_sec_txt: p2_score = 3.0
            else: p2_score = 5.0

            p3_score = 2.0 if has_ciso else 4.0

            rule_conditions = []
            if is_public:
                ci_score = round(0.40 * p1_score + 0.40 * p2_score + 0.20 * p3_score, 1)
                rule_conditions.append("Entity Type = Public Company (40% Certs + 40% Live Web + 20% SEC CISO)")
            else:
                ci_score = round(0.50 * p1_score + 0.50 * p2_score, 1)
                rule_conditions.append("Entity Type = Private Company (50% Certs + 50% Live Web)")

            rule_conditions.append(f"Disclosed Frameworks: {frameworks if frameworks else 'None Discovered'}")
            rule_conditions.append(f"Web Security: DMARC/SPF={has_dmarc_spf}, Headers={has_sec_headers}, security.txt={has_sec_txt}")
            if is_public:
                rule_conditions.append(f"SEC CISO Disclosure = {has_ciso}")

            if ci_score <= 2.8: ci_rating, bucket = "favourable", "CI-01"
            elif ci_score <= 3.8: ci_rating, bucket = "partially favourable", "CI-02"
            elif ci_score <= 4.5: ci_rating, bucket = "average", "CI-03"
            else: ci_rating, bucket = "partially unfavourable", "CI-04"

            desc = f"Cybersecurity Info score evaluated as {ci_score:.1f} based on policy frameworks, live web security defense, and executive governance."
            p_factors, r_factors = [], []
            if "favourable" in ci_rating: p_factors.append("Formal cybersecurity framework adoption & strong web security controls")
            if "unfavourable" in ci_rating: r_factors.append("Unmitigated web security vulnerabilities (missing DMARC/SPF or security headers)")

            modifier_scores["Cybersecurity Info"] = {
                "score": f"{ci_score:.1f}",
                "rating": ci_rating,
                "confidence": "High",
                "reference": f"Certs: {len(frameworks)}, Web Security: {'Strong' if has_dmarc_spf and has_sec_headers else 'Baseline'}"
            }
            underwriting_rationale["Cybersecurity Info"] = {
                "decision_summary": f"Cybersecurity Info score calculated as {ci_score:.1f}.",
                "rule_id": bucket,
                "rule_name": f"Cybersecurity Info - {ci_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_conditions,
                "input_values": {
                    "Entity Classification": "Public" if is_public else "Private",
                    "Disclosed Frameworks": frameworks,
                    "DMARC/SPF Protection": has_dmarc_spf,
                    "Security Headers": has_sec_headers,
                    "CISO Governance Disclosed": has_ciso,
                    "Calculated CI Score": ci_score
                },
                "matched_bucket": bucket,
                "assigned_category": ci_rating.title(),
                "reason": generate_reason(ci_rating.title(), {
                    "Entity Classification": "Public" if is_public else "Private",
                    "Disclosed Frameworks": frameworks,
                    "Calculated CI Score": ci_score
                }, bucket, desc),
                "business_impact": ["Strong operational cybersecurity practices reduce likelihood and severity of ransomware incidents"] if "favourable" in ci_rating else ["Unmitigated security posture increases operational vulnerability"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            ci_logger.error(f"Exception: {e}")

        # --- 15. Industry & Company Breach History ---
        bh_logger = get_agent_logger("Industry & Company Breach History")
        try:
            sic_list = reconciled.get("sic_codes", [])
            primary_sic = str(sic_list[0]) if isinstance(sic_list, list) and sic_list else None
            
            if not primary_sic:
                naics = str(reconciled.get("naics_code", ""))
                sub_ind_str = str(reconciled.get("sub_industries", [])).lower()
                c_name_str = str(reconciled.get("company_name", "")).lower()
                if naics.startswith("524") or "insurance" in sub_ind_str or "insurance" in c_name_str:
                    primary_sic = "6331"
                elif naics.startswith("511") or naics.startswith("5415") or "software" in sub_ind_str:
                    primary_sic = "7372"
                elif naics.startswith("622") or naics.startswith("621") or "health" in sub_ind_str:
                    primary_sic = "8062"
                else:
                    primary_sic = "6331" if "insurance" in c_name_str else "7372"
            
            very_high_sics = ["6331", "6311", "6321", "8011", "8062", "5311", "9111"]
            high_sics = ["7372", "7371", "7373", "4813"]
            mod_sics = ["3571", "5045", "5731"]
            
            if primary_sic in very_high_sics: ind_score = 4; ind_tier = "Very High"
            elif primary_sic in high_sics: ind_score = 3; ind_tier = "High"
            elif primary_sic in mod_sics: ind_score = 2; ind_tier = "Moderate"
            else: ind_score = 1; ind_tier = "Low"

            breaches = reconciled.get("company_breaches", [])
            sec_incidents = reconciled.get("sec_cyber_incidents", [])
            is_public = reconciled.get("revenue", 0) >= 1000000000 or reconciled.get("entity_status") == "Public"
            
            raw_breach_list = []
            if isinstance(breaches, list): raw_breach_list.extend(breaches)
            elif breaches: raw_breach_list.append(breaches)

            if isinstance(sec_incidents, list): raw_breach_list.extend(sec_incidents)
            elif sec_incidents: raw_breach_list.append(sec_incidents)
            
            has_breach_signal = len(raw_breach_list) > 0 or reconciled.get("has_cyber_breach", False)
            
            itemized_details = []
            import re
            
            if raw_breach_list:
                for idx, b in enumerate(raw_breach_list):
                    b_name = f"Incident #{idx+1}"
                    b_type = "Data Breach"
                    b_year = 2024.0
                    base_pts = 1
                    
                    if isinstance(b, dict):
                        b_name = b.get("name", b_name)
                        b_type = b.get("incident_type", b.get("type", "Data Breach"))
                        b_year = float(b.get("year", b.get("recency_years", 2024.0)))
                        base_pts = int(b.get("severity_pts", b.get("base_pts", 2)))
                    else:
                        b_str = str(b)
                        b_name = b_str[:40] if len(b_str) > 40 else b_str
                        yr_match = re.search(r'\b(19\d\d|20\d\d)\b', b_str)
                        if yr_match:
                            b_year = float(yr_match.group(1))
                        
                        b_lower = b_str.lower()
                        if "8-k" in b_lower or "material" in b_lower or "ransomware" in b_lower or ">1m" in b_lower or "major" in b_lower:
                            base_pts = 4
                            b_type = "Material 8-K / Ransomware"
                        elif "100k" in b_lower or "significant" in b_lower:
                            base_pts = 3
                            b_type = "Significant Breach (100k-1M)"
                        elif "10k" in b_lower or "moderate" in b_lower:
                            base_pts = 2
                            b_type = "Moderate Breach (10k-100k)"
                        else:
                            base_pts = 1
                            b_type = "Minor Credential Exposure"

                    age = max(0.0, 2026.0 - b_year)
                    if age < 1.0: recency_mult = 2.0
                    elif age <= 2.0: recency_mult = 1.5
                    elif age <= 5.0: recency_mult = 1.0
                    elif age <= 10.0: recency_mult = 0.5
                    else: recency_mult = 0.0
                    
                    pts = round(base_pts * recency_mult, 1)
                    itemized_details.append({
                        "name": b_name,
                        "deal_type": b_type,
                        "recency": f"{int(b_year)}" if b_year > 1900 else f"{age:.1f} yrs ago",
                        "base_pts": base_pts,
                        "multiplier": recency_mult,
                        "points": pts
                    })

            worst_incident_score = max((item["points"] for item in itemized_details), default=0.0) if itemized_details else 0.0
            repeat_kicker = min(3, len(itemized_details) - 1) if len(itemized_details) > 1 else 0
            
            cisa_kev_matches = reconciled.get("cisa_kev_matches", [])
            has_cisa_kev = reconciled.get("has_cisa_kev_vulnerabilities", False) or len(cisa_kev_matches) > 0
            cisa_kev_penalty = min(3, len(cisa_kev_matches)) if has_cisa_kev else 0

            company_score = round(worst_incident_score + repeat_kicker + cisa_kev_penalty, 1)
            combined_score = round(ind_score + company_score, 1)

            rule_conditions = []
            rule_conditions.append(f"Primary SIC = {primary_sic} (DBIR Industry Breach Frequency: {ind_tier}, {ind_score} pts)")
            rule_conditions.append(f"Confirmed Company Breaches = {len(itemized_details)} (Company Score: {company_score} pts [Worst: {worst_incident_score:.1f} pts, Kicker: +{repeat_kicker} pt, CISA KEV Penalty: +{cisa_kev_penalty} pt])")
            if has_cisa_kev:
                rule_conditions.append(f"CISA KEV Active Exploited Vulnerabilities Matched: {len(cisa_kev_matches)} (+{cisa_kev_penalty} pt penalty)")

            if revenue >= 1000000000:
                rule_conditions.append("Revenue Tier >= $1B")
                if combined_score <= 2: bh_rating, bucket = "very favourable", "BH-01"
                elif combined_score <= 5: bh_rating, bucket = "favourable", "BH-02"
                elif combined_score <= 8: bh_rating, bucket = "partially favourable", "BH-03"
                elif combined_score <= 11: bh_rating, bucket = "average", "BH-04"
                elif combined_score <= 14: bh_rating, bucket = "partially unfavourable", "BH-05"
                else: bh_rating, bucket = "unfavourable", "BH-06"
            elif revenue >= 250000000:
                rule_conditions.append("Revenue Tier $250M - $1B")
                if combined_score <= 1: bh_rating, bucket = "very favourable", "BH-07"
                elif combined_score <= 4: bh_rating, bucket = "favourable", "BH-08"
                elif combined_score <= 7: bh_rating, bucket = "partially favourable", "BH-09"
                elif combined_score <= 10: bh_rating, bucket = "average", "BH-10"
                elif combined_score <= 13: bh_rating, bucket = "partially unfavourable", "BH-11"
                else: bh_rating, bucket = "unfavourable", "BH-12"
            elif revenue >= 50000000:
                rule_conditions.append("Revenue Tier $50M - $250M")
                if combined_score <= 1: bh_rating, bucket = "very favourable", "BH-13"
                elif combined_score <= 3: bh_rating, bucket = "favourable", "BH-14"
                elif combined_score <= 6: bh_rating, bucket = "partially favourable", "BH-15"
                elif combined_score <= 9: bh_rating, bucket = "average", "BH-16"
                elif combined_score <= 12: bh_rating, bucket = "partially unfavourable", "BH-17"
                else: bh_rating, bucket = "unfavourable", "BH-18"
            else:
                rule_conditions.append("Revenue Tier < $50M")
                if combined_score <= 0: bh_rating, bucket = "very favourable", "BH-19"
                elif combined_score <= 2: bh_rating, bucket = "favourable", "BH-20"
                elif combined_score <= 4: bh_rating, bucket = "partially favourable", "BH-21"
                elif combined_score <= 7: bh_rating, bucket = "average", "BH-22"
                elif combined_score <= 10: bh_rating, bucket = "partially unfavourable", "BH-23"
                else: bh_rating, bucket = "unfavourable", "BH-24"

            if not is_public and not has_breach_signal:
                if bh_rating in ["very favourable", "favourable", "partially favourable"]:
                    bh_rating = "average"
                    rule_conditions.append("Private Entity Zero-Breach Floor Applied: Rating capped at Average due to lack of SEC 8-K disclosure obligations")

            desc = f"Industry & Company Breach History evaluated as {combined_score:.1f} (Industry: {ind_score} pts, Company: {company_score} pts)."
            p_factors, r_factors = [], []
            if "favourable" in bh_rating: p_factors.append("Clean company breach history in low-to-moderate risk industry sector")
            if "unfavourable" in bh_rating or "average" in bh_rating: r_factors.append(f"Operating in {ind_tier} breach frequency sector ({primary_sic})")

            modifier_scores["Industry & Company Breach History"] = {
                "score": f"{combined_score:.1f}",
                "rating": bh_rating,
                "confidence": "High" if is_public else "Medium",
                "reference": f"Industry: {ind_tier} ({ind_score} pts), Breaches: {len(itemized_details)}",
                "itemized_details": itemized_details
            }
            underwriting_rationale["Industry & Company Breach History"] = {
                "decision_summary": f"Breach history combined score calculated as {combined_score:.1f}.",
                "rule_id": bucket,
                "rule_name": f"Breach History - {bh_rating.title()}",
                "rule_description": desc,
                "rule_conditions": rule_conditions,
                "input_values": {
                    "Primary SIC": primary_sic,
                    "Industry Breach Tier": ind_tier,
                    "Industry Score": ind_score,
                    "Company Score": company_score,
                    "Combined Score": combined_score
                },
                "matched_bucket": bucket,
                "assigned_category": bh_rating.title(),
                "reason": generate_reason(bh_rating.title(), {
                    "Primary SIC": primary_sic,
                    "Industry Breach Tier": ind_tier,
                    "Combined Score": combined_score
                }, bucket, desc),
                "business_impact": ["Historical security breaches demonstrate elevated threat exposure and potential unmitigated attack vectors"] if "favourable" not in bh_rating else ["No significant historical breach impact detected"],
                "positive_factors": p_factors,
                "risk_factors": r_factors
            }
        except Exception as e:
            bh_logger.error(f"Exception: {e}")

        # Aggregate overall rating
        underwriter_logger.info("START Modifier Aggregation")
        numeric_scores = []
        for name, details in modifier_scores.items():
            rat = details["rating"].lower()
            score_val = RATING_SCORES.get(rat, 4.0)
            numeric_scores.append(score_val)

        avg_score = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 4.0
        if avg_score < 2.0: risk_category = "Very Favourable"
        elif avg_score < 3.0: risk_category = "Favourable"
        elif avg_score < 4.0: risk_category = "Partially Favourable"
        elif avg_score < 4.5: risk_category = "Average"
        elif avg_score < 5.5: risk_category = "Partially Unfavourable"
        else: risk_category = "Unfavourable"

        if state.get("entity_status") == "Mismatch":
            confidence_score = 0.0
            confidence_band = "Low"
        else:
            confidence_score = float(round(accuracy * 100.0, 1))
            if accuracy >= 0.8: confidence_band = "High"
            elif accuracy >= 0.5: confidence_band = "Medium"
            else: confidence_band = "Low"

        human_escalation_flag = False
        if accuracy < 0.5: human_escalation_flag = True
        if mismatch: human_escalation_flag = True
        actual_contradictions = sum(1 for flag in conflicts if not flag.get("parameter", "").endswith("_partial"))
        if actual_contradictions > 0: human_escalation_flag = True

        logs.append(f"Underwriter Verdict: Overall Category = {risk_category} (Confidence: {confidence_score}% - {confidence_band})")



        # Log final summarized outcomes to the Underwriter logger
        underwriter_logger.info("********************************************")
        underwriter_logger.info("[UNDERWRITER] Starting Risk Assessment Summary")
        underwriter_logger.info("********************************************")
        underwriter_logger.info(f"Claims Accuracy: {accuracy*100:.1f}%, Discrepancies Count: {len(conflicts)}")
        underwriter_logger.info("Reconciled Profile Inputs used for mathematical modifiers:")
        underwriter_logger.info(f"- Revenue: {revenue}")
        underwriter_logger.info(f"- Customer Type: {reconciled.get('customer_type')}")
        underwriter_logger.info(f"- Ecommerce: {reconciled.get('has_ecommerce')}")
        underwriter_logger.info(f"- Domains: {len(reconciled.get('domains', []))} domains")
        underwriter_logger.info(f"- Countries: {len(reconciled.get('countries_of_operation', []))} countries")
        underwriter_logger.info(f"- Subsidiaries: {len(reconciled.get('subsidiaries', []))} subsidiaries")
        underwriter_logger.info(f"- Acquisitions: {len(reconciled.get('acquisitions', []))} acquisitions")
        underwriter_logger.info(f"- Founding Year: {reconciled.get('founding_year')}")
        underwriter_logger.info(f"- Has Cyber Breach: {reconciled.get('has_cyber_breach')}")
        underwriter_logger.info(f"- Has Active Litigation: {reconciled.get('has_active_litigation')}")
        underwriter_logger.info(f"- FTC Actions Count: {reconciled.get('ftc_actions_count')}")
        underwriter_logger.info(f"- SSL Grade: {reconciled.get('ssl_grade')}")
        underwriter_logger.info(f"- Detected Tech Count: {len(reconciled.get('detected_technologies', []))}")
        underwriter_logger.info(f"- Primary Country: {reconciled.get('country')}")
        underwriter_logger.info(f"- NAICS Code: {reconciled.get('naics_code')}")
        underwriter_logger.info("----------------------------------------")
        underwriter_logger.info("Final Aggregated Modifiers Result:")
        underwriter_logger.info(f"Average Numeric Score: {avg_score:.3f}")
        underwriter_logger.info(f"Overall Category: {risk_category}")
        underwriter_logger.info(f"Confidence Score: {confidence_score}% ({confidence_band})")
        underwriter_logger.info(f"Human Escalation Required: {human_escalation_flag}")
        underwriter_logger.info("********************************************")

        return {
            "risk_category": risk_category,
            "underwriting_rationale": underwriting_rationale,
            "modifier_scores": modifier_scores,
            "confidence_score": confidence_score,
            "confidence_band": confidence_band,
            "human_escalation_flag": human_escalation_flag,
            "audit_logs": state.get("audit_logs", []) + logs
        }
