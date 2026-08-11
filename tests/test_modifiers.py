import unittest
import os
from src.config import BusinessRuleConfig
from src.registry import BusinessRuleRegistry
from src.factory import AgentFactory
from src.processors import UnderwriterAgent

# Trigger registration on import
import src.rules as _rules

class TestModifiersAndParser(unittest.TestCase):
    def setUp(self):
        self.factory = AgentFactory.for_rule("cyber_risk_rating")
        self.underwriter = self.factory.create_underwriter(UnderwriterAgent)

    def test_rule_registration(self):
        rules = BusinessRuleRegistry.list_rules()
        self.assertIn("cyber_risk_rating", rules)
        
        cfg = BusinessRuleRegistry.get("cyber_risk_rating")
        self.assertIsNotNone(cfg)
        self.assertEqual(cfg.rule_id, "cyber_risk_rating")

    def test_underwriter_org_complexity(self):
        # 1. Test Org Complexity for >$1B company with 11 subsidiaries (favourable)
        state_large = {
            "company_name": "Test Large",
            "domain": "test.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "revenue": 1200000000,
                "subsidiaries": ["Sub1", "Sub2", "Sub3", "Sub4", "Sub5", "Sub6", "Sub7", "Sub8", "Sub9", "Sub10", "Sub11"],
                "acquisitions": [],
                "customer_type": "B2B",
                "has_ecommerce": False,
                "domains": [{"url": "test.com", "https_encrypted": True}],
                "countries_of_operation": ["USA"],
                "continent_spread": ["North America"]
            }
        }
        # Mock LLM call to return standard formatting
        self.underwriter.call_llm = lambda prompt, temp=0.0: '{"risk_category": "Favourable", "underwriting_rationale": {"Organizational Complexity": "Reconciled ok"}}'
        res = self.underwriter.underwrite(state_large)
        self.assertEqual(res["modifier_scores"]["Organizational Complexity"]["rating"], "favourable")

        # 2. Test Org Complexity for <$50M company with 12 subsidiaries (partially unfavourable)
        state_small = {
            "company_name": "Test Small",
            "domain": "test.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "revenue": 10000000,
                "subsidiaries": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12"],
                "acquisitions": [],
                "customer_type": "B2B",
                "has_ecommerce": False,
                "domains": [{"url": "test.com", "https_encrypted": True}],
                "countries_of_operation": ["USA"],
                "continent_spread": ["North America"]
            }
        }
        res_small = self.underwriter.underwrite(state_small)
        self.assertEqual(res_small["modifier_scores"]["Organizational Complexity"]["rating"], "partially unfavourable")

    def test_underwriter_sensitive_info(self):
        # B2B, no ecommerce = favourable
        state1 = {
            "company_name": "Test B2B",
            "domain": "test.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "customer_type": "B2B",
                "has_ecommerce": False
            }
        }
        self.underwriter.call_llm = lambda prompt, temp=0.0: '{"risk_category": "Favourable", "underwriting_rationale": {}}'
        res1 = self.underwriter.underwrite(state1)
        self.assertEqual(res1["modifier_scores"]["Amount of sensitive information"]["rating"], "favourable")

        # B2C, has ecommerce = Partially Unfavourable
        state2 = {
            "company_name": "Test B2C",
            "domain": "test.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "customer_type": "B2C",
                "has_ecommerce": True
            }
        }
        res2 = self.underwriter.underwrite(state2)
        self.assertEqual(res2["modifier_scores"]["Amount of sensitive information"]["rating"], "partially unfavourable")

    def test_underwriter_years_in_business(self):
        # 1. >$1B revenue, yib = 35 (very favourable)
        state_large = {
            "company_name": "Large Old Co",
            "domain": "largeold.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "revenue": 1500000000,
                "founding_year": 1990
            }
        }
        self.underwriter.call_llm = lambda prompt, temp=0.0: '{"risk_category": "Favourable", "underwriting_rationale": {}}'
        res = self.underwriter.underwrite(state_large)
        self.assertEqual(res["modifier_scores"]["Years in business"]["rating"], "very favourable")

        # 2. <$50M revenue, yib = 2 (average)
        state_small = {
            "company_name": "Small Startup",
            "domain": "startup.com",
            "accuracy_score": 1.0,
            "mismatch_flag": False,
            "conflict_flags": [],
            "reconciled_profile": {
                "revenue": 5000000,
                "founding_year": 2024
            }
        }
        res2 = self.underwriter.underwrite(state_small)
        self.assertEqual(res2["modifier_scores"]["Years in business"]["rating"], "average")

    def test_sec_collector_revenue_extraction(self):
        # Test that SECCollectorAgent correctly chooses the best revenue key
        # and extracts the latest annual and chronological deduplicated quarterly revenues.
        from src.collectors import SECCollectorAgent
        from unittest.mock import patch, MagicMock
        import json
        
        collector = self.factory.create_collector_agent("sec", SECCollectorAgent)
        
        # Mock company tickers JSON response
        mock_tickers = {
            "0": {"cik_str": 1297989, "ticker": "EXLS", "title": "ExlService Holdings, Inc."}
        }
        
        # Mock CIK JSON response with multiple keys (SalesRevenueNet ending 2013 and RevenueFromContractWithCustomerExcludingAssessedTax ending 2025)
        mock_facts = {
            "facts": {
                "us-gaap": {
                    "SalesRevenueNet": {
                        "units": {
                            "USD": [
                                # Old 10-K entry for 2013
                                {"start": "2013-01-01", "end": "2013-12-31", "val": 124000000, "form": "10-K", "fy": 2013, "fp": "FY", "filed": "2014-03-03"}
                            ]
                        }
                    },
                    "RevenueFromContractWithCustomerExcludingAssessedTax": {
                        "units": {
                            "USD": [
                                # 2024 10-K annual entry
                                {"start": "2024-01-01", "end": "2024-12-31", "val": 1800000000, "form": "10-K", "fy": 2024, "fp": "FY", "filed": "2025-02-25"},
                                # 2025 10-K annual entry
                                {"start": "2025-01-01", "end": "2025-12-31", "val": 2000000000, "form": "10-K", "fy": 2025, "fp": "FY", "filed": "2026-02-24"},
                                # 2025 Q1 10-Q entry (3-month duration)
                                {"start": "2025-01-01", "end": "2025-03-31", "val": 450000000, "form": "10-Q", "fy": 2025, "fp": "Q1", "filed": "2025-05-01"},
                                # 2025 Q2 10-Q entry (3-month duration)
                                {"start": "2025-04-01", "end": "2025-06-30", "val": 480000000, "form": "10-Q", "fy": 2025, "fp": "Q2", "filed": "2025-08-01"},
                                # 2025 Q2 YTD 10-Q entry (6-month duration, should be ignored for quarterly list)
                                {"start": "2025-01-01", "end": "2025-06-30", "val": 930000000, "form": "10-Q", "fy": 2025, "fp": "Q2", "filed": "2025-08-01"}
                            ]
                        }
                    }
                }
            }
        }
        
        # Mock urlopen calls
        def mock_urlopen(req, *args, **kwargs):
            url = req.full_url if hasattr(req, 'full_url') else req
            mock_res = MagicMock()
            mock_res.__enter__.return_value = mock_res
            if "company_tickers.json" in url:
                mock_res.read.return_value = json.dumps(mock_tickers).encode()
            elif "CIK0001297989.json" in url:
                mock_res.read.return_value = json.dumps(mock_facts).encode()
            else:
                mock_res.read.return_value = b"{}"
            return mock_res
            
        with patch('urllib.request.urlopen', side_effect=mock_urlopen):
            # Mock call_llm because we don't want to hit Groq API in this unit test
            collector.call_llm = lambda prompt, temp=0.0: '{"revenue": 2000000000, "fiscal_year": 2025, "subsidiaries_count": 0, "quarterly_revenue": []}'
            import asyncio
            res = asyncio.run(collector.collect("ExlService Holdings, Inc.", "exlservice.com"))
            
            self.assertEqual(res["status"], "success")
            findings = res["findings"]
            
            # Annual revenue should be the latest (2,000,000,000) from the newer key
            self.assertEqual(findings["revenue"], 2000000000)
            self.assertEqual(findings["fiscal_year"], 2025)
            
            # Quarterly revenue list should contain the two 3-month period values (450M and 480M) but ignore the 6-month YTD one (930M)
            self.assertEqual(findings["quarterly_revenue"], [450000000, 480000000])

    def test_dynamic_sic_inference(self):
        from src.processors import CollectionCoordinatorAgent
        coordinator = self.factory.create_coordinator(CollectionCoordinatorAgent)
        
        # Test 1: Company name contains "insurance", should infer "6331"
        reports = {
            "Wikipedia": {"status": "success", "findings": {"industry_classification": ["Property and Casualty"]}},
            "Wikidata": {"status": "success", "findings": {"industry": ["financial services"]}}
        }
        res1 = coordinator.infer_sic_codes_dynamically("Liberty Mutual Insurance Company", reports, ["7372"])
        self.assertEqual(res1, ["6331"])

        # Test 2: Wikipedia/Wikidata findings contain "hospital" or "healthcare", should infer "8062"
        reports_health = {
            "Wikipedia": {"status": "success", "findings": {"industry_classification": ["General Hospital", "Healthcare"]}}
        }
        res2 = coordinator.infer_sic_codes_dynamically("Any Hospital Group", reports_health, ["7372"])
        self.assertEqual(res2, ["8062"])

        # Test 3: Existing SIC code is not "7372", should keep it
        res3 = coordinator.infer_sic_codes_dynamically("Liberty Mutual", reports, ["6331"])
        self.assertEqual(res3, ["6331"])

        # Test 4: Default fallback when nothing matches and no existing valid codes
        res4 = coordinator.infer_sic_codes_dynamically("Generic Random Inc", {}, ["7372"])
        self.assertEqual(res4, ["7372"])

    def test_report_comparison(self):
        from reports.report_generator import generate_underwriting_audit_report
        mock_state = {
            "entity_status": "Match",
            "risk_category": "Partially Favourable",
            "confidence_score": 58.3,
            "confidence_band": "Medium",
            "human_escalation_flag": False,
            "token_summary": {"prompt_tokens": 1000, "completion_tokens": 200, "total_tokens": 1200},
            "collected_evidence": {
                "Wikipedia": {
                    "status": "success",
                    "findings": {
                        "subsidiaries": ["Safeco", "State Auto", "Ironshore", "Peerless"],
                        "acquisitions": []
                    }
                }
            },
            "reconciled_profile": {
                "revenue": 50218500000,
                "founding_year": 1912,
                "customer_type": "MIX",
                "has_ecommerce": True,
                "privacy_policy_published": True,
                "subsidiaries": ["Safeco", "State Auto", "Ironshore", "Peerless"],
                "acquisitions": [], 
                "countries_of_operation": ["United States", "Brazil"],
                "continent_spread": ["North America"],
                "domains": [{"url": "libertymutual.com", "https_encrypted": True}],
                "digital_exposure": 4,
                "disruption_speed": 3,
                "recovery_complexity": 4,
                "sic_codes": ["6331"]
            },
            "modifier_scores": {
                "Mergers and Acquisitions": {"rating": "favourable", "score": "8.00"},
                "Amount of sensitive information": {"rating": "partially unfavourable", "score": "0.00"},
                "Domain Encryption": {"rating": "favourable", "score": "12/12"},
                "Geographic Spread": {"rating": "average", "score": "15.00"},
                "Internet footprint": {"rating": "favourable", "score": "3.0"},
                "Nature of services": {"rating": "partially unfavourable", "score": "high_risk"},
                "Organizational Complexity": {"rating": "average", "score": "24.00"},
                "Privacy Regulation": {"rating": "partially favourable", "score": "1.00"},
                "Seasonality of sales": {"rating": "average", "score": "0.00"},
                "Volatility/Recovery in Sales": {"rating": "average", "score": "10.00"},
                "Applicability of Privacy Regulation": {"rating": "average", "score": "0.00"},
                "B2C End Products": {"rating": "partially favourable", "score": "0.00"},
                "Years in business": {"rating": "very favourable", "score": "114.00"},
                "Cybersecurity Info": {"rating": "favourable", "score": "2.0"},
                "Industry & Company Breach History": {"rating": "favourable", "score": "4.0"}
            },
            "underwriting_rationale": {}
        }
        # Test new JSON key loading path
        report_path_json = generate_underwriting_audit_report(
            mock_state,
            "Liberty Mutual Insurance",
            "www.libertymutualgroup.com",
            "cyber_risk_rating",
            ground_truth_key="liberty_mutual"
        )
        self.assertTrue(os.path.exists(report_path_json))
        if os.path.exists(report_path_json):
            os.remove(report_path_json)

    def test_volatility_v1_modifier(self):
        from src.processors import AssessmentUnderwriterAgent
        underwriter = self.factory.create_underwriter(AssessmentUnderwriterAgent)
        
        # Test 1: Low digital exposure (D1=1, D2=1, D3=1) + Favourable overlay (-1) => Total 2 => Favourable (VR-01)
        prof1 = {"digital_exposure": 1, "disruption_speed": 1, "recovery_complexity": 1, "has_sales_spikes": False}
        res1 = underwriter.evaluate_modifiers(prof1)
        vol1 = res1["modifier_scores"]["Volatility/Recovery in Sales"]
        self.assertEqual(vol1["rating"], "favourable")
        self.assertEqual(vol1["score"], 2.0)

        # Test 2: High digital exposure (D1=5, D2=5, D3=5) + Spikes (+1) => Total 16 => Partially Unfavourable (VR-04)
        prof2 = {"digital_exposure": 5, "disruption_speed": 5, "recovery_complexity": 5, "has_sales_spikes": True}
        res2 = underwriter.evaluate_modifiers(prof2)
        vol2 = res2["modifier_scores"]["Volatility/Recovery in Sales"]
        self.assertEqual(vol2["rating"], "partially unfavourable")
        self.assertEqual(vol2["score"], 16.0)

    def test_nature_of_services_modifier(self):
        from src.processors import AssessmentUnderwriterAgent
        underwriter = self.factory.create_underwriter(AssessmentUnderwriterAgent)
        
        # Test 1: >1B Revenue, 2 sub-industries, Target appetite (0.1) => Score 0.2 => Very Favourable (NS-01)
        prof1 = {"revenue": 2000000000, "sub_industries": ["Property & Casualty", "Reinsurance"], "worst_sub_industry_appetite": "target"}
        res1 = underwriter.evaluate_modifiers(prof1)
        ns1 = res1["modifier_scores"]["Nature of services"]
        self.assertEqual(ns1["rating"], "very favourable")
        self.assertEqual(ns1["score"], "0.2")

        # Test 2: >1B Revenue, 5 sub-industries, Prohibited appetite (x3) => Score 15.0 => Average (NS-04)
        prof2 = {"revenue": 2000000000, "sub_industries": ["1", "2", "3", "4", "5"], "worst_sub_industry_appetite": "prohibited"}
        res2 = underwriter.evaluate_modifiers(prof2)
        ns2 = res2["modifier_scores"]["Nature of services"]
        self.assertEqual(ns2["rating"], "average")
        self.assertEqual(ns2["score"], "15.0")

    def test_internet_footprint_v1_modifier(self):
        from src.processors import AssessmentUnderwriterAgent
        underwriter = self.factory.create_underwriter(AssessmentUnderwriterAgent)
        
        # Test 1: >1B Revenue, 1 domain, 100k customers (1.5 multiplier) => Score 1.5 => Very Favourable (IF-01)
        prof1 = {"revenue": 2000000000, "domains": [{"url": "example.com"}], "estimated_customers_count": 50000}
        res1 = underwriter.evaluate_modifiers(prof1)
        if1 = res1["modifier_scores"]["Internet footprint"]
        self.assertEqual(if1["rating"], "very favourable")
        self.assertEqual(if1["score"], "1.5")

        # Test 2: >1B Revenue, 5 domains, >1B customers (4.0 multiplier) => Score 20.0 => Average (IF-04)
        prof2 = {"revenue": 2000000000, "domains": [{"url": f"d{i}.com"} for i in range(5)], "estimated_customers_count": 2000000000}
        res2 = underwriter.evaluate_modifiers(prof2)
        if2 = res2["modifier_scores"]["Internet footprint"]
        self.assertEqual(if2["rating"], "average")
        self.assertEqual(if2["score"], "20.0")

    def test_cybersecurity_info_modifier(self):
        from src.processors import AssessmentUnderwriterAgent
        underwriter = self.factory.create_underwriter(AssessmentUnderwriterAgent)

        # Test 1: Public Entity with Audited Certs (ISO 27001) + DMARC + CISO => Favourable
        prof1 = {
            "revenue": 2000000000, "entity_status": "Public",
            "cybersecurity_frameworks": ["ISO 27001", "SOC 2 Type II"],
            "has_dmarc_spf": True, "has_security_headers": True, "has_ciso_disclosure": True
        }
        res1 = underwriter.evaluate_modifiers(prof1)
        ci1 = res1["modifier_scores"]["Cybersecurity Info"]
        self.assertEqual(ci1["rating"], "favourable")

        # Test 2: Private Entity with no certs (neutral) + weak web security => Average / Partially Unfavourable
        prof2 = {
            "revenue": 10000000, "entity_status": "Private",
            "cybersecurity_frameworks": [],
            "has_dmarc_spf": False, "has_security_headers": False
        }
        res2 = underwriter.evaluate_modifiers(prof2)
        ci2 = res2["modifier_scores"]["Cybersecurity Info"]
        self.assertIn(ci2["rating"], ["average", "partially unfavourable"])

    def test_industry_and_company_breach_history_modifier(self):
        from src.processors import AssessmentUnderwriterAgent
        underwriter = self.factory.create_underwriter(AssessmentUnderwriterAgent)

        # Test 1: Public Mega Enterprise with 0 breaches in High-risk industry (7372: 3 pts) => Score 3.0 => Favourable (BH-02)
        prof1 = {
            "revenue": 2000000000, "entity_status": "Public", "sic_codes": ["7372"], "company_breaches": []
        }
        res1 = underwriter.evaluate_modifiers(prof1)
        bh1 = res1["modifier_scores"]["Industry & Company Breach History"]
        self.assertEqual(bh1["rating"], "favourable")

        # Test 2: Private SMB with 0 breaches -> Private Zero-Breach Floor applies -> Capped at Average
        prof2 = {
            "revenue": 10000000, "entity_status": "Private", "sic_codes": ["7372"], "company_breaches": []
        }
        res2 = underwriter.evaluate_modifiers(prof2)
        bh2 = res2["modifier_scores"]["Industry & Company Breach History"]
        self.assertEqual(bh2["rating"], "average")

        # Test 3: CISA KEV Active Exploit Penalty
        prof3 = {
            "revenue": 2000000000, "entity_status": "Public", "sic_codes": ["7372"], "company_breaches": [],
            "cisa_kev_matches": [{"cve_id": "CVE-2023-34362", "vulnerability_name": "MOVEit Transfer Vulnerability"}],
            "has_cisa_kev_vulnerabilities": True
        }
        res3 = underwriter.evaluate_modifiers(prof3)
        bh3 = res3["modifier_scores"]["Industry & Company Breach History"]
        self.assertEqual(bh3["score"], "4.0")

if __name__ == "__main__":
    unittest.main()
