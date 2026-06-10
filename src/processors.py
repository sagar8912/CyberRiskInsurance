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

        # Subsidiaries Priority
        for src in sources_order:
            val = get_val(src, "subsidiaries")
            if val:
                merged["subsidiaries"] = val
                break

        # Acquisitions Priority
        for src in sources_order:
            val = get_val(src, "acquisitions")
            if val:
                merged["acquisitions"] = val
                break

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
        for src in sources_order:
            val = get_val(src, "countries_of_operation")
            if val:
                merged["countries_of_operation"] = val
                break
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

        # Domains / HTTPS
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
                merged[k] = v

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

        logs.append("Coordinator: Merge and reconciliation completed.")
        return {
            "reconciled_profile": merged,
            "conflict_flags": conflict_flags,
            "audit_logs": state.get("audit_logs", []) + logs
        }

class FactCheckerAgent(BaseFactCheckerAgent):
    async def verify(self, state: Dict[str, Any]) -> Dict[str, Any]:
        reconciled = state.get("reconciled_profile", {})
        reports = state.get("reports", {})
        logs = []
        logs.append("Fact Checker: Starting fact corroboration and consensus analysis...")

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
        logs.append(f"Fact Checker Verdict: Accuracy Score = {accuracy_score:.2f} ({verified_count}/{total_claims} corroborated claims)")

        return {
            "claims_verification": claims_verif,
            "accuracy_score": accuracy_score,
            "audit_logs": state.get("audit_logs", []) + logs
        }

