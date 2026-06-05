import unittest
from src.utils.excel_parser import ExcelParser
from src.utils.rules_engine import CyberRulesEngine

class TestModifiersAndParser(unittest.TestCase):
    def setUp(self):
        self.parser = ExcelParser(filepath="data/cyber_rater_modifier_summary.xlsx")
        self.engine = CyberRulesEngine(parser=self.parser)

    def test_excel_parsing(self):
        names = self.parser.get_all_names()
        self.assertEqual(len(names), 10, f"Expected 10 modifiers, but found {len(names)}: {names}")
        
        # Test specific modifier detail extraction
        org_mod = self.parser.get_modifier("Organizational Complexity")
        self.assertIsNotNone(org_mod)
        self.assertIn("Revenue >= $1B", org_mod["description"])
        self.assertEqual(org_mod["target_parameter"], "Subsidiary count and organizational hierarchy complexity.")

    def test_rules_engine_complexity(self):
        # 1. Test Org Complexity for >$1B company with 11 subsidiaries (favourable)
        profile_large = {
            "revenue": 1200000000,
            "subsidiaries": ["Sub1", "Sub2", "Sub3", "Sub4", "Sub5", "Sub6", "Sub7", "Sub8", "Sub9", "Sub10", "Sub11"],
            "acquisitions": [],
            "customer_type": "B2B",
            "has_ecommerce": False,
            "domains": [{"url": "test.com", "https_encrypted": True}],
            "countries_of_operation": ["USA"],
            "continent_spread": ["North America"]
        }
        res = self.engine.calculate_modifiers(profile_large)
        self.assertEqual(res["Organizational Complexity"]["rating"], "favourable")

        # 2. Test Org Complexity for <$50M company with 12 subsidiaries (partially unfavourable)
        profile_small = {
            "revenue": 10000000,
            "subsidiaries": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12"],
            "acquisitions": [],
            "customer_type": "B2B",
            "has_ecommerce": False,
            "domains": [{"url": "test.com", "https_encrypted": True}],
            "countries_of_operation": ["USA"],
            "continent_spread": ["North America"]
        }
        res_small = self.engine.calculate_modifiers(profile_small)
        self.assertEqual(res_small["Organizational Complexity"]["rating"], "partially unfavourable")

    def test_rules_engine_sensitive_info(self):
        # B2B, no ecommerce = favourable
        p1 = {"customer_type": "B2B", "has_ecommerce": False}
        res1 = self.engine.calculate_modifiers(p1)
        self.assertEqual(res1["Amount of sensitive information"]["rating"], "favourable")

        # B2C, has ecommerce = Partially Unfavourable
        p2 = {"customer_type": "B2C", "has_ecommerce": True}
        res2 = self.engine.calculate_modifiers(p2)
        self.assertEqual(res2["Amount of sensitive information"]["rating"], "Partially Unfavourable")

if __name__ == "__main__":
    unittest.main()
