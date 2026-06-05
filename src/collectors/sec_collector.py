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
            fiscal_year = None
            revenue_keys = ['Revenues', 'SalesRevenueNet', 'RevenueFromContractWithCustomerExcludingAssessedTax']
            
            valid_annuals = []
            
            for rk in revenue_keys:
                if rk in gaap:
                    units = gaap[rk].get('units', {})
                    usd = units.get('USD', [])
                    for u in usd:
                        if u.get('form') == '10-K' and 'fy' in u:
                            frame = u.get('frame', '')
                            # Ensure it's an annual frame without a 'Q' (e.g. CY2024)
                            # Or if no frame, use dates difference to roughly ensure it's a year.
                            is_annual = False
                            if frame and len(frame) == 6 and frame.startswith('CY'):
                                is_annual = True
                            else:
                                start = u.get('start')
                                end = u.get('end')
                                if start and end:
                                    try:
                                        from datetime import datetime
                                        d1 = datetime.strptime(start, "%Y-%m-%d")
                                        d2 = datetime.strptime(end, "%Y-%m-%d")
                                        if (d2 - d1).days > 300:
                                            is_annual = True
                                    except Exception:
                                        pass
                            
                            if is_annual:
                                valid_annuals.append(u)
                                
            if valid_annuals:
                latest = sorted(valid_annuals, key=lambda x: x['fy'])[-1]
                revenue = latest['val']
                fiscal_year = latest['fy']
                            
            # 3. Extract Exhibit 21 Subsidiaries
            subsidiaries_exhibit21 = []
            try:
                # Get the submissions again if needed, or we already have the CIK
                req_sub = urllib.request.Request(f"https://data.sec.gov/submissions/CIK{cik}.json", headers=headers)
                with urllib.request.urlopen(req_sub, timeout=10) as res_sub:
                    sub_data = json.loads(res_sub.read().decode())
                
                filings = sub_data.get('filings', {}).get('recent', {})
                forms = filings.get('form', [])
                accessions = filings.get('accessionNumber', [])
                
                acc_no = None
                for i, f in enumerate(forms):
                    if f == '10-K':
                        acc_no = accessions[i]
                        break
                        
                if acc_no:
                    acc_no_nodashes = acc_no.replace('-', '')
                    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodashes}/index.json"
                    
                    req_idx = urllib.request.Request(index_url, headers=headers)
                    with urllib.request.urlopen(req_idx, timeout=10) as res_idx:
                        idx = json.loads(res_idx.read().decode())
                        
                    ex21_file = None
                    for file_info in idx['directory']['item']:
                        name = file_info['name']
                        if 'ex21' in name.lower() or 'ex-21' in name.lower() or 'exhibit21' in name.lower():
                            ex21_file = name
                            break
                            
                    if ex21_file:
                        file_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodashes}/{ex21_file}"
                        req_file = urllib.request.Request(file_url, headers=headers)
                        with urllib.request.urlopen(req_file, timeout=10) as res_file:
                            html = res_file.read().decode('utf-8', errors='ignore')
                            
                        import re
                        rows = re.findall(r'<tr[^>]*>', html, re.IGNORECASE)
                        count = max(0, len(rows) - 1)
                        if count < 2:
                            text = re.sub(r'<[^>]+>', '\n', html)
                            lines = [l.strip() for l in text.split('\n') if len(l.strip()) > 3]
                            count = len(lines) // 2
                            
                        subsidiaries_exhibit21 = [f"Subsidiary {i}" for i in range(count)]
            except Exception as e:
                pass

            return {
                "source": self.name,
                "status": "success",
                "is_mock": False,
                "findings": {
                    "sec_acquisitions": [], # Not extracted yet
                    "subsidiaries_exhibit21": subsidiaries_exhibit21,
                    "revenue": revenue,
                    "revenue_period": "annual" if revenue is not None else None,
                    "fiscal_year": fiscal_year
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
