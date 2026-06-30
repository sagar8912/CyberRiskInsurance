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
            "services_appetite": "medium_risk",
            "internet_exposure_domains": 1,
            "customer_base_scale": "SMB (<1k)",
            "digital_exposure": 3,
            "disruption_speed": 3,
            "recovery_complexity": 3,
            "founding_year": None
        }

        # 1. Merge logic with priority: SEC > GLEIF/DBCollector > Wikidata > Wikipedia > ResponsesAPI
        sources_order = ["SECCollector", "DBCollector", "Wikidata", "Wikipedia", "ResponsesAPI", "DomainScraper"]

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
            val = get_val(src, "services_appetite")
            if val:
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
            val = get_val(src, "founding_year")
            if val is not None:
                merged["founding_year"] = val
                break

        # Domains / HTTPS — first take what DomainScraper found
        for src in sources_order:
            val = get_val(src, "domains")
            if val:
                merged["domains"] = val
                break



        # Call LLM to reconcile profile and write rationale
        prompt_vars = {
            "company_name": company_name,
            "domain": domain,
            "reports_json": json.dumps(reports)
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
            inferred_sic = self.infer_sic_codes_dynamically(company_name, reports, final_sic)
            logger.info(f"[COORDINATOR] Dynamic SIC inference resolved: {inferred_sic} (original was {final_sic})")
            merged["sic_codes"] = inferred_sic

        # Re-verify USA Presence
        countries_lower = [c.lower() for c in merged["countries_of_operation"]]
        merged["usa_presence"] = ("usa" in countries_lower or "united states" in countries_lower or "us" in countries_lower)

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

    def infer_sic_codes_dynamically(self, company_name: str, reports: Dict[str, Any], existing_sic_codes: List[str] = None) -> List[str]:
        # Gather all industry text indicators from Wikipedia, Wikidata, SEC
        indicators = []
        
        # Check Wikipedia industry classification
        wiki_report = reports.get("Wikipedia", {})
        if wiki_report.get("status") == "success":
            ind_class = wiki_report.get("findings", {}).get("industry_classification", [])
            if isinstance(ind_class, list):
                indicators.extend(ind_class)
                
        # Check Wikidata industry and sub_industries
        wikidata_report = reports.get("Wikidata", {})
        if wikidata_report.get("status") == "success":
            findings = wikidata_report.get("findings", {})
            ind = findings.get("industry", [])
            if isinstance(ind, list):
                indicators.extend(ind)
            sub_ind = findings.get("sub_industries", [])
            if isinstance(sub_ind, list):
                indicators.extend(sub_ind)

        # Check SEC segments/SIC codes
        sec_report = reports.get("SECCollector", {})
        if sec_report.get("status") == "success":
            findings = sec_report.get("findings", {})
            segments = findings.get("business_segments", [])
            if isinstance(segments, list):
                indicators.extend(segments)
            # Check if SEC already provided some SIC codes
            sec_sics = findings.get("sic_codes", [])
            if sec_sics and isinstance(sec_sics, list):
                valid_sec_sics = [str(s) for s in sec_sics if str(s).strip() and str(s).strip() != "7372"]
                if valid_sec_sics:
                    return valid_sec_sics

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

        # 1. Format LLM underwriter prompt to get qualitative assessment
        prompt_vars = {
            "business_rule": self.config.business_rule,
            "inputs_json": json.dumps(reconciled),
            "fact_check_summary": f"Claims Accuracy: {accuracy*100:.1f}%. Discrepancies count: {len(conflicts)}"
        }
        prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
        response_text = self.call_llm(prompt)
        assessment = self.parse_json(response_text)

        # 2. Strict mathematical validation (Option A - no Excel file, coded directly)
        revenue = reconciled.get("revenue") or 0
        modifier_scores = {}
        underwriting_rationale = {}

        from src.utils.logger import get_agent_logger

        # --- 1. Mergers and Acquisitions ---
        ma_logger = get_agent_logger("Mergers and Acquisitions")
        ma_logger.info("========================================")
        ma_logger.info("START Modifier: Mergers and Acquisitions")
        ma_logger.info("========================================")
        try:
            acqs = reconciled.get("acquisitions", [])
            ma_logger.info(f"Input: acquisitions = {json.dumps(acqs)}")
            ma_logger.info(f"Input: revenue = {revenue}")
            ma_logger.info("Math Logic: Points calculated by deal type and recency multiplier. Thresholds depend on revenue tier.")

            ma_points = 0.0
            for i, acq in enumerate(acqs):
                acq_name = acq.get("name", f"Acquisition {i+1}")
                deal_type = str(acq.get("deal_type", "minor acquisition")).lower()
                pts = 1.0
                if "trans" in deal_type:
                    pts = 4.0
                elif "material" in deal_type:
                    pts = 3.0
                elif "minor" in deal_type:
                    pts = 2.0
            
                recency = acq.get("recency_years", 5.0)
                orig_recency = recency
                if recency > 1900:
                    recency = datetime.now().year - recency
            
                mult = 0.0
                if recency < 1.0:
                    mult = 2.0
                elif recency < 2.0:
                    mult = 1.5
                elif recency < 5.0:
                    mult = 1.0
                elif recency <= 10.0:
                    mult = 0.5
                else:
                    mult = 0.0

                acq_points = pts * mult
                ma_points += acq_points
                ma_logger.info(f"Processing acquisition '{acq_name}': deal_type='{deal_type}' -> base_points={pts}, recency_years={orig_recency} (elapsed={recency:.1f} yrs) -> recency_multiplier={mult}. Computed points = {acq_points:.2f}")

            ma_logger.info(f"Total accumulated M&A points: {ma_points:.2f}")

            ma_rating = "average"
            if revenue >= 1000000000:
                ma_logger.info("Revenue Tier: >= $1B")
                ma_logger.info(f"Evaluating ma_points={ma_points:.2f} against thresholds: <=5 Very Favourable, <=10 Favourable, <=15 Partially Favourable, <=20 Average, <=30 Partially Unfavourable, >30 Unfavourable")
                if ma_points <= 5: ma_rating = "very favourable"
                elif ma_points <= 10: ma_rating = "favourable"
                elif ma_points <= 15: ma_rating = "partially favourable"
                elif ma_points <= 20: ma_rating = "average"
                elif ma_points <= 30: ma_rating = "partially unfavourable"
                else: ma_rating = "unfavourable"
            elif revenue >= 250000000:
                ma_logger.info("Revenue Tier: >= $250M")
                ma_logger.info(f"Evaluating ma_points={ma_points:.2f} against thresholds: <=3 Very Favourable, <=6 Favourable, <=10 Partially Favourable, <=15 Average, <=20 Partially Unfavourable, >20 Unfavourable")
                if ma_points <= 3: ma_rating = "very favourable"
                elif ma_points <= 6: ma_rating = "favourable"
                elif ma_points <= 10: ma_rating = "partially favourable"
                elif ma_points <= 15: ma_rating = "average"
                elif ma_points <= 20: ma_rating = "partially unfavourable"
                else: ma_rating = "unfavourable"
            elif revenue >= 50000000:
                ma_logger.info("Revenue Tier: >= $50M")
                ma_logger.info(f"Evaluating ma_points={ma_points:.2f} against thresholds: <=2 Very Favourable, <=4 Favourable, <=7 Partially Favourable, <=10 Average, <=15 Partially Unfavourable, >15 Unfavourable")
                if ma_points <= 2: ma_rating = "very favourable"
                elif ma_points <= 4: ma_rating = "favourable"
                elif ma_points <= 7: ma_rating = "partially favourable"
                elif ma_points <= 10: ma_rating = "average"
                elif ma_points <= 15: ma_rating = "partially unfavourable"
                else: ma_rating = "unfavourable"
            else:
                ma_logger.info("Revenue Tier: < $50M")
                ma_logger.info(f"Evaluating ma_points={ma_points:.2f} against thresholds: <=1 Very Favourable, <=3 Favourable, <=5 Partially Favourable, <=7 Average, <=10 Partially Unfavourable, >10 Unfavourable")
                if ma_points <= 1: ma_rating = "very favourable"
                elif ma_points <= 3: ma_rating = "favourable"
                elif ma_points <= 5: ma_rating = "partially favourable"
                elif ma_points <= 7: ma_rating = "average"
                elif ma_points <= 10: ma_rating = "partially unfavourable"
                else: ma_rating = "unfavourable"

            modifier_scores["Mergers and Acquisitions"] = {"score": ma_points, "rating": ma_rating}
            underwriting_rationale["Mergers and Acquisitions"] = (
                f"Based on {len(acqs)} recent acquisition(s), the company's M&A activity is evaluated for integration complexity. "
                "A higher frequency and recency of acquisitions generally elevate cyber exposure."
            )
            ma_logger.info(f"Resulting Rating: {ma_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            ma_logger.error(f"Exception in Mergers and Acquisitions: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Mergers and Acquisitions' failed: {e}") from e
        ma_logger.info("END Modifier: Mergers and Acquisitions")
        ma_logger.info("========================================\n")


        # --- 2. Amount of sensitive information ---
        sens_logger = get_agent_logger("Amount of sensitive information")
        sens_logger.info("========================================")
        sens_logger.info("START Modifier: Amount of sensitive information")
        sens_logger.info("========================================")
        try:
            cust_type = str(reconciled.get("customer_type", "B2B")).upper()
            has_ecom = reconciled.get("has_ecommerce", False)
            sens_logger.info(f"Input: customer_type = {cust_type}")
            sens_logger.info(f"Input: has_ecommerce = {has_ecom}")
            sens_logger.info("Math Logic: B2C/MIX + ecommerce => partially unfavourable; B2C/MIX + no ecommerce => average; B2B + ecommerce => partially favourable; B2B + no ecommerce => favourable.")
        
            if "B2C" in cust_type or "MIX" in cust_type:
                sens_logger.info(f"Customer type '{cust_type}' indicates consumer/mixed exposure.")
                if has_ecom:
                    sens_logger.info("E-commerce is present: rating set to 'partially unfavourable'")
                    sens_rating = "partially unfavourable"
                else:
                    sens_logger.info("No e-commerce detected: rating set to 'average'")
                    sens_rating = "average"
            elif "B2B" in cust_type:
                sens_logger.info(f"Customer type '{cust_type}' indicates B2B-only exposure.")
                if has_ecom:
                    sens_logger.info("E-commerce is present: rating set to 'partially favourable'")
                    sens_rating = "partially favourable"
                else:
                    sens_logger.info("No e-commerce detected: rating set to 'favourable'")
                    sens_rating = "favourable"
            else:
                sens_logger.info(f"Unknown customer type '{cust_type}': fallback rating set to 'partially unfavourable'")
                sens_rating = "partially unfavourable"
            
            modifier_scores["Amount of sensitive information"] = {"score": 0.0, "rating": sens_rating}
            underwriting_rationale["Amount of sensitive information"] = (
                f"The company serves a {cust_type.lower()} customer base with {'an active' if has_ecom else 'no significant'} e-commerce presence. "
                "Direct consumer interactions and e-commerce platforms typically increase the volume and sensitivity of data stored."
            )
            sens_logger.info(f"Resulting Rating: {sens_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            sens_logger.error(f"Exception in Amount of sensitive information: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Amount of sensitive information' failed: {e}") from e
        sens_logger.info("END Modifier: Amount of sensitive information")
        sens_logger.info("========================================\n")


        # --- 3. Domain Encryption ---
        enc_logger = get_agent_logger("Domain Encryption")
        enc_logger.info("========================================")
        enc_logger.info("START Modifier: Domain Encryption")
        enc_logger.info("========================================")
        try:
            domains = reconciled.get("domains", [])
            total_domains = len(domains)
            enc_logger.info(f"Input: domains = {json.dumps(domains)}")
            enc_logger.info("Math Logic: Ratio of HTTPS encrypted domains. All encrypted => favourable; Some => partially favourable; None => average.")
        
            enc_count = 0
            for d in domains:
                url = d.get("url")
                encrypted = d.get("https_encrypted", False)
                if encrypted:
                    enc_count += 1
                enc_logger.info(f"Domain '{url}' check: https_encrypted={encrypted}")
            
            enc_rating = "average"
            if total_domains > 0:
                enc_logger.info(f"Encryption ratio: {enc_count}/{total_domains} domains encrypted.")
                if enc_count == total_domains:
                    enc_logger.info("All domains are encrypted: rating set to 'favourable'")
                    enc_rating = "favourable"
                elif enc_count > 0:
                    enc_logger.info("Some domains are encrypted: rating set to 'partially favourable'")
                    enc_rating = "partially favourable"
                else:
                    enc_logger.info("No domains are encrypted: rating set to 'average'")
                    enc_rating = "average"
            else:
                enc_logger.info("No domains registered: rating set to 'average'")
                enc_rating = "average"
            
            modifier_scores["Domain Encryption"] = {"score": f"{enc_count}/{total_domains}", "rating": enc_rating}
            underwriting_rationale["Domain Encryption"] = (
                f"Analysis of the company's internet footprint shows that {enc_count} out of {total_domains} identified domains are securely encrypted via HTTPS. "
                "Higher encryption ratios indicate a stronger security posture and lower risk of data interception."
            )
            enc_logger.info(f"Resulting Rating: {enc_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            enc_logger.error(f"Exception in Domain Encryption: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Domain Encryption' failed: {e}") from e
        enc_logger.info("END Modifier: Domain Encryption")
        enc_logger.info("========================================\n")


        # --- 4. Geographic Spread ---
        geo_logger = get_agent_logger("Geographic Spread")
        geo_logger.info("========================================")
        geo_logger.info("START Modifier: Geographic Spread")
        geo_logger.info("========================================")
        try:
            countries = reconciled.get("countries_of_operation", ["USA"])
            c_count = len(countries)
            continents = reconciled.get("continent_spread", ["North America"])
            cont_count = len(continents)
            usa_p = reconciled.get("usa_presence", True)
        
            geo_logger.info(f"Input: countries_of_operation = {countries} (count: {c_count})")
            geo_logger.info(f"Input: continent_spread = {continents} (count: {cont_count})")
            geo_logger.info(f"Input: usa_presence = {usa_p}")
            geo_logger.info(f"Input: revenue = {revenue}")
            geo_logger.info("Math Logic: Evaluates country count and continent spread against revenue tier thresholds.")
        
            geo_rating = "average"
            if revenue >= 1000000000:
                geo_logger.info("Revenue Tier: >= $1B")
                geo_logger.info(f"Evaluating c_count={c_count}, cont_count={cont_count} against thresholds: c_count<=10 and cont_count==1 => Favourable; c_count<=10 => Partially Favourable; else Average")
                if c_count <= 10 and cont_count == 1: 
                    geo_rating = "favourable"
                elif c_count <= 10: 
                    geo_rating = "partially favourable"
                else:
                    geo_rating = "average"
            elif revenue >= 250000000:
                geo_logger.info("Revenue Tier: >= $250M")
                geo_logger.info(f"Evaluating c_count={c_count}, cont_count={cont_count} against thresholds: c_count<=5 and cont_count==1 => Favourable; c_count<=7 => Partially Favourable; else Average")
                if c_count <= 5 and cont_count == 1: 
                    geo_rating = "favourable"
                elif c_count <= 7: 
                    geo_rating = "partially favourable"
                else:
                    geo_rating = "average"
            elif revenue >= 50000000:
                geo_logger.info("Revenue Tier: >= $50M")
                geo_logger.info(f"Evaluating c_count={c_count}, cont_count={cont_count} against thresholds: c_count<=3 and cont_count==1 => Favourable; c_count<=5 => Partially Favourable; else Average")
                if c_count <= 3 and cont_count == 1: 
                    geo_rating = "favourable"
                elif c_count <= 5: 
                    geo_rating = "partially favourable"
                else:
                    geo_rating = "average"
            else:
                geo_logger.info("Revenue Tier: < $50M")
                geo_logger.info(f"Evaluating c_count={c_count}, cont_count={cont_count} against thresholds: c_count<=2 and cont_count==1 => Favourable; c_count<=10 => Partially Favourable; else Average")
                if c_count <= 2 and cont_count == 1: 
                    geo_rating = "favourable"
                elif c_count <= 10: 
                    geo_rating = "partially favourable"
                else:
                    geo_rating = "average"
                
            modifier_scores["Geographic Spread"] = {"score": c_count, "rating": geo_rating}
            underwriting_rationale["Geographic Spread"] = (
                f"The company operates across {c_count} countries" + (", including the United States." if usa_p else ".") +
                " Broader geographic footprints, particularly in heavily regulated jurisdictions, increase compliance requirements and potential cyber liability."
            )
            geo_logger.info(f"Resulting Rating: {geo_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            geo_logger.error(f"Exception in Geographic Spread: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Geographic Spread' failed: {e}") from e
        geo_logger.info("END Modifier: Geographic Spread")
        geo_logger.info("========================================\n")


        # --- 5. Internet Footprint ---
        foot_logger = get_agent_logger("Internet footprint")
        foot_logger.info("========================================")
        foot_logger.info("START Modifier: Internet Footprint")
        foot_logger.info("========================================")
        try:
            domain_count = int(reconciled.get("internet_exposure_domains", 1))
            scale = reconciled.get("customer_base_scale", "SMB (<1k)")
        
            foot_logger.info(f"Input: internet_exposure_domains = {domain_count}")
            foot_logger.info(f"Input: customer_base_scale = {scale}")
        
            mult = 1.0
            if "Enterprise" in scale: 
                mult = 3.0
            elif "Mid-Market" in scale: 
                mult = 2.0
            
            footprint_score = domain_count * mult
            foot_logger.info(f"Resolved scale multiplier: {mult}. Computed footprint score (domain_count * multiplier) = {footprint_score}")
        
            footprint_rating = "average"
            foot_logger.info(f"Evaluating footprint_score={footprint_score} against thresholds: <=5 Favourable, <=20 Average, <=100 Partially Unfavourable, >100 Unfavourable")
            if footprint_score <= 5: 
                footprint_rating = "favourable"
            elif footprint_score <= 20: 
                footprint_rating = "average"
            elif footprint_score <= 100: 
                footprint_rating = "partially unfavourable"
            else: 
                footprint_rating = "unfavourable"
            
            modifier_scores["Internet footprint"] = {"score": footprint_score, "rating": footprint_rating}
            underwriting_rationale["Internet footprint"] = (
                f"The company's external attack surface yields a footprint score of {footprint_score}. "
                "A larger volume of publicly accessible domains and subdomains increases the potential attack surface available to threat actors."
            )
            foot_logger.info(f"Resulting Rating: {footprint_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            foot_logger.error(f"Exception in Internet Footprint: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Internet Footprint' failed: {e}") from e
        foot_logger.info("END Modifier: Internet Footprint")
        foot_logger.info("========================================\n")


        # --- 6. Nature of Services ---
        serv_logger = get_agent_logger("Nature of services")
        serv_logger.info("========================================")
        serv_logger.info("START Modifier: Nature of Services")
        serv_logger.info("========================================")
        try:
            evidence = state.get("collected_evidence", {})
        
            # Helper to convert to string
            def _to_str(val):
                if isinstance(val, list): return ", ".join(str(i) for i in val if i)
                return str(val) if val else ""

            # 1. Gather all extraction signals
            domain_findings = evidence.get("DomainScraper", {}).get("findings", {})
            wikidata_findings = evidence.get("Wikidata", {}).get("findings", {})
            wikipedia_findings = evidence.get("Wikipedia", {}).get("findings", {})

            products_str = _to_str(domain_findings.get("products_services_portfolio", []))
            industry_str = _to_str(wikidata_findings.get("industry", [])) + ", " + \
                           _to_str(wikidata_findings.get("sub_industries", [])) + ", " + \
                           _to_str(wikipedia_findings.get("industry_classification", []))
            sic_str = _to_str(reconciled.get("sic_codes", []))
            compliance_str = _to_str(domain_findings.get("compliance_mentions", [])) + ", " + _to_str(reconciled.get("customer_type", ""))

            serv_logger.info(f"Gathered text signals:")
            serv_logger.info(f"- Products/Services Portfolio: '{products_str}'")
            serv_logger.info(f"- Industry Classifications: '{industry_str}'")
            serv_logger.info(f"- SIC Codes: '{sic_str}'")
            serv_logger.info(f"- Compliance & Customer Type: '{compliance_str}'")

            # 2. Reference keywords mapping function
            high_risk_kw = ["healthcare", "hospital", "patient", "clinical", "insurance", "banking", "financial services", "payment", "lending", "fintech"]
            medium_risk_kw = ["cloud", "saas", "software", "enterprise software", "ai", "cybersecurity", "data platform", "manufacturing", "logistics", "education", "retail"]
            low_risk_kw = ["low digital exposure", "simple services"]

            def score_text_logged(text: str, category_name: str):
                t = text.lower()
                if not t.strip() or t.strip() == ", ,": 
                    serv_logger.info(f"Category '{category_name}' text is empty. Skipping.")
                    return None, None
                for kw in high_risk_kw:
                    if kw in t: 
                        serv_logger.info(f"Category '{category_name}' matched High Risk keyword: '{kw}' (3.0 pts)")
                        return 3.0, kw
                for kw in medium_risk_kw:
                    if kw in t: 
                        serv_logger.info(f"Category '{category_name}' matched Medium Risk keyword: '{kw}' (2.0 pts)")
                        return 2.0, kw
                for kw in low_risk_kw:
                    if kw in t: 
                        serv_logger.info(f"Category '{category_name}' matched Low Risk keyword: '{kw}' (1.0 pts)")
                        return 1.0, kw
                serv_logger.info(f"Category '{category_name}' text has no matching risk keywords.")
                return None, None

            # 3. Evaluate each signal category
            p_score, p_kw = score_text_logged(products_str, "Products")
            i_score, i_kw = score_text_logged(industry_str, "Industry")
            s_score, s_kw = score_text_logged(sic_str, "SIC")
            c_score, c_kw = score_text_logged(compliance_str, "Compliance/Customer")

            # 4. Compute weighted decision
            weights = {"p": 0.40, "i": 0.30, "s": 0.20, "c": 0.10}
            total_score = 0.0
            total_weight = 0.0

            if p_score is not None:
                total_score += p_score * weights["p"]
                total_weight += weights["p"]
                serv_logger.info(f"Weighted Products: score={p_score} * weight={weights['p']} = {p_score * weights['p']:.2f}")
            if i_score is not None:
                total_score += i_score * weights["i"]
                total_weight += weights["i"]
                serv_logger.info(f"Weighted Industry: score={i_score} * weight={weights['i']} = {i_score * weights['i']:.2f}")
            if s_score is not None:
                total_score += s_score * weights["s"]
                total_weight += weights["s"]
                serv_logger.info(f"Weighted SIC: score={s_score} * weight={weights['s']} = {s_score * weights['s']:.2f}")
            if c_score is not None:
                total_score += c_score * weights["c"]
                total_weight += weights["c"]
                serv_logger.info(f"Weighted Compliance: score={c_score} * weight={weights['c']} = {c_score * weights['c']:.2f}")

            appetite = None
            if total_weight > 0:
                final_score = total_score / total_weight
                serv_logger.info(f"Normalized Weighted Score: {total_score:.4f} / {total_weight:.2f} = {final_score:.4f}")
            
                serv_logger.info("Evaluating final_score against thresholds: >=2.5 High Risk, >=1.5 Medium Risk, else Low Risk")
                if final_score >= 2.5:
                    appetite = "high_risk"
                elif final_score >= 1.5:
                    appetite = "medium_risk"
                else:
                    appetite = "low_risk"
            
                # Generate Explainability Rationale
                lines = []
                if p_kw: lines.append(f"Detected products: {p_kw}")
                if i_kw: lines.append(f"Detected industries: {i_kw}")
                if s_kw or c_kw:
                    other_kw = [k for k in [s_kw, c_kw] if k]
                    if other_kw: lines.append(f"Other signals: {', '.join(other_kw)}")
            
                lines.append(f"Weighted Score: {final_score:.2f}")
                lines.append(f"Assigned {appetite} according to reference table.")
                rationale_text = " | ".join(lines)
            else:
                appetite = reconciled.get("services_appetite", "medium_risk")
                rationale_text = f"Nature of Services evaluated from fallback. Mapped to {appetite}."
                serv_logger.info(f"No text keywords matched. Falling back to default services_appetite: '{appetite}'")

            if "low_risk" in appetite: 
                services_rating = "favourable"
            elif "high_risk" in appetite: 
                services_rating = "partially unfavourable"
            else: 
                services_rating = "average"
            
            modifier_scores["Nature of services"] = {"score": appetite, "rating": services_rating}
            underwriting_rationale["Nature of services"] = rationale_text
            serv_logger.info(f"Resulting Rating: {services_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            serv_logger.error(f"Exception in Nature of Services: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Nature of Services' failed: {e}") from e
        serv_logger.info("END Modifier: Nature of Services")
        serv_logger.info("========================================\n")


        # --- 7. Organizational Complexity ---
        org_logger = get_agent_logger("Organizational Complexity")
        org_logger.info("========================================")
        org_logger.info("START Modifier: Organizational Complexity")
        org_logger.info("========================================")
        try:
            subs_count = len(reconciled.get("subsidiaries", []))
            org_logger.info(f"Input: subsidiaries count = {subs_count}")
            org_logger.info(f"Input: revenue = {revenue}")
            org_logger.info("Math Logic: Subsidiary count evaluated against revenue tier thresholds.")
        
            org_rating = "average"
            if revenue >= 1000000000:
                org_logger.info("Revenue Tier: >= $1B")
                org_logger.info(f"Evaluating subs_count={subs_count} against thresholds: <10 Very Favourable, <=20 Favourable, <=50 Average, >50 Partially Unfavourable")
                if subs_count < 10: org_rating = "very favourable"
                elif subs_count <= 20: org_rating = "favourable"
                elif subs_count <= 50: org_rating = "average"
                else: org_rating = "partially unfavourable"
            elif revenue >= 250000000:
                org_logger.info("Revenue Tier: >= $250M")
                org_logger.info(f"Evaluating subs_count={subs_count} against thresholds: <7 Very Favourable, <=15 Favourable, <=30 Average, >30 Partially Unfavourable")
                if subs_count < 7: org_rating = "very favourable"
                elif subs_count <= 15: org_rating = "favourable"
                elif subs_count <= 30: org_rating = "average"
                else: org_rating = "partially unfavourable"
            elif revenue >= 50000000:
                org_logger.info("Revenue Tier: >= $50M")
                org_logger.info(f"Evaluating subs_count={subs_count} against thresholds: <5 Very Favourable, <=10 Favourable, <=15 Average, >15 Partially Unfavourable")
                if subs_count < 5: org_rating = "very favourable"
                elif subs_count <= 10: org_rating = "favourable"
                elif subs_count <= 15: org_rating = "average"
                else: org_rating = "partially unfavourable"
            else:
                org_logger.info("Revenue Tier: < $50M")
                org_logger.info(f"Evaluating subs_count={subs_count} against thresholds: <3 Very Favourable, <=6 Favourable, <=10 Average, >10 Partially Unfavourable")
                if subs_count < 3: org_rating = "very favourable"
                elif subs_count <= 6: org_rating = "favourable"
                elif subs_count <= 10: org_rating = "average"
                else: org_rating = "partially unfavourable"
            
            modifier_scores["Organizational Complexity"] = {"score": subs_count, "rating": org_rating}
            underwriting_rationale["Organizational Complexity"] = (
                f"The organization encompasses {subs_count} identified subsidiaries. "
                "A higher number of corporate entities often correlates with decentralized IT environments and increased structural complexity, elevating cyber risk."
            )
            org_logger.info(f"Resulting Rating: {org_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            org_logger.error(f"Exception in Organizational Complexity: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Organizational Complexity' failed: {e}") from e
        org_logger.info("END Modifier: Organizational Complexity")
        org_logger.info("========================================\n")


        # --- 8. Privacy Regulation ---
        priv_logger = get_agent_logger("Privacy Regulation")
        priv_logger.info("========================================")
        priv_logger.info("START Modifier: Privacy Regulation")
        priv_logger.info("========================================")
        try:
            has_policy = reconciled.get("privacy_policy_published", False)
            mentions = reconciled.get("compliance_mentions", [])
            m_count = len(mentions)
        
            priv_logger.info(f"Input: privacy_policy_published = {has_policy}")
            priv_logger.info(f"Input: compliance_mentions = {mentions} (count: {m_count})")
            priv_logger.info("Math Logic: Policy published and compliance count >= 2 => favourable; count == 1 => partially favourable; no policy => partially unfavourable.")
        
            priv_rating = "average"
            if has_policy:
                priv_logger.info("Privacy policy is published. Checking compliance mentions count:")
                if m_count >= 2: 
                    priv_logger.info("Compliance count >= 2: rating set to 'favourable'")
                    priv_rating = "favourable"
                elif m_count == 1: 
                    priv_logger.info("Compliance count == 1: rating set to 'partially favourable'")
                    priv_rating = "partially favourable"
                else:
                    priv_logger.info("Compliance count == 0: rating set to 'average'")
                    priv_rating = "average"
            else:
                priv_logger.info("Privacy policy is NOT published: rating set to 'partially unfavourable'")
                priv_rating = "partially unfavourable"
            
            modifier_scores["Privacy Regulation"] = {"score": m_count, "rating": priv_rating}
            underwriting_rationale["Privacy Regulation"] = (
                f"{'A published privacy policy was identified' if has_policy else 'No distinct privacy policy was located'}, alongside {m_count} compliance framework mentions. "
                "Adherence to standardized privacy regulations generally demonstrates mature data governance and reduces cyber liability."
            )
            priv_logger.info(f"Resulting Rating: {priv_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            priv_logger.error(f"Exception in Privacy Regulation: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Privacy Regulation' failed: {e}") from e
        priv_logger.info("END Modifier: Privacy Regulation")
        priv_logger.info("========================================\n")


        # --- 9. Seasonality of Sales ---
        seas_logger = get_agent_logger("Seasonality of sales")
        seas_logger.info("========================================")
        seas_logger.info("START Modifier: Seasonality of Sales")
        seas_logger.info("========================================")
        try:
            q_rev = reconciled.get("quarterly_revenue", [])
            sic_codes = reconciled.get("sic_codes", ["7372"])
            sic = sic_codes[0] if sic_codes else "7372"
            cv = None
            season_rating = "average"
        
            seas_logger.info(f"Input: quarterly_revenue = {q_rev}")
            seas_logger.info(f"Input: sic_codes = {sic_codes}")
            seas_logger.info("Math Logic: If quarterly revenue count >= 4, CV = std/mean. CV < 0.1 => favourable, CV <= 0.25 => average, else partially unfavourable. Else fallback to SIC-based rule.")
        
            if len(q_rev) >= 4:
                mean = np.mean(q_rev)
                std = np.std(q_rev)
                seas_logger.info(f"Quarterly revenue data available. Calculated mean = {mean:.2f}, standard deviation = {std:.2f}")
                if mean > 0:
                    cv = std / mean
                    seas_logger.info(f"Computed Coefficient of Variation (CV) = {cv:.4f}")
                    seas_logger.info(f"Evaluating CV against thresholds: <0.1 Favourable, <=0.25 Average, else Partially Unfavourable")
                    if cv < 0.1: 
                        season_rating = "favourable"
                    elif cv <= 0.25: 
                        season_rating = "average"
                    else: 
                        season_rating = "partially unfavourable"
                    underwriting_rationale["Seasonality of sales"] = (
                    f"Revenue analysis yields a variance (CV) of {cv:.3f}. High seasonality implies that operational outages during peak periods would have a disproportionately severe financial impact."
                )
                else:
                    seas_logger.info("Mean is zero or negative. Fallback to average seasonality.")
                    underwriting_rationale["Seasonality of sales"] = "Insufficient quarterly revenue variance data; evaluated at an average seasonality risk."
            else:
                seas_logger.info(f"Quarterly revenue data count is {len(q_rev)} (fewer than 4). Using SIC fallback code: '{sic}'")
                if sic == "5311":
                    seas_logger.info("SIC is 5311 (Department Stores): high seasonality expected, rating set to 'partially unfavourable'")
                    season_rating = "partially unfavourable"
                    underwriting_rationale["Seasonality of sales"] = "Based on retail industry classification, the company is expected to experience high sales seasonality, heightening business interruption risks."
                else:
                    seas_logger.info(f"SIC '{sic}' is not 5311: average seasonality expected, rating set to 'average'")
                    season_rating = "average"
                    underwriting_rationale["Seasonality of sales"] = "Based on the industry classification, the company is evaluated at a standard seasonality risk, indicating moderate exposure to targeted outages."
                
            modifier_scores["Seasonality of sales"] = {"score": cv if cv is not None else 0.0, "rating": season_rating}
            seas_logger.info(f"Resulting Rating: {season_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            seas_logger.error(f"Exception in Seasonality of Sales: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Seasonality of Sales' failed: {e}") from e
        seas_logger.info("END Modifier: Seasonality of Sales")
        seas_logger.info("========================================\n")


        # --- 10. Volatility/Recovery in Sales ---
        vol_logger = get_agent_logger("Volatility/Recovery in Sales")
        vol_logger.info("========================================")
        vol_logger.info("START Modifier: Volatility/Recovery in Sales")
        vol_logger.info("========================================")
        try:
            de = reconciled.get("digital_exposure", 3)
            ds = reconciled.get("disruption_speed", 3)
            rc = reconciled.get("recovery_complexity", 3)
        
            vol_logger.info(f"Input: digital_exposure = {de}")
            vol_logger.info(f"Input: disruption_speed = {ds}")
            vol_logger.info(f"Input: recovery_complexity = {rc}")
        
            vol_avg = (de + ds + rc) / 3.0
            vol_logger.info(f"Computed average index (exposure + speed + complexity) / 3 = {vol_avg:.4f}")
        
            vol_rating = "average"
            vol_logger.info(f"Evaluating vol_avg={vol_avg:.4f} against thresholds: <=2.0 Favourable, <=3.5 Average, else Partially Unfavourable")
            if vol_avg <= 2.0: 
                vol_rating = "favourable"
            elif vol_avg <= 3.5: 
                vol_rating = "average"
            else: 
                vol_rating = "partially unfavourable"
            
            modifier_scores["Volatility/Recovery in Sales"] = {"score": vol_avg, "rating": vol_rating}
            underwriting_rationale["Volatility/Recovery in Sales"] = (
                f"The averaged recovery risk index is {vol_avg:.2f}. "
                "Higher volatility indicates greater difficulty and extended timelines for business recovery following a cyber event."
            )
            vol_logger.info(f"Resulting Rating: {vol_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            vol_logger.error(f"Exception in Volatility/Recovery in Sales: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Volatility/Recovery in Sales' failed: {e}") from e
        vol_logger.info("END Modifier: Volatility/Recovery in Sales")
        vol_logger.info("========================================\n")


        # --- 11. Applicability of Privacy Regulation ---
        appl_logger = get_agent_logger("Applicability of Privacy Regulation")
        appl_logger.info("========================================")
        appl_logger.info("START Modifier: Applicability of Privacy Regulation")
        appl_logger.info("========================================")
        try:
            sic_codes = reconciled.get("sic_codes") or []
            sic = str(sic_codes[0]) if sic_codes else ""
            cust_type = str(reconciled.get("customer_type", "B2B")).upper()
            has_ecom = bool(reconciled.get("has_ecommerce", False))

            is_high_risk_industry = sic.startswith(("737", "80", "6"))
            is_strict = (
                is_high_risk_industry
                or cust_type in ["B2C", "MIX"]
                or has_ecom
            )

            appl_logger.info(f"Input: sic_codes = {sic_codes} (using primary SIC: '{sic}')")
            appl_logger.info(f"Input: customer_type = {cust_type}")
            appl_logger.info(f"Input: has_ecommerce = {has_ecom}")

            # High privacy applicability industries: IT=737x, Healthcare=80xx, Finance=6xxx
            appl_logger.info(f"Checking high risk industry status (SIC prefix 737, 80, or 6): {is_high_risk_industry}")

            appl_logger.info("Math Logic: Checks if industry is not high risk and customer type is B2B-only and has no ecommerce => favourable; B2B-only with ecommerce => partially favourable; else average.")
            if not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type and not has_ecom:
                appl_logger.info("Industry not high risk, B2B-only, no e-commerce: rating set to 'favourable'")
                appl_rating = "favourable"
            elif not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type:
                appl_logger.info("Industry not high risk, B2B-only, has e-commerce: rating set to 'partially favourable'")
                appl_rating = "partially favourable"
            else:
                appl_logger.info("High risk industry, consumer/mixed customer type, or other configuration: rating set to 'average'")
                appl_rating = "average"

            modifier_scores["Applicability of Privacy Regulation"] = {"score": 0.0, "rating": appl_rating}
            underwriting_rationale["Applicability of Privacy Regulation"] = (
                "The company's primary industry sector involves strict privacy regulations (e.g., healthcare or financial data), significantly increasing regulatory liability in the event of a breach."
                if is_strict else
                "The company's primary industry sector carries standard regulatory requirements, presenting typical liability in the event of a data breach."
            )
            appl_logger.info(f"Resulting Rating: {appl_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            appl_logger.error(f"Exception in Applicability of Privacy Regulation: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Applicability of Privacy Regulation' failed: {e}") from e
        appl_logger.info("END Modifier: Applicability of Privacy Regulation")
        appl_logger.info("========================================\n")


        # --- 12. B2C End Products ---
        b2c_logger = get_agent_logger("B2C End Products")
        b2c_logger.info("========================================")
        b2c_logger.info("START Modifier: B2C End Products")
        b2c_logger.info("========================================")
        try:
            b2c_logger.info(f"Input: customer_type = {cust_type}")
            b2c_logger.info("Math Logic: B2C/B2B mix or MIX => partially favourable; pure B2C or CONSUMER or SMB => favourable; else average.")
        
            if ("B2C" in cust_type and "B2B" in cust_type) or "MIX" in cust_type:
                b2c_logger.info("Customer type contains mixed B2B and B2C / MIX: rating set to 'partially favourable'")
                b2c_rating = "partially favourable"
            elif "B2C" in cust_type or "CONSUMER" in cust_type or "SMB" in cust_type:
                b2c_logger.info("Customer type is B2C / Consumer / SMB: rating set to 'favourable'")
                b2c_rating = "favourable"
            else:
                b2c_logger.info("Customer type is pure B2B / other: rating set to 'average'")
                b2c_rating = "average"
            
            modifier_scores["B2C End Products"] = {"score": 0.0, "rating": b2c_rating}
            underwriting_rationale["B2C End Products"] = (
                f"The company primarily serves a {cust_type.lower()} market. "
                "Direct-to-consumer businesses generally collect and retain more granular personally identifiable information (PII), increasing the severity of a potential compromise."
            )
            b2c_logger.info(f"Resulting Rating: {b2c_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            b2c_logger.error(f"Exception in B2C End Products: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'B2C End Products' failed: {e}") from e
        b2c_logger.info("END Modifier: B2C End Products")
        b2c_logger.info("========================================\n")


        # --- 13. Years in business ---
        yib_logger = get_agent_logger("Years in business")
        yib_logger.info("========================================")
        yib_logger.info("START Modifier: Years in business")
        yib_logger.info("========================================")
        try:
            founding_year = reconciled.get("founding_year")
            current_year = datetime.now().year
            yib = None
            yib_rating = "average"
        
            yib_logger.info(f"Input: founding_year = {founding_year}")
            yib_logger.info(f"Input: current_year = {current_year}")
            yib_logger.info(f"Input: revenue = {revenue}")
            yib_logger.info("Math Logic: Years since founding year evaluated against revenue tier thresholds.")
        
            if founding_year is not None:
                try:
                    yib = int(current_year) - int(founding_year)
                    yib_logger.info(f"Calculated Years in Business: {current_year} - {founding_year} = {yib}")
                except Exception as e:
                    yib_logger.warning(f"Could not convert founding year '{founding_year}' to integer: {e}")
                    pass

            if yib is not None and yib >= 0:
                if revenue >= 1000000000:
                    yib_logger.info("Revenue Tier: >= $1B")
                    yib_logger.info(f"Evaluating yib={yib} against thresholds: >30 Very Favourable, >=20 Favourable, >=10 Partially Favourable, >=5 Average, else Unfavourable")
                    if yib > 30: yib_rating = "very favourable"
                    elif yib >= 20: yib_rating = "favourable"
                    elif yib >= 10: yib_rating = "partially favourable"
                    elif yib >= 5: yib_rating = "average"
                    else: yib_rating = "unfavourable"
                elif revenue >= 250000000:
                    yib_logger.info("Revenue Tier: >= $250M")
                    yib_logger.info(f"Evaluating yib={yib} against thresholds: >20 Very Favourable, >=10 Favourable, >=5 Partially Favourable, >=3 Average, else Unfavourable")
                    if yib > 20: yib_rating = "very favourable"
                    elif yib >= 10: yib_rating = "favourable"
                    elif yib >= 5: yib_rating = "partially favourable"
                    elif yib >= 3: yib_rating = "average"
                    else: yib_rating = "unfavourable"
                elif revenue >= 50000000:
                    yib_logger.info("Revenue Tier: >= $50M")
                    yib_logger.info(f"Evaluating yib={yib} against thresholds: >10 Very Favourable, >=7 Favourable, >=4 Partially Favourable, >=2 Average, else Unfavourable")
                    if yib > 10: yib_rating = "very favourable"
                    elif yib >= 7: yib_rating = "favourable"
                    elif yib >= 4: yib_rating = "partially favourable"
                    elif yib >= 2: yib_rating = "average"
                    else: yib_rating = "unfavourable"
                else:
                    yib_logger.info("Revenue Tier: < $50M")
                    yib_logger.info(f"Evaluating yib={yib} against thresholds: >7 Very Favourable, >=5 Favourable, >=3 Partially Favourable, >=1 Average, else Unfavourable")
                    if yib > 7: yib_rating = "very favourable"
                    elif yib >= 5: yib_rating = "favourable"
                    elif yib >= 3: yib_rating = "partially favourable"
                    elif yib >= 1: yib_rating = "average"
                    else: yib_rating = "unfavourable"
            else:
                yib_logger.info("Founding year missing or invalid. Rating set to 'average'")
                yib_rating = "average"

            modifier_scores["Years in business"] = {"score": yib if yib is not None else 0.0, "rating": yib_rating}
            underwriting_rationale["Years in business"] = (
                f"The company has been operating for {yib if yib is not None else 'an undetermined number of'} years. "
                "Established organizations typically exhibit more mature cybersecurity practices and resilience compared to newer ventures."
            )
            yib_logger.info(f"Resulting Rating: {yib_rating}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            yib_logger.error(f"Exception in Years in business: {e}\n{tb}")
            raise RuntimeError(f"Modifier 'Years in business' failed: {e}") from e
        yib_logger.info("END Modifier: Years in business")
        yib_logger.info("========================================\n")

        # Aggregate overall rating
        underwriter_logger.info("START Modifier Aggregation")
        numeric_scores = []
        for name, details in modifier_scores.items():
            rat = details["rating"].lower()
            score_val = RATING_SCORES.get(rat, 4.0)
            numeric_scores.append(score_val)
            # Use LLM rationale if available, otherwise fallback to mathematical rationale
            if name in assessment.get("underwriting_rationale", {}) and name != "Nature of services":
                raw_rat = assessment["underwriting_rationale"][name]
                # Strip trailing incorrect rating words from LLM response
                cleaned = re.sub(r'(?i)[,\s]*(very favourable|partially favourable|favourable|average|neutral|partially unfavourable|unfavourable)(?:\s*risk)?\.?$', '', raw_rat)
                underwriting_rationale[name] = f"{cleaned}, {rat}."

        underwriter_logger.info("START Verdict Generation")
        avg_score = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 4.0
        if avg_score < 2.0: risk_category = "Very Favourable"
        elif avg_score < 3.0: risk_category = "Favourable"
        elif avg_score < 4.0: risk_category = "Partially Favourable"
        elif avg_score < 4.5: risk_category = "Average"
        elif avg_score < 5.5: risk_category = "Partially Unfavourable"
        else: risk_category = "Unfavourable"

        # Confidence score based on fact check consensus accuracy
        if state.get("entity_status") == "Mismatch":
            confidence_score = 0.0
            confidence_band = "Low"
        else:
            confidence_score = float(round(accuracy * 100.0, 1))
            if accuracy >= 0.8: confidence_band = "High"
            elif accuracy >= 0.5: confidence_band = "Medium"
            else: confidence_band = "Low"

        # Human Escalation Logic
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