class UnderwriterAgent(BaseUnderwriterAgent):
    def underwrite(self, state: Dict[str, Any]) -> Dict[str, Any]:
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

        # M&A
        acqs = reconciled.get("acquisitions", [])
        ma_points = 0.0
        for acq in acqs:
            deal_type = str(acq.get("deal_type", "minor acquisition")).lower()
            pts = 1.0
            if "trans" in deal_type:
                pts = 4.0
            elif "material" in deal_type:
                pts = 3.0
            elif "minor" in deal_type:
                pts = 2.0
            
            recency = acq.get("recency_years", 5.0)
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

            ma_points += (pts * mult)

        ma_rating = "average"
        if revenue >= 1000000000:
            if ma_points <= 5: ma_rating = "very favourable"
            elif ma_points <= 10: ma_rating = "favourable"
            elif ma_points <= 15: ma_rating = "partially favourable"
            elif ma_points <= 20: ma_rating = "average"
            elif ma_points <= 30: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        elif revenue >= 250000000:
            if ma_points <= 3: ma_rating = "very favourable"
            elif ma_points <= 6: ma_rating = "favourable"
            elif ma_points <= 10: ma_rating = "partially favourable"
            elif ma_points <= 15: ma_rating = "average"
            elif ma_points <= 20: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        elif revenue >= 50000000:
            if ma_points <= 2: ma_rating = "very favourable"
            elif ma_points <= 4: ma_rating = "favourable"
            elif ma_points <= 7: ma_rating = "partially favourable"
            elif ma_points <= 10: ma_rating = "average"
            elif ma_points <= 15: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        else:
            if ma_points <= 1: ma_rating = "very favourable"
            elif ma_points <= 3: ma_rating = "favourable"
            elif ma_points <= 5: ma_rating = "partially favourable"
            elif ma_points <= 7: ma_rating = "average"
            elif ma_points <= 10: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"

        modifier_scores["Mergers and Acquisitions"] = {"score": ma_points, "rating": ma_rating}
        underwriting_rationale["Mergers and Acquisitions"] = f"M&A score calculated at {ma_points:.1f} across {len(acqs)} acquisitions."

        # Sensitive Info
        cust_type = str(reconciled.get("customer_type", "B2B")).upper()
        has_ecom = reconciled.get("has_ecommerce", False)
        if "B2C" in cust_type:
            if has_ecom:
                sens_rating = "partially unfavourable"
            else:
                sens_rating = "average"
        elif "B2B" in cust_type:
            if has_ecom:
                sens_rating = "partially favourable"
            else:
                sens_rating = "favourable"
        else:
            sens_rating = "partially unfavourable"
        modifier_scores["Amount of sensitive information"] = {"score": 0.0, "rating": sens_rating}
        underwriting_rationale["Amount of sensitive information"] = f"Customer type: {cust_type}, E-commerce presence: {has_ecom}."

        # Domain Encryption
        domains = reconciled.get("domains", [])
        total_domains = len(domains)
        enc_count = sum(1 for d in domains if d.get("https_encrypted", False))
        enc_rating = "average"
        if total_domains > 0:
            if enc_count == total_domains:
                enc_rating = "favourable"
            elif enc_count > 0:
                enc_rating = "partially favourable"
            else:
                enc_rating = "average"
        modifier_scores["Domain Encryption"] = {"score": f"{enc_count}/{total_domains}", "rating": enc_rating}
        underwriting_rationale["Domain Encryption"] = f"HTTPS Encryption ratio: {enc_count} of {total_domains} domains encrypted."

        # Geographic Spread
        countries = reconciled.get("countries_of_operation", ["USA"])
        c_count = len(countries)
        cont_count = len(reconciled.get("continent_spread", ["North America"]))
        usa_p = reconciled.get("usa_presence", True)
        geo_rating = "average"
        if revenue >= 1000000000:
            if c_count <= 10 and cont_count == 1: geo_rating = "favourable"
            elif c_count <= 10: geo_rating = "partially favourable"
        elif revenue >= 250000000:
            if c_count <= 5 and cont_count == 1: geo_rating = "favourable"
            elif c_count <= 7: geo_rating = "partially favourable"
        elif revenue >= 50000000:
            if c_count <= 3 and cont_count == 1: geo_rating = "favourable"
            elif c_count <= 5: geo_rating = "partially favourable"
        else:
            if c_count <= 2 and cont_count == 1: geo_rating = "favourable"
            elif c_count <= 10: geo_rating = "partially favourable"
        modifier_scores["Geographic Spread"] = {"score": c_count, "rating": geo_rating}
        underwriting_rationale["Geographic Spread"] = f"Operates in {c_count} countries. USA presence: {usa_p}."

        # Internet Footprint
        domain_count = int(reconciled.get("internet_exposure_domains", 1))
        scale = reconciled.get("customer_base_scale", "SMB (<1k)")
        mult = 1.0
        if "Enterprise" in scale: mult = 3.0
        elif "Mid-Market" in scale: mult = 2.0
        footprint_score = domain_count * mult
        footprint_rating = "average"
        if footprint_score <= 5: footprint_rating = "favourable"
        elif footprint_score <= 20: footprint_rating = "average"
        elif footprint_score <= 100: footprint_rating = "partially unfavourable"
        else: footprint_rating = "unfavourable"
        modifier_scores["Internet footprint"] = {"score": footprint_score, "rating": footprint_rating}
        underwriting_rationale["Internet footprint"] = f"Footprint score: {footprint_score} based on scale multiplier."

        # Nature of services
        appetite = reconciled.get("services_appetite", "medium_risk")
        services_rating = "average"
        if "low_risk" in appetite: services_rating = "favourable"
        elif "high_risk" in appetite: services_rating = "unfavourable"
        modifier_scores["Nature of services"] = {"score": appetite, "rating": services_rating}
        underwriting_rationale["Nature of services"] = f"Cyber industry appetite is '{appetite}'."

        # Org Complexity
        subs_count = len(reconciled.get("subsidiaries", []))
        org_rating = "average"
        if revenue >= 1000000000:
            if subs_count < 10: org_rating = "very favourable"
            elif subs_count <= 20: org_rating = "favourable"
            elif subs_count <= 50: org_rating = "average"
            else: org_rating = "partially unfavourable"
        elif revenue >= 250000000:
            if subs_count < 7: org_rating = "very favourable"
            elif subs_count <= 15: org_rating = "favourable"
            elif subs_count <= 30: org_rating = "average"
            else: org_rating = "partially unfavourable"
        elif revenue >= 50000000:
            if subs_count < 5: org_rating = "very favourable"
            elif subs_count <= 10: org_rating = "favourable"
            elif subs_count <= 15: org_rating = "average"
            else: org_rating = "partially unfavourable"
        else:
            if subs_count < 3: org_rating = "very favourable"
            elif subs_count <= 6: org_rating = "favourable"
            elif subs_count <= 10: org_rating = "average"
            else: org_rating = "partially unfavourable"
        modifier_scores["Organizational Complexity"] = {"score": subs_count, "rating": org_rating}
        underwriting_rationale["Organizational Complexity"] = f"Total subsidiaries: {subs_count} evaluated against revenue tier."

        # Privacy Regulation
        has_policy = reconciled.get("privacy_policy_published", False)
        mentions = reconciled.get("compliance_mentions", [])
        m_count = len(mentions)
        priv_rating = "average"
        if has_policy:
            if m_count >= 2: priv_rating = "favourable"
            elif m_count == 1: priv_rating = "partially favourable"
        else:
            priv_rating = "partially unfavourable"
        modifier_scores["Privacy Regulation"] = {"score": m_count, "rating": priv_rating}
        underwriting_rationale["Privacy Regulation"] = f"Privacy Policy published: {has_policy}, compliance count: {m_count}."

        # Seasonality of Sales
        q_rev = reconciled.get("quarterly_revenue", [])
        sic_codes = reconciled.get("sic_codes", ["7372"])
        sic = sic_codes[0] if sic_codes else "7372"
        cv = None
        season_rating = "average"
        if len(q_rev) >= 4:
            mean = np.mean(q_rev)
            std = np.std(q_rev)
            if mean > 0:
                cv = std / mean
                if cv < 0.1: season_rating = "favourable"
                elif cv <= 0.25: season_rating = "average"
                else: season_rating = "partially unfavourable"
            underwriting_rationale["Seasonality of sales"] = f"Sales CV: {cv:.3f} calculated from quarterly revenues."
        else:
            if sic == "5311":
                season_rating = "partially unfavourable"
                underwriting_rationale["Seasonality of sales"] = "Fallback to Retail SIC: high seasonality expected."
            else:
                season_rating = "average"
                underwriting_rationale["Seasonality of sales"] = "Fallback to services SIC: average seasonality expected."
        modifier_scores["Seasonality of sales"] = {"score": cv if cv is not None else 0.0, "rating": season_rating}

        # Volatility / Recovery in Sales
        de = reconciled.get("digital_exposure", 3)
        ds = reconciled.get("disruption_speed", 3)
        rc = reconciled.get("recovery_complexity", 3)
        vol_avg = (de + ds + rc) / 3.0
        vol_rating = "average"
        if vol_avg <= 2.0: vol_rating = "favourable"
        elif vol_avg <= 3.5: vol_rating = "average"
        else: vol_rating = "partially unfavourable"
        modifier_scores["Volatility/Recovery in Sales"] = {"score": vol_avg, "rating": vol_rating}
        underwriting_rationale["Volatility/Recovery in Sales"] = f"Averaged risk index: {vol_avg:.2f}."

        # Applicability of Privacy Regulation (Modifier 12)
        sic_codes = reconciled.get("sic_codes", ["7372"])
        sic = str(sic_codes[0]) if sic_codes else "7372"
        cust_type = str(reconciled.get("customer_type", "B2B")).upper()
        has_ecom = reconciled.get("has_ecommerce", False)

        # High privacy applicability industries: IT=737x, Healthcare=80xx, Finance=6xxx
        is_high_risk_industry = sic.startswith("737") or sic.startswith("80") or sic.startswith("6")

        if not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type and not has_ecom:
            appl_rating = "favourable"
        elif not is_high_risk_industry and "B2B" in cust_type and "B2C" not in cust_type:
            appl_rating = "partially favourable"
        else:
            appl_rating = "average"

        modifier_scores["Applicability of Privacy Regulation"] = {"score": 0.0, "rating": appl_rating}
        underwriting_rationale["Applicability of Privacy Regulation"] = (
            f"Industry SIC {sic}, customer type {cust_type}, and ecommerce={has_ecom} evaluated for privacy regulation applicability."
        )

        # B2C End Products
        if ("B2C" in cust_type and "B2B" in cust_type) or "MIX" in cust_type:
            b2c_rating = "partially favourable"
        elif "B2C" in cust_type or "CONSUMER" in cust_type or "SMB" in cust_type:
            b2c_rating = "favourable"
        else:
            b2c_rating = "average"
        modifier_scores["B2C End Products"] = {"score": 0.0, "rating": b2c_rating}
        underwriting_rationale["B2C End Products"] = f"Target customer category is {cust_type}."

        # Years in business (Modifier 13)
        founding_year = reconciled.get("founding_year")
        current_year = datetime.now().year
        yib = None
        yib_rating = "average"
        
        if founding_year is not None:
            try:
                yib = int(current_year) - int(founding_year)
            except Exception:
                pass

        if yib is not None and yib >= 0:
            if revenue >= 1000000000:
                if yib > 30: yib_rating = "very favourable"
                elif yib >= 20: yib_rating = "favourable"
                elif yib >= 10: yib_rating = "partially favourable"
                elif yib >= 5: yib_rating = "average"
                else: yib_rating = "unfavourable"
            elif revenue >= 250000000:
                if yib > 20: yib_rating = "very favourable"
                elif yib >= 10: yib_rating = "favourable"
                elif yib >= 5: yib_rating = "partially favourable"
                elif yib >= 3: yib_rating = "average"
                else: yib_rating = "unfavourable"
            elif revenue >= 50000000:
                if yib > 10: yib_rating = "very favourable"
                elif yib >= 7: yib_rating = "favourable"
                elif yib >= 4: yib_rating = "partially favourable"
                elif yib >= 2: yib_rating = "average"
                else: yib_rating = "unfavourable"
            else:
                if yib > 7: yib_rating = "very favourable"
                elif yib >= 5: yib_rating = "favourable"
                elif yib >= 3: yib_rating = "partially favourable"
                elif yib >= 1: yib_rating = "average"
                else: yib_rating = "unfavourable"
        else:
            yib_rating = "average"

        modifier_scores["Years in business"] = {"score": yib if yib is not None else 0.0, "rating": yib_rating}
        underwriting_rationale["Years in business"] = f"Founding year: {founding_year}. Years in business: {yib if yib is not None else 'Unknown'}."

        # Aggregate overall rating
        numeric_scores = []
        for name, details in modifier_scores.items():
            rat = details["rating"].lower()
            score_val = RATING_SCORES.get(rat, 4.0)
            numeric_scores.append(score_val)
            # Use LLM rationale if available, otherwise fallback to mathematical rationale
            if name in assessment.get("underwriting_rationale", {}):
                raw_rat = assessment["underwriting_rationale"][name]
                # Strip trailing incorrect rating words from LLM response
                cleaned = re.sub(r'(?i)[,\s]*(very favourable|partially favourable|favourable|average|neutral|partially unfavourable|unfavourable)(?:\s*risk)?\.?$', '', raw_rat)
                underwriting_rationale[name] = f"{cleaned}, {rat}."

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
        return {
            "risk_category": risk_category,
            "underwriting_rationale": underwriting_rationale,
            "modifier_scores": modifier_scores,
            "confidence_score": confidence_score,
            "confidence_band": confidence_band,
            "human_escalation_flag": human_escalation_flag,
            "audit_logs": state.get("audit_logs", []) + logs
        }
