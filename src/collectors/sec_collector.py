import json
import urllib.request
import urllib.parse
from typing import Dict, Any
from src.collectors.base import BaseCollector

class SECCollector(BaseCollector):
    def __init__(self):
        super().__init__("SECCollector")

    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        headers = {
            'User-Agent': 'CyberRiskAgent/1.0 (contact@example.com)'
        }
        
        try:
            # 1. Resolve Company Name to CIK
            req = urllib.request.Request("https://www.sec.gov/files/company_tickers.json", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                tickers = json.loads(response.read().decode())
                
            cik = None
            for key, data in tickers.items():
                if company_name.lower() in data['title'].lower():
                    cik = str(data['cik_str']).zfill(10)
                    break
                    
            if not cik:
                return {
                    "source": self.name,
                    "status": "skipped",
                    "is_mock": False,
                    "message": "Company not found in SEC EDGAR tickers.",
                    "findings": {}
                }
                
            # 2. Fetch Company Facts
            req2 = urllib.request.Request(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", headers=headers)
            with urllib.request.urlopen(req2, timeout=10) as response:
                facts = json.loads(response.read().decode())
                
            gaap = facts.get('facts', {}).get('us-gaap', {})
            
            revenue = None
            revenue_keys = ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax']
            
            for rk in revenue_keys:
                if rk in gaap:
                    units = gaap[rk].get('units', {})
                    usd = units.get('USD', [])
                    if usd:
                        # Find the latest annual revenue (form 10-K)
                        annuals = [u for u in usd if u.get('form') == '10-K' and 'fy' in u]
                        if annuals:
                            latest = sorted(annuals, key=lambda x: x['end'])[-1]
                            revenue = latest['val']
                            break
                            
            return {
                "source": self.name,
                "status": "success",
                "is_mock": False,
                "findings": {
                    "sec_acquisitions": [], # Not extracted yet
                    "subsidiaries_exhibit21": [], # Not extracted yet
                    "revenue": revenue
                }
            }
        except Exception as e:
            return {
                "source": self.name,
                "status": "error",
                "is_mock": False,
                "error": str(e),
                "findings": {}
            }
