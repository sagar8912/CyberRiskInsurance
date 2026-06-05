import math
import numpy as np
from typing import Dict, Any, List

class CyberRulesEngine:
    def __init__(self, parser=None):
        self.parser = parser

    def calculate_modifiers(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate all 10 underwriting modifiers based on the reconciled profile.
        Returns a dictionary containing modifier names, points, ratings, and audit rationales.
        """
        revenue = profile.get("revenue")
        if revenue is None:
            revenue = 0
        results = {}

        # 1. Mergers and Acquisitions
        acqs = profile.get("acquisitions", [])
        ma_points = 0.0
        for acq in acqs:
            # Determine deal size points
            # pre-acquisition employee counts or revenue compared to current pre-acquisition size
            deal_type = acq.get("deal_type", "minor acquisition").lower()
            pts = 1.0
            if "trans" in deal_type:
                pts = 4.0
            elif "material" in deal_type:
                pts = 3.0
            elif "minor" in deal_type:
                pts = 2.0
            
            # Recency multiplier
            recency = acq.get("recency_years", 5.0)
            mult = 0.0
            if recency < 1.0:
                mult = 2.0
            elif recency < 2.0:
                mult = 1.5
            elif recency < 5.0:
                mult = 1.0
            elif recency <= 10.0:
                mult = 0.5
            
            ma_points += (pts * mult)

        # Map M&A points to revenue tiers
        ma_rating = "average"
        if revenue >= 1000000000: # >$1B
            if ma_points <= 5: ma_rating = "very favourable"
            elif ma_points <= 10: ma_rating = "favourable"
            elif ma_points <= 15: ma_rating = "partially favourable"
            elif ma_points <= 20: ma_rating = "average"
            elif ma_points <= 30: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        elif revenue >= 250000000: # $250M - $1B
            if ma_points <= 3: ma_rating = "very favourable"
            elif ma_points <= 6: ma_rating = "favourable"
            elif ma_points <= 10: ma_rating = "partially favourable"
            elif ma_points <= 15: ma_rating = "average"
            elif ma_points <= 20: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        elif revenue >= 50000000: # $50M - $250M
            if ma_points <= 2: ma_rating = "very favourable"
            elif ma_points <= 4: ma_rating = "favourable"
            elif ma_points <= 7: ma_rating = "partially favourable"
            elif ma_points <= 10: ma_rating = "average"
            elif ma_points <= 15: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"
        else: # < $50M
            if ma_points <= 1: ma_rating = "very favourable"
            elif ma_points <= 3: ma_rating = "favourable"
            elif ma_points <= 5: ma_rating = "partially favourable"
            elif ma_points <= 7: ma_rating = "average"
            elif ma_points <= 10: ma_rating = "partially unfavourable"
            else: ma_rating = "unfavourable"

        results["Mergers and Acquisitions"] = {
            "score": ma_points,
            "rating": ma_rating,
            "rationale": f"M&A points: {ma_points:.1f} calculated across {len(acqs)} acquisitions. Revenue tier comparison applied."
        }

        # 2. Amount of sensitive information
        cust_type = str(profile.get("customer_type", "B2B")).upper()
        has_ecom = profile.get("has_ecommerce", False)
        sens_rating = "Average"
        
        if "B2B" in cust_type and not has_ecom:
            sens_rating = "favourable"
        elif "B2B" in cust_type and has_ecom:
            sens_rating = "Partially favourable"
        elif ("B2C" in cust_type or "B2B" in cust_type) and not has_ecom:
            sens_rating = "Average"
        else:
            sens_rating = "Partially Unfavourable"

        results["Amount of sensitive information"] = {
            "score": 0.0,
            "rating": sens_rating,
            "rationale": f"Customer type: {cust_type}, E-commerce presence: {has_ecom}."
        }

        # 3. Domain Encryption
        domains = profile.get("domains", [])
        total_domains = len(domains)
        encrypted_count = sum(1 for d in domains if d.get("https_encrypted", False))
        
        enc_rating = "Average"
        if total_domains > 0:
            if encrypted_count == total_domains:
                enc_rating = "favourable"
            elif encrypted_count > 0: # main domain + some secondary
                enc_rating = "partially favourable"
            else:
                enc_rating = "Average"
        
        results["Domain Encryption"] = {
            "score": f"{encrypted_count}/{total_domains}",
            "rating": enc_rating,
            "rationale": f"HTTPS Encryption: {encrypted_count} of {total_domains} domains encrypted."
        }

        # 4. Geographic Spread
        countries = profile.get("countries_of_operation", ["USA"])
        country_count = len(countries)
        continent_count = len(profile.get("continent_spread", ["North America"]))
        usa_presence = profile.get("usa_presence", True)
        
        geo_rating = "average"
        
        if revenue >= 1000000000: # >$1B
            if country_count <= 10 and continent_count == 1:
                geo_rating = "favourable"
            elif country_count <= 10:
                geo_rating = "partially favourable"
            else:
                geo_rating = "average"
        elif revenue >= 250000000: # $250M - $1B
            if country_count <= 5 and continent_count == 1:
                geo_rating = "favourable"
            elif country_count <= 7:
                geo_rating = "partially favourable"
            else:
                geo_rating = "average"
        elif revenue >= 50000000: # $50M - $250M
            if country_count <= 3 and continent_count == 1:
                geo_rating = "favourable"
            elif country_count <= 5:
                geo_rating = "partially favourable"
            else:
                geo_rating = "average"
        else: # < $50M
            if country_count <= 2 and continent_count == 1:
                geo_rating = "favourable"
            elif country_count <= 10:
                geo_rating = "partially favourable"
            else:
                geo_rating = "average"

        results["Geographic Spread"] = {
            "score": country_count,
            "rating": geo_rating,
            "rationale": f"Operates in {country_count} countries across {continent_count} continents. USA Presence: {usa_presence}."
        }

        # 5. Internet footprint
        domain_count = int(profile.get("internet_exposure_domains", 1))
        scale = profile.get("customer_base_scale", "SMB (<1k)")
        
        mult = 1.0
        if "Enterprise" in scale:
            mult = 3.0
        elif "Mid-Market" in scale:
            mult = 2.0
            
        footprint_score = domain_count * mult
        footprint_rating = "average"
        
        if footprint_score <= 5:
            footprint_rating = "favourable"
        elif footprint_score <= 20:
            footprint_rating = "average"
        elif footprint_score <= 100:
            footprint_rating = "partially unfavourable"
        else:
            footprint_rating = "unfavourable"

        results["Internet footprint"] = {
            "score": footprint_score,
            "rating": footprint_rating,
            "rationale": f"Footprint score: {footprint_score} (domains: {domain_count} x multiplier: {mult} based on customer scale: {scale})."
        }

        # 6. Nature of services
        appetite = profile.get("services_appetite", "medium_risk")
        services_rating = "average"
        if "low_risk" in appetite:
            services_rating = "favourable"
        elif "high_risk" in appetite:
            services_rating = "unfavourable"
            
        results["Nature of services"] = {
            "score": appetite,
            "rating": services_rating,
            "rationale": f"Cyber sub-industry appetite category is '{appetite}'."
        }

        # 7. Organizational Complexity
        subsidiaries_count = len(profile.get("subsidiaries", []))
        org_rating = "average"
        
        if revenue >= 1000000000: # >= $1B
            if subsidiaries_count < 10: org_rating = "very favourable"
            elif subsidiaries_count <= 20: org_rating = "favourable"
            elif subsidiaries_count <= 50: org_rating = "average"
            else: org_rating = "partially unfavourable"
        elif revenue >= 250000000: # $250M - $1B
            if subsidiaries_count < 7: org_rating = "very favourable"
            elif subsidiaries_count <= 15: org_rating = "favourable"
            elif subsidiaries_count <= 30: org_rating = "average"
            else: org_rating = "partially unfavourable"
        elif revenue >= 50000000: # $50M - $250M
            if subsidiaries_count < 5: org_rating = "very favourable"
            elif subsidiaries_count <= 10: org_rating = "favourable"
            elif subsidiaries_count <= 15: org_rating = "average"
            else: org_rating = "partially unfavourable"
        else: # < $50M
            if subsidiaries_count < 3: org_rating = "very favourable"
            elif subsidiaries_count <= 6: org_rating = "favourable"
            elif subsidiaries_count <= 10: org_rating = "average"
            else: org_rating = "partially unfavourable"

        results["Organizational Complexity"] = {
            "score": subsidiaries_count,
            "rating": org_rating,
            "rationale": f"Total subsidiaries: {subsidiaries_count} evaluated against revenue tier."
        }

        # 8. Privacy Regulation
        has_policy = profile.get("privacy_policy_published", False)
        mentions = profile.get("compliance_mentions", [])
        mentions_count = len(mentions)
        
        priv_rating = "average"
        if has_policy:
            if mentions_count >= 2:
                priv_rating = "favourable"
            elif mentions_count == 1:
                priv_rating = "partially favourable"
            else:
                priv_rating = "average"
        else:
            priv_rating = "partially unfavourable"

        results["Privacy Regulation"] = {
            "score": mentions_count,
            "rating": priv_rating,
            "rationale": f"Privacy Policy published: {has_policy}, Compliance frameworks: {mentions_count} ({', '.join(mentions)})."
        }

        # 9. Seasonality of sales
        q_rev = profile.get("quarterly_revenue", [])
        sic_codes = profile.get("sic_codes", ["7372"])
        sic_first = sic_codes[0] if sic_codes else "7372"
        
        cv = None
        season_rating = "average"
        
        if len(q_rev) >= 4:
            mean = np.mean(q_rev)
            std = np.std(q_rev)
            if mean > 0:
                cv = std / mean
                if cv < 0.1:
                    season_rating = "favourable"
                elif cv <= 0.25:
                    season_rating = "average"
                else:
                    season_rating = "partially unfavourable"
            rationale = f"Sales seasonality CV: {cv:.3f} calculated from quarterly revenues."
        else:
            # Fallback to SIC benchmark
            if sic_first == "5311": # Retail Department store
                season_rating = "partially unfavourable"
                rationale = f"Fallback to SIC code {sic_first} benchmark: Retail has high seasonality."
            else:
                season_rating = "average"
                rationale = f"Fallback to SIC code {sic_first} benchmark: Software/services expected average seasonality."

        results["Seasonality of sales"] = {
            "score": cv if cv is not None else 0.0,
            "rating": season_rating,
            "rationale": rationale
        }

        # 10. Volatility/Recovery in Sales
        de = profile.get("digital_exposure", 3)
        ds = profile.get("disruption_speed", 3)
        rc = profile.get("recovery_complexity", 3)
        
        vol_avg = (de + ds + rc) / 3.0
        vol_rating = "average"
        if vol_avg <= 2.0:
            vol_rating = "favourable"
        elif vol_avg <= 3.5:
            vol_rating = "average"
        else:
            vol_rating = "partially unfavourable"

        results["Volatility/Recovery in Sales"] = {
            "score": vol_avg,
            "rating": vol_rating,
            "rationale": f"Dimensions avg: {vol_avg:.2f} (Digital exposure: {de}/5, Disruption speed: {ds}/5, Recovery complexity: {rc}/5)."
        }

        # Add Excel metadata details to findings if parser is loaded
        if self.parser:
            for name, res in results.items():
                meta = self.parser.get_modifier(name)
                if meta:
                    res["excel_description"] = meta.get("description", "")
                    res["excel_target_parameter"] = meta.get("target_parameter", "")
                    res["excel_research_needed"] = meta.get("research_needed", "")

        return results
