import unittest
import os
import json
from src.graph import build_workflow
from src.utils.cache_manager import CacheManager

class TestWorkflowIntegration(unittest.TestCase):
    def setUp(self):
        # Clear cache before running integration tests to ensure deterministic runs
        self.cache_path = "data/cache/company_cache.json"
        if os.path.exists(self.cache_path):
            try:
                os.remove(self.cache_path)
            except Exception:
                pass
        self.app = build_workflow()

    def test_validation_reject(self):
        # Empty name and domain should set valid to False and stop immediately
        state = {
            "company_name": "",
            "domain": "",
            "valid": False,
            "enrichment": {},
            "mismatch_flag": False,
            "cache_hit": False,
            "cache_data": None,
            "routing_tier": "Unknown / Tiny",
            "tool_budget": [],
            "collected_evidence": {},
            "reconciled_profile": {},
            "conflict_flags": [],
            "claims_verification": {},
            "accuracy_score": 0.0,
            "risk_category": "Average",
            "underwriting_rationale": {},
            "modifier_scores": {},
            "confidence_score": 0.0,
            "confidence_band": "Low",
            "human_escalation_flag": False,
            "audit_logs": []
        }
        res = self.app.invoke(state)
        self.assertFalse(res["valid"])
        self.assertIn("Supervisor Reject", res["audit_logs"][-1])

    def test_workflow_execution_and_cache(self):
        state = {
            "company_name": "TechGiant Inc.",
            "domain": "techgiant.com",
            "valid": False,
            "enrichment": {},
            "mismatch_flag": False,
            "cache_hit": False,
            "cache_data": None,
            "routing_tier": "Unknown / Tiny",
            "tool_budget": [],
            "collected_evidence": {},
            "reconciled_profile": {},
            "conflict_flags": [],
            "claims_verification": {},
            "accuracy_score": 0.0,
            "risk_category": "Average",
            "underwriting_rationale": {},
            "modifier_scores": {},
            "confidence_score": 0.0,
            "confidence_band": "Low",
            "human_escalation_flag": False,
            "audit_logs": []
        }
        
        # 1. First execution - Cache Miss
        res_miss = self.app.invoke(state)
        self.assertTrue(res_miss["valid"])
        self.assertFalse(res_miss["cache_hit"])
        self.assertEqual(res_miss["routing_tier"], "Public / $500M+")
        self.assertEqual(res_miss["risk_category"], "Favourable") # Calculated rating for TechGiant Inc.
        self.assertTrue(res_miss["confidence_score"] > 0)
        
        # 2. Second execution - Cache Hit
        res_hit = self.app.invoke(state)
        self.assertTrue(res_hit["valid"])
        self.assertTrue(res_hit["cache_hit"])
        self.assertIsNotNone(res_hit["cache_data"])
        self.assertEqual(res_hit["cache_data"]["risk_category"], "Favourable")

    def test_entity_mismatch(self):
        state = {
            "company_name": "Amazon",
            "domain": "amazon-river.org",
            "valid": False,
            "enrichment": {},
            "mismatch_flag": False,
            "cache_hit": False,
            "cache_data": None,
            "routing_tier": "Unknown / Tiny",
            "tool_budget": [],
            "collected_evidence": {},
            "reconciled_profile": {},
            "conflict_flags": [],
            "claims_verification": {},
            "accuracy_score": 0.0,
            "risk_category": "Average",
            "underwriting_rationale": {},
            "modifier_scores": {},
            "confidence_score": 0.0,
            "confidence_band": "Low",
            "human_escalation_flag": False,
            "audit_logs": []
        }
        res = self.app.invoke(state)
        self.assertTrue(res["valid"])
        self.assertTrue(res["mismatch_flag"])
        self.assertTrue(res["human_escalation_flag"])

if __name__ == "__main__":
    unittest.main()
