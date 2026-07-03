import os
import json
import socket
import ssl
import urllib.request
import urllib.parse
from typing import Dict, Any
from src.base_agents import BaseCollectorAgent

class WikipediaCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        query = urllib.parse.quote(company_name)
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json"
        
        logger = self.get_logger()
        logger.info(f"[Wikipedia Collector] Fetching search results for '{company_name}' using query '{query}'")
        search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={query}&utf8=&format=json"
        
        try:
            req = urllib.request.Request(search_url, headers={'User-Agent': self.USER_AGENT})
            logger.info(f"[Wikipedia Collector] Requesting URL: {search_url} with User-Agent: {self.USER_AGENT}")
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_bytes = response.read()
                logger.info(f"[Wikipedia Collector] Received search API response (status {response.status}, {len(resp_bytes)} bytes)")
                data = json.loads(resp_bytes.decode())
                
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                logger.info(f"[Wikipedia Collector] No search results returned for query '{query}'")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "No Wikipedia article found.",
                    "findings": {}
                }
                
            title = urllib.parse.quote(search_results[0]["title"])
            summary_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=&titles={title}&format=json"
            
            logger.info(f"[Wikipedia Collector] Requesting full extract from Wikipedia page for title '{search_results[0]['title']}'")
            logger.info(f"[Wikipedia Collector] Requesting URL: {summary_url}")
            req2 = urllib.request.Request(summary_url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req2, timeout=10) as response2:
                resp2_bytes = response2.read()
                logger.info(f"[Wikipedia Collector] Received extract API response (status {response2.status}, {len(resp2_bytes)} bytes)")
                summary_data = json.loads(resp2_bytes.decode())
            
            pages = summary_data.get("query", {}).get("pages", {})
            page = list(pages.values())[0] if pages else {}
            extract = page.get("extract", "")[:12000]
            logger.info(f"[Wikipedia Collector] Page extract successfully retrieved. Extract preview (first 500 chars):\n{extract[:500]}...")
            
            if not extract:
                logger.info("[Wikipedia Collector] Wikipedia extract page is empty")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "Wikipedia page extract is empty.",
                    "findings": {}
                }

            # Call LLM to extract fields from the Wikipedia page text
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "wikipedia_text": extract
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)
            
            # Map target fields
            findings = {k: extracted.get(k) for k in self.config.target_fields}
            logger.info(f"[Wikipedia Collector] Mapped target fields: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.error(f"[Wikipedia Collector] Collection failed: {e}\nTraceback:\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"{e}\nTraceback:\n{traceback.format_exc()}",
                "findings": {}
            }

class WikidataCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        logger = self.get_logger()
        try:
            # 1. Search entities
            query = urllib.parse.urlencode({
                'action': 'wbsearchentities',
                'search': company_name,
                'language': 'en',
                'format': 'json',
                'limit': 5
            })
            url = f'https://www.wikidata.org/w/api.php?{query}'
            req = urllib.request.Request(url, headers={'User-Agent': self.USER_AGENT})
            
            logger.info(f"[Wikidata Collector] Resolving entity for search: '{company_name}'")
            logger.info(f"[Wikidata Collector] Requesting URL: {url}")
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[Wikidata Collector] Received wbsearchentities response (status {response.status}, {len(resp_bytes)} bytes)")
                data = json.loads(resp_bytes.decode())
                
            search_results = data.get('search', [])
            if not search_results:
                logger.info(f"[Wikidata Collector] No entity search results resolved on Wikidata for '{company_name}'")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "No entity resolved on Wikidata.",
                    "findings": {}
                }
                
            qids = [res['id'] for res in search_results]
            logger.info(f"[Wikidata Collector] Search matched entity IDs: {qids}")
            
            # 2. Get entity claims
            query2 = urllib.parse.urlencode({
                'action': 'wbgetentities',
                'ids': '|'.join(qids),
                'format': 'json',
                'props': 'claims|labels'
            })
            url2 = f'https://www.wikidata.org/w/api.php?{query2}'
            req2 = urllib.request.Request(url2, headers={'User-Agent': self.USER_AGENT})
            
            logger.info(f"[Wikidata Collector] Requesting entity details for IDs: {qids}")
            logger.info(f"[Wikidata Collector] Requesting URL: {url2}")
            with urllib.request.urlopen(req2, timeout=10) as response:
                resp2_bytes = response.read()
                logger.info(f"[Wikidata Collector] Received wbgetentities response (status {response.status}, {len(resp2_bytes)} bytes)")
                data2 = json.loads(resp2_bytes.decode())
                
            entities = data2.get('entities', {})
            best_qid = None
            best_claims = {}
            
            import difflib
            for qid_candidate in qids:
                entity = entities.get(qid_candidate, {})
                label = entity.get('labels', {}).get('en', {}).get('value', '').lower()
                candidate_claims = entity.get('claims', {})
                
                websites = []
                for statement in candidate_claims.get('P856', []):
                    snak = statement.get('mainsnak', {})
                    if snak.get('snaktype') == 'value' and snak.get('datavalue', {}).get('type') == 'string':
                        websites.append(snak.get('datavalue', {}).get('value'))
                        
                domain_match = False
                for w in websites:
                    if domain.lower() in w.lower():
                        domain_match = True
                        break
                        
                sim = difflib.SequenceMatcher(None, company_name.lower(), label).ratio()
                logger.info(f"[Wikidata Collector] Evaluating entity {qid_candidate} ({label}): domain_match={domain_match}, name_similarity={sim:.2f}")
                if domain_match or sim > 0.8:
                    best_qid = qid_candidate
                    best_claims = candidate_claims
                    logger.info(f"[Wikidata Collector] Selected best entity match: {best_qid} ('{label}')")
                    break
                    
            if not best_qid:
                logger.info(f"[Wikidata Collector] Could not resolve matching company entity on Wikidata with high confidence (sim > 0.8 or domain match) out of: {qids}")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "Could not resolve matching company entity on Wikidata.",
                    "findings": {}
                }

            # Helper to extract basic string / amount data for LLM context
            def get_snak_value(snak):
                if snak.get('snaktype') == 'value':
                    datavalue = snak.get('datavalue', {})
                    if datavalue.get('type') == 'wikibase-entityid':
                        return datavalue.get('value', {}).get('id')
                    elif datavalue.get('type') == 'string':
                        return datavalue.get('value')
                    elif datavalue.get('type') == 'monolingualtext':
                        return datavalue.get('value', {}).get('text')
                    elif datavalue.get('type') == 'quantity':
                        return datavalue.get('value', {}).get('amount')
                return None

            def extract_claim_values(prop_id):
                vals = []
                for statement in best_claims.get(prop_id, []):
                    val = get_snak_value(statement.get('mainsnak', {}))
                    if val:
                        vals.append(val)
                return vals

            # Get some raw values for claims to present to LLM
            countries = extract_claim_values('P17')         # country
            hqs = extract_claim_values('P159')              # headquarters location
            industries = extract_claim_values('P452')       # industry
            websites = extract_claim_values('P856')         # official website(s)
            subsidiaries = extract_claim_values('P355')     # subsidiaries
            inception = extract_claim_values('P571')        # inception date
            owned_by = extract_claim_values('P127')         # owned by (parent/acquirer context)
            operating_areas = extract_claim_values('P159')  # areas served via HQ locations
            instance_of = extract_claim_values('P31')
            parent_org = extract_claim_values('P749')
            revenue_supplemental = extract_claim_values('P2139') # revenue supplemental

            raw_data = {
                "qid": best_qid,
                "countries_ids": countries,
                "headquarters_ids": hqs,
                "industry_ids": industries,
                "websites": websites,
                "subsidiaries_ids": subsidiaries,
                "inception": inception,
                "owned_by_ids": owned_by,
                "parent_org_ids": parent_org,
                "instance_of_ids": instance_of,
                "operating_area_ids": operating_areas,
                "revenue_supplemental": revenue_supplemental
            }
            
            logger.info(f"[Wikidata Collector] Fetched raw claims from Wikidata entity '{best_qid}': {json.dumps(raw_data)}")
            
            # Send raw details to LLM to parse and extract requested target fields
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "wikidata_text": json.dumps(raw_data)
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)
            
            findings = {k: extracted.get(k) for k in self.config.target_fields}
            logger.info(f"[Wikidata Collector] Mapped target fields: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.error(f"[Wikidata Collector] Collection failed: {e}\nTraceback:\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"{e}\nTraceback:\n{traceback.format_exc()}",
                "findings": {}
            }

class SECCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskAgent/1.0 (contact@example.com)'

    def _resolve_cik(self, company_name: str) -> tuple:
        """
        Resolve company name to (cik_str, matched_entity_name) using a 3-tier strategy:
        1. EDGAR full-text search API (efts.sec.gov) — works for private/mutual companies
        2. EDGAR company browse API (HTML-based, broader coverage)
        3. Fallback: company_tickers.json (public/ticker companies only)
        Returns (cik_padded, entity_name) or (None, None) if not found.
        """
        logger = self.get_logger()
        import re
        import difflib

        encoded = urllib.parse.quote(f'"{company_name}"')

        # --- Tier 1: EDGAR EFTS full-text search (handles private companies) ---
        try:
            search_url = f"https://efts.sec.gov/LATEST/search-index?q={encoded}&forms=10-K&hits.hits.total.value=true"
            logger.info(f"[SEC CIK Resolve] Tier 1 EFTS search URL: {search_url}")
            req = urllib.request.Request(search_url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_bytes = resp.read()
                logger.info(f"[SEC CIK Resolve] Tier 1 response received ({len(resp_bytes)} bytes)")
                data = json.loads(resp_bytes.decode())

            hits = data.get('hits', {}).get('hits', [])
            logger.info(f"[SEC CIK Resolve] Tier 1 hits resolved count: {len(hits)}")
            if hits:
                best_cik = None
                best_name = None
                best_score = 0.0
                for hit in hits[:10]:
                    src = hit.get('_source', {})
                    entity_name = src.get('entity_name', '')
                    acc_id = hit.get('_id', '')
                    raw_cik = acc_id.split('-')[0] if '-' in acc_id else acc_id[:10]
                    if not raw_cik.isdigit():
                        continue
                    score = difflib.SequenceMatcher(None, company_name.lower(), entity_name.lower()).ratio()
                    logger.info(f"[SEC CIK Resolve] Tier 1 matching entity '{entity_name}' CIK={raw_cik} Score={score:.2f}")
                    if score > best_score:
                        best_score = score
                        best_cik = raw_cik.zfill(10)
                        best_name = entity_name
                if best_cik and best_score > 0.4:
                    logger.info(f"[SEC CIK Resolve] Tier 1 Match Found: CIK={best_cik} Name='{best_name}' (Score={best_score:.2f})")
                    return best_cik, best_name
        except Exception as e:
            import traceback
            logger.warning(f"[SEC CIK Resolve] Tier 1 EFTS failed: {e}\n{traceback.format_exc()}")

        # --- Tier 2: EDGAR company browse API (wider net, parses XML atom feed) ---
        try:
            browse_name = urllib.parse.quote(company_name)
            browse_url = f"https://www.sec.gov/cgi-bin/browse-edgar?company={browse_name}&CIK=&type=10-K&dateb=&owner=include&count=10&search_text=&action=getcompany&output=atom"
            logger.info(f"[SEC CIK Resolve] Tier 2 browse URL: {browse_url}")
            req2 = urllib.request.Request(browse_url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req2, timeout=10) as resp2:
                xml_text = resp2.read().decode()
                logger.info(f"[SEC CIK Resolve] Tier 2 response size: {len(xml_text)} chars")

            cik_matches = re.findall(r'<CIK>(\d+)</CIK>', xml_text)
            name_matches = re.findall(r'<conformed-name>(.*?)</conformed-name>', xml_text, re.IGNORECASE)
            logger.info(f"[SEC CIK Resolve] Tier 2 resolved CIK matches: {cik_matches}, Name matches: {name_matches}")
            if cik_matches and name_matches:
                best_cik = None
                best_name = None
                best_score = 0.0
                for cik_val, nm in zip(cik_matches, name_matches):
                    score = difflib.SequenceMatcher(None, company_name.lower(), nm.lower()).ratio()
                    logger.info(f"[SEC CIK Resolve] Tier 2 matching candidate '{nm}' CIK={cik_val} Score={score:.2f}")
                    if score > best_score:
                        best_score = score
                        best_cik = str(cik_val).zfill(10)
                        best_name = nm
                if best_cik and best_score > 0.3:
                    logger.info(f"[SEC CIK Resolve] Tier 2 Match Found: CIK={best_cik} Name='{best_name}' (Score={best_score:.2f})")
                    return best_cik, best_name
        except Exception as e:
            import traceback
            logger.warning(f"[SEC CIK Resolve] Tier 2 browse failed: {e}\n{traceback.format_exc()}")

        # --- Tier 3: Fallback — company_tickers.json (public/ticker companies) ---
        try:
            tickers_url = "https://www.sec.gov/files/company_tickers.json"
            logger.info(f"[SEC CIK Resolve] Tier 3 query: {tickers_url}")
            req3 = urllib.request.Request(tickers_url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req3, timeout=10) as resp3:
                tickers_text = resp3.read().decode()
                tickers = json.loads(tickers_text)
            for _, data in tickers.items():
                if company_name.lower() in data['title'].lower():
                    logger.info(f"[SEC CIK Resolve] Tier 3 Match Found (ticker json): CIK={data['cik_str']} Name='{data['title']}'")
                    return str(data['cik_str']).zfill(10), data['title']
        except Exception as e:
            import traceback
            logger.warning(f"[SEC CIK Resolve] Tier 3 ticker lookup failed: {e}\n{traceback.format_exc()}")

        logger.info(f"[SEC CIK Resolve] CIK lookup failed across all tiers for '{company_name}'")
        return None, None

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        logger = self.get_logger()
        try:
            logger.info(f"[SEC EDGAR Collector] Starting data collection for '{company_name}' ({domain})")
            # 1. Resolve Company Name to CIK via multi-tier EDGAR name search
            cik, matched_name = self._resolve_cik(company_name)

            if not cik:
                logger.info(f"[SEC EDGAR Collector] Skipped: CIK could not be resolved for '{company_name}'")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": f"Company '{company_name}' not found in SEC EDGAR (tried EFTS search, browse API, and tickers list).",
                    "findings": {}
                }

            # 2. Fetch Company Facts
            facts_url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
            logger.info(f"[SEC EDGAR Collector] Requesting Company Facts URL: {facts_url}")
            req2 = urllib.request.Request(facts_url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req2, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[SEC EDGAR Collector] Facts API response size: {len(resp_bytes)} bytes")
                facts = json.loads(resp_bytes.decode())
                
            gaap = facts.get('facts', {}).get('us-gaap', {})
            logger.info(f"[SEC EDGAR Collector] Available us-gaap metrics count: {len(gaap)}")
            
            # Find the best revenue key (the one with the latest ending 10-K/annual filing)
            best_key = None
            best_latest_end = ""
            best_usd = []
            
            from datetime import datetime

            for rk in [
                # Standard commercial/tech
                'RevenueFromContractWithCustomerExcludingAssessedTax',
                'Revenues',
                'SalesRevenueNet',
                # Insurance-specific (Liberty Mutual, Travelers, etc.)
                'PremiumsEarned',
                'PremiumsWrittenNet',
                'NetPremiumsEarned',
                'InsurancePremiumsAndOtherRevenues',
                'PolicyholderBenefitsAndClaimsIncurredNet',
                # Financial services
                'InterestAndDividendIncomeOperating',
                'RevenuesExcludingInterestAndDividends',
                'NetIncomeLoss',
            ]:
                if rk in gaap:
                    units = gaap[rk].get('units', {})
                    usd = units.get('USD', [])
                    # Find if there are any valid annual entries and what their latest end date is
                    key_latest_end = ""
                    for u in usd:
                        if 'start' in u and 'end' in u and 'val' in u:
                            try:
                                start = datetime.strptime(u['start'], "%Y-%m-%d")
                                end = datetime.strptime(u['end'], "%Y-%m-%d")
                                days = (end - start).days
                                if 330 <= days <= 390:
                                    if u['end'] > key_latest_end:
                                        key_latest_end = u['end']
                            except Exception:
                                pass
                    # If this key has more recent annual data, pick it
                    if key_latest_end and (not best_latest_end or key_latest_end > best_latest_end):
                        best_latest_end = key_latest_end
                        best_key = rk
                        best_usd = usd

            logger.info(f"[SEC EDGAR Collector] Best GAAP revenue/premium key matched: '{best_key}' (latest end date: {best_latest_end})")

            revenue_val = None
            fiscal_year = None
            quarterly_revenue = []

            if best_key:
                annual_entries = []
                quarterly_entries = []
                for u in best_usd:
                    if 'start' not in u or 'end' not in u or 'val' not in u:
                        continue
                    try:
                        start = datetime.strptime(u['start'], "%Y-%m-%d")
                        end = datetime.strptime(u['end'], "%Y-%m-%d")
                        days = (end - start).days
                        if 330 <= days <= 390:
                            annual_entries.append(u)
                        elif 80 <= days <= 105:
                            quarterly_entries.append(u)
                    except Exception:
                        continue

                # 1. Extrapolate latest annual
                if annual_entries:
                    latest_annual = sorted(annual_entries, key=lambda x: (x.get('end', ''), x.get('filed', '')))[-1]
                    revenue_val = latest_annual['val']
                    try:
                        fiscal_year = int(latest_annual['end'].split('-')[0])
                    except Exception:
                        fiscal_year = latest_annual.get('fy')
                    logger.info(f"[SEC EDGAR Collector] Extracted annual revenue: {revenue_val} for fiscal year {fiscal_year}")

                # 2. Extrapolate quarterly revenues (sorted chronologically and deduplicated by end date)
                if quarterly_entries:
                    sorted_quarters = sorted(quarterly_entries, key=lambda x: (x.get('end', ''), x.get('filed', '')))
                    dedup_quarters = {}
                    for q in sorted_quarters:
                        dedup_quarters[q['end']] = q['val']
                    
                    chronological_ends = sorted(dedup_quarters.keys())
                    quarterly_revenue = [dedup_quarters[e] for e in chronological_ends]
                    logger.info(f"[SEC EDGAR Collector] Extracted quarterly revenues: {quarterly_revenue}")

            # Fetch submissions to count subsidiaries if Exhibit 21 is available
            subsidiaries_count = 0
            business_text = ""
            risk_text = ""
            mdna_text = ""
            segment_text = ""
            try:
                submissions_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
                logger.info(f"[SEC EDGAR Collector] Requesting submissions URL: {submissions_url}")
                req_sub = urllib.request.Request(submissions_url, headers={'User-Agent': self.USER_AGENT})
                with urllib.request.urlopen(req_sub, timeout=10) as res_sub:
                    resp_sub_bytes = res_sub.read()
                    logger.info(f"[SEC EDGAR Collector] Submissions response size: {len(resp_sub_bytes)} bytes")
                    sub_data = json.loads(resp_sub_bytes.decode())
                
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
                    logger.info(f"[SEC EDGAR Collector] Requesting index directory: {index_url}")
                    req_idx = urllib.request.Request(index_url, headers={'User-Agent': self.USER_AGENT})
                    with urllib.request.urlopen(req_idx, timeout=10) as res_idx:
                        idx = json.loads(res_idx.read().decode())
                        
                    ex21_file = None
                    primary_doc = None
                    for file_info in idx['directory']['item']:
                        name = file_info['name']
                        lower_name = name.lower()
                        if 'ex21' in lower_name or 'ex-21' in lower_name or 'exhibit21' in lower_name:
                            ex21_file = name
                        elif lower_name.endswith('.htm') and 'ex' not in lower_name and not primary_doc:
                            primary_doc = name
                    
                    subsidiaries_list = []
                    if ex21_file:
                        file_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodashes}/{ex21_file}"
                        logger.info(f"[SEC EDGAR Collector] Requesting Exhibit 21 URL: {file_url}")
                        req_file = urllib.request.Request(file_url, headers={'User-Agent': self.USER_AGENT})
                        with urllib.request.urlopen(req_file, timeout=10) as res_file:
                            html = res_file.read().decode('utf-8', errors='ignore')
                        
                        import re
                        rows = re.findall(r'<tr[^>]*>', html, re.IGNORECASE)
                        for row in re.findall(r'<tr[^>]*>.*?</tr>', html, re.DOTALL | re.IGNORECASE):
                            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
                            if cells:
                                cell_text = re.sub(r'<[^>]+>', ' ', cells[0])
                                cell_text = re.sub(r'\s+', ' ', cell_text).strip()
                                if cell_text and len(cell_text) > 2 and not any(k in cell_text.lower() for k in ["name of", "subsidiary", "jurisdiction", "state of", "percent", "ownership", "domestic"]):
                                    subsidiaries_list.append(cell_text)
                        
                        subsidiaries_count = len(subsidiaries_list)
                        if subsidiaries_count == 0:
                            subsidiaries_count = max(0, len(rows) - 1)
                        logger.info(f"[SEC EDGAR Collector] Counted {subsidiaries_count} subsidiaries in Exhibit 21.")

                    customer_text = ""
                    if primary_doc:
                        file_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_nodashes}/{primary_doc}"
                        logger.info(f"[SEC EDGAR Collector] Requesting primary 10-K filing URL: {file_url}")
                        req_file = urllib.request.Request(file_url, headers={'User-Agent': self.USER_AGENT})
                        with urllib.request.urlopen(req_file, timeout=10) as res_file:
                            html_10k = res_file.read().decode('utf-8', errors='ignore')
                            
                        import re
                        text_10k = re.sub(r'<[^>]+>', ' ', html_10k)
                        text_10k = re.sub(r'\s+', ' ', text_10k)
                        
                        m_bus = re.search(r'(?i)Item\s+1\.\s+Business\b(.*?)(?:Item\s+1A|Item\s+2)', text_10k)
                        if m_bus:
                            business_text = m_bus.group(1)[:4000]
                            logger.info(f"[SEC EDGAR Collector] Extracted Item 1 Business ({len(business_text)} chars)")
                            
                            # Scan business section for customer segments
                            m_cust = re.findall(r'(?i)([^.]{10,200}\b(?:customer|consumer|client|subscriber|retail|enterprise|b2b|b2c)\b[^.]{10,200}\.)', business_text)
                            customer_text = " ".join(m_cust[:10]) if m_cust else ""
                        
                        m_risk = re.search(r'(?i)Item\s+1A\.\s+Risk Factors\b(.*?)(?:Item\s+1B|Item\s+2)', text_10k)
                        if m_risk:
                            risk_text = m_risk.group(1)[:4000]
                            logger.info(f"[SEC EDGAR Collector] Extracted Item 1A Risk Factors ({len(risk_text)} chars)")
                        
                        m_mdna = re.search(r'(?i)Item\s+7\.\s+Management\'s Discussion(.*?)(?:Item\s+7A|Item\s+8)', text_10k)
                        if m_mdna:
                            mdna_text = m_mdna.group(1)[:4000]
                            logger.info(f"[SEC EDGAR Collector] Extracted Item 7 MD&A ({len(mdna_text)} chars)")
                        
                        m_seg = re.search(r'(?i)(?:Segment Reporting|Reportable Segments)(.{0,2000})', text_10k)
                        if m_seg:
                            segment_text = m_seg.group(1)
                            logger.info(f"[SEC EDGAR Collector] Extracted Segment Reporting indicator text ({len(segment_text)} chars)")
            except Exception as e:
                import traceback
                logger.error(f"[SEC EDGAR Collector] Submissions or 10-K text extraction failed: {e}\n{traceback.format_exc()}")

            acquisitions_mentions = []
            try:
                efts_search_url = f"https://efts.sec.gov/LATEST/search-index?q=acquisition%20OR%20merger%20OR%20acquired&ciks={cik}&hits.hits.total.value=true"
                logger.info(f"[SEC EDGAR Collector] Requesting EFTS acquisitions search URL: {efts_search_url}")
                req_efts = urllib.request.Request(efts_search_url, headers={'User-Agent': self.USER_AGENT})
                with urllib.request.urlopen(req_efts, timeout=10) as resp_efts:
                    resp_efts_bytes = resp_efts.read()
                    logger.info(f"[SEC EDGAR Collector] EFTS search response received ({len(resp_efts_bytes)} bytes)")
                    efts_data = json.loads(resp_efts_bytes.decode())
                    
                hits = efts_data.get('hits', {}).get('hits', [])
                for hit in hits[:10]:
                    src = hit.get('_source', {})
                    file_desc = src.get('file_description', '')
                    highlights = hit.get('highlight', {}).get('extxt', [])
                    hl_text = " ".join(highlights) if highlights else ""
                    desc = f"{file_desc} (Highlights: {hl_text})" if hl_text else file_desc
                    if desc:
                        acquisitions_mentions.append(desc)
                logger.info(f"[SEC EDGAR Collector] Found {len(acquisitions_mentions)} recent acquisition mentions in EFTS.")
            except Exception as e:
                logger.warning(f"[SEC EDGAR Collector] EFTS acquisitions search failed: {e}")

            raw_sec_context = {
                "cik": cik,
                "matched_entity_name": matched_name,
                "raw_annual_revenue": revenue_val,
                "fiscal_year": fiscal_year,
                "exhibit21_subsidiaries_count": subsidiaries_count,
                "exhibit21_subsidiaries_list": subsidiaries_list,
                "acquisitions_mentions": acquisitions_mentions,
                "customer_segments_mentions": customer_text,
                "quarterly_revenue": quarterly_revenue,
                "business_section": business_text,
                "risk_factors_section": risk_text,
                "mda_section": mdna_text,
                "segment_reporting": segment_text
            }

            # Call LLM to parse and extract target fields
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "sec_text": json.dumps(raw_sec_context)
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)
            
            findings = {k: extracted.get(k) for k in self.config.target_fields}
            findings["quarterly_revenue"] = quarterly_revenue
            logger.info(f"[SEC EDGAR Collector] Target mapped findings: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.error(f"[SEC EDGAR Collector] Collection failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"{e}\nTraceback:\n{traceback.format_exc()}",
                "findings": {}
            }

class DNBCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        logger = self.get_logger()
        query = urllib.parse.quote(company_name)
        url = f"https://api.gleif.org/api/v1/fuzzycompletions?field=entity.legalName&q={query}"
        logger.info(f"[GLEIF DNB Collector] Resolving legal entity fuzzy completion URL: {url}")
        
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=5) as response:
                resp_bytes = response.read()
                logger.info(f"[GLEIF DNB Collector] Received response size: {len(resp_bytes)} bytes")
                data = json.loads(resp_bytes.decode())
                
            if data.get("data") and len(data["data"]) > 0:
                match_id = data["data"][0].get("id")
                lei = match_id
                entity = data["data"][0].get("attributes", {}).get("entity", {})
                if entity.get("lei"):
                    lei = entity.get("lei")
                
                logger.info(f"[GLEIF DNB Collector] Matched fuzzy completion ID: {match_id}, LEI: {lei}")
                
                full_entity_data = {}
                try:
                    record_url = f"https://api.gleif.org/api/v1/lei-records/{lei}"
                    logger.info(f"[GLEIF DNB Collector] Requesting full record URL: {record_url}")
                    req_record = urllib.request.Request(record_url, headers={'Accept': 'application/json', 'User-Agent': self.USER_AGENT})
                    with urllib.request.urlopen(req_record, timeout=8) as response_record:
                        record_bytes = response_record.read()
                        record_json = json.loads(record_bytes.decode())
                        
                    full_entity_data = record_json.get("data", {})
                    logger.info(f"[GLEIF DNB Collector] Successfully fetched full LEI record for {lei}")
                except Exception as ex:
                    logger.warning(f"[GLEIF DNB Collector] Failed to fetch full LEI record: {ex}. Falling back to fuzzy data.")
                    full_entity_data = data["data"][0]

                attributes = full_entity_data.get("attributes", {})
                entity_details = attributes.get("entity", entity)
                legal_address = attributes.get("legalAddress", {})
                hq_address = attributes.get("headquartersAddress", {})
                relationships = full_entity_data.get("relationships", {})
                
                combined_context = {
                    "lei": lei,
                    "entity": entity_details,
                    "legal_address": legal_address,
                    "headquarters_address": hq_address,
                    "relationships": relationships,
                    "registration": attributes.get("registration", {})
                }
                
                # Pass GLEIF raw structure to LLM
                prompt_vars = {
                    "company_name": company_name,
                    "domain": domain,
                    "dnb_text": json.dumps(combined_context)
                }
                prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
                response_text = self.call_llm(prompt)
                extracted = self.parse_json(response_text)
                
                findings = {k: extracted.get(k) for k in self.config.target_fields}
                logger.info(f"[GLEIF DNB Collector] Mapped target fields: {findings}")
                return {
                    "source": self.config.source_name,
                    "status": "success",
                    "findings": findings
                }
            else:
                logger.info(f"[GLEIF DNB Collector] No company matches resolved in GLEIF index for query '{company_name}'")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "No company legal entity matched in GLEIF registration database.",
                    "findings": {}
                }
        except Exception as e:
            import traceback
            logger.error(f"[GLEIF DNB Collector] Collection failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"{e}\nTraceback:\n{traceback.format_exc()}",
                "findings": {}
            }

class DomainScraperCollectorAgent(BaseCollectorAgent):

    def _check_ssl(self, domain_str: str) -> bool:
        import ssl
        import socket
        try:
            context = ssl.create_default_context()
            with socket.create_connection((domain_str, 443), timeout=3) as sock:
                with context.wrap_socket(sock, server_hostname=domain_str) as ssock:
                    ssock.getpeercert()
                    return True
        except Exception:
            return False

    def _is_reachable(self, domain_str: str) -> bool:
        import socket
        try:
            socket.gethostbyname(domain_str)
            return True
        except Exception:
            return False

    def _crtsh_discover(self, domain_str: str) -> set:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        subdomains = set()
        try:
            query_url = f"https://crt.sh/?q={urllib.parse.quote(domain_str)}&output=json"
            req = urllib.request.Request(query_url, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                data = json.loads(response.read().decode('utf-8'))
                for entry in data:
                    name_value = entry.get("name_value", "")
                    for name in name_value.split("\n"):
                        name = name.strip().lower()
                        if name.startswith("*."):
                            name = name[2:]
                        if name:
                            subdomains.add(name)
        except Exception as e:
            logger.info(f"[Domain Scraper Collector] crt.sh query failed for {domain_str}: {e}")
        return subdomains

    def _scrape_domain(self, host: str, ssl_valid: bool) -> tuple[str, bool]:
        import urllib.request
        import re
        protocol = "https" if ssl_valid else "http"
        url = f"{protocol}://{host}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            with urllib.request.urlopen(req, timeout=4) as response:
                page_bytes = response.read()
                page_html = page_bytes.decode('utf-8', errors='ignore')
                cleaned = re.sub(r'<style.*?>.*?</style>', ' ', page_html, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<script.*?>.*?</script>', ' ', cleaned, flags=re.DOTALL | re.IGNORECASE)
                cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
                cleaned = re.sub(r'\s+', ' ', cleaned)
                return cleaned, True
        except Exception:
            return "", False

    async def collect(self, company_name: str, domain: str, discovered_domains: list = None) -> Dict[str, Any]:
        import re
        import asyncio
        logger = self.get_logger()
        logger.info(f"[Domain Scraper Collector] Starting recursive collection for '{company_name}' on domain '{domain}' (input discovered domains: {discovered_domains})")

        # 1. Brand Keywords Extraction
        words = re.findall(r'[a-zA-Z0-9]+', company_name.lower())
        ignored_suffixes = {"inc", "corp", "corporation", "ltd", "limited", "co", "llc", "group", "pc", "intl", "international", "incorporated", "llp", "company", "plc"}
        brand_keywords = [w for w in words if w not in ignored_suffixes and len(w) > 2]
        if not brand_keywords:
            brand_keywords = [w for w in words if len(w) > 1]
            
        logger.info(f"[Domain Scraper Collector] Brand keywords: {brand_keywords}")

        # Clean and extract root hostnames from input discovered_domains
        discovered_set = set()
        if discovered_domains:
            from urllib.parse import urlparse
            for d_url in discovered_domains:
                try:
                    parsed = urlparse(d_url if d_url.startswith("http") else f"https://{d_url}")
                    host = parsed.hostname or ""
                    host = re.sub(r'^www\.', '', host.lower()).strip()
                    if host:
                        discovered_set.add(host)
                except Exception:
                    pass
            logger.info(f"[Domain Scraper Collector] Normalized discovered domains: {list(discovered_set)}")


        # 2. Helpers for SSL, crt.sh query, and URL fetching
        async def check_ssl(domain_str: str) -> bool:
            return await asyncio.to_thread(self._check_ssl, domain_str)

        async def discover_crtsh(domain_str: str) -> set:
            return await asyncio.to_thread(self._crtsh_discover, domain_str)

        async def scrape_url(url_str: str) -> tuple[str, set[str]]:
            def blocking_fetch():
                text = ""
                links = set()
                try:
                    req = urllib.request.Request(url_str, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
                    with urllib.request.urlopen(req, timeout=4) as response:
                        page_bytes = response.read()
                        page_html = page_bytes.decode('utf-8', errors='ignore')
                        
                        # Extract absolute domains from link tags
                        found_domains = re.findall(r'https?://([a-zA-Z0-9.-]+)', page_html)
                        for d in found_domains:
                            d = d.lower()
                            if d.startswith("www."):
                                d = d[4:]
                            if d:
                                links.add(d)

                        # Clean HTML tags and scripts
                        cleaned = re.sub(r'<style.*?>.*?</style>', ' ', page_html, flags=re.DOTALL | re.IGNORECASE)
                        cleaned = re.sub(r'<script.*?>.*?</script>', ' ', cleaned, flags=re.DOTALL | re.IGNORECASE)
                        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
                        cleaned = re.sub(r'\s+', ' ', cleaned)
                        text = cleaned
                except Exception as e:
                    logger.info(f"[Domain Scraper Collector] Fetch failed for {url_str}: {e}")
                return text, links
            return await asyncio.to_thread(blocking_fetch)

        # 3. Filtering Helper
        def is_valid_domain(candidate: str) -> bool:
            candidate = candidate.lower()
            # Rule A: Subdomain of primary domain
            if candidate == domain.lower() or candidate.endswith("." + domain.lower()):
                return True
            # Rule B: Alternate domain matching brand keywords
            for keyword in brand_keywords:
                if keyword in candidate:
                    return True
            return False

        discovered_domains = {domain.lower()}
        crawled_domains = set()
        domain_ssl_status = {}

        # Stage 1: SSL Check and Page Crawl for Primary Domain + crt.sh Discovery
        primary_ssl = await check_ssl(domain)
        domain_ssl_status[domain.lower()] = primary_ssl

        protocol = "https" if primary_ssl else "http"
        primary_paths = [
            "", "/about", "/services", "/solutions", "/products", "/platform",
            "/privacy", "/privacy-policy", "/terms", "/terms-of-service"
        ]
        primary_urls = [f"{protocol}://{domain.lower()}{p}" for p in primary_paths]

        logger.info(f"[Domain Scraper Collector] Stage 1: Scraping primary domain and querying crt.sh...")
        stage1_tasks = [scrape_url(url) for url in primary_urls]
        stage1_tasks.append(discover_crtsh(domain))

        stage1_results = await asyncio.gather(*stage1_tasks)

        primary_pages_results = stage1_results[:-1]
        crtsh_subdomains = stage1_results[-1]

        merged_text = ""
        seen_lines = set()
        all_discovered_links = set(crtsh_subdomains)
        if discovered_set:
            all_discovered_links.update(discovered_set)

        compliance_matches = set()
        for text, links in primary_pages_results:
            all_discovered_links.update(links)
            if text:
                for framework in ["GDPR", "CCPA", "HIPAA", "COPPA", "SOC 2", "SOC2", "PCI-DSS", "FERPA"]:
                    if framework.lower() in text.lower():
                        compliance_matches.add(framework)
                chunks = text.split('.')
                for c in chunks:
                    c = c.strip()
                    if len(c) > 15 and c not in seen_lines:
                        seen_lines.add(c)
                        merged_text += c + ". "

        crawled_domains.add(domain.lower())

        # Stage 2: Filter and Limit Discovered Subdomains / Alternate Domains
        candidates = [link for link in all_discovered_links if link not in crawled_domains and is_valid_domain(link)]
        # Cap to a maximum of 11 additional domains (making it 12 total)
        candidates = candidates[:11]

        logger.info(f"[Domain Scraper Collector] Discovered valid domain candidates: {candidates}")

        if candidates:
            # Perform parallel SSL checks
            ssl_checks = await asyncio.gather(*[check_ssl(cand) for cand in candidates])
            for cand, ssl_ok in zip(candidates, ssl_checks):
                domain_ssl_status[cand] = ssl_ok
                discovered_domains.add(cand)

            # Build URLs (crawling "/" and "/about" for each candidate)
            cand_urls = []
            for cand in candidates:
                proto = "https" if domain_ssl_status[cand] else "http"
                cand_urls.append((cand, f"{proto}://{cand}"))
                cand_urls.append((cand, f"{proto}://{cand}/about"))

            logger.info(f"[Domain Scraper Collector] Stage 2: Crawling candidate pages in parallel...")
            cand_scrape_results = await asyncio.gather(*[scrape_url(url) for _, url in cand_urls])

            for (_, url), (text, links) in zip(cand_urls, cand_scrape_results):
                if text:
                    for framework in ["GDPR", "CCPA", "HIPAA", "COPPA", "SOC 2", "SOC2", "PCI-DSS", "FERPA"]:
                        if framework.lower() in text.lower():
                            compliance_matches.add(framework)
                    chunks = text.split('.')
                    for c in chunks:
                        c = c.strip()
                        if len(c) > 15 and c not in seen_lines:
                            seen_lines.add(c)
                            merged_text += c + ". "

        # Stage 3: Construct context and call LLM
        domain_objects = [{"url": d, "https_encrypted": domain_ssl_status.get(d, False)} for d in discovered_domains]
        merged_text = merged_text[:15000]

        # --- A. Mozilla Observatory API ---
        mozilla_grade = None
        try:
            obs_url = f"https://http-observatory.security.mozilla.org/api/v1/analyze?host={domain}"
            logger.info(f"[Domain Scraper - Observatory] Fetching Observatory grade for '{domain}'")
            req_obs = urllib.request.Request(obs_url, method='POST', headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            try:
                with urllib.request.urlopen(req_obs, timeout=6) as resp_obs:
                    obs_data = json.loads(resp_obs.read().decode())
            except Exception:
                req_obs_get = urllib.request.Request(obs_url, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
                with urllib.request.urlopen(req_obs_get, timeout=6) as resp_obs:
                    obs_data = json.loads(resp_obs.read().decode())
            mozilla_grade = obs_data.get("grade")
            logger.info(f"[Domain Scraper - Observatory] Observatory Grade for {domain}: {mozilla_grade}")
        except Exception as obs_err:
            logger.warning(f"[Domain Scraper - Observatory] Observatory lookup failed: {obs_err}")

        # --- B. ToS;DR API ---
        tosdr_grade = None
        try:
            tosdr_url = f"https://api.tosdr.org/service/v2/?name={domain}"
            logger.info(f"[Domain Scraper - ToS;DR] Fetching privacy rating for '{domain}'")
            req_tosdr = urllib.request.Request(tosdr_url, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            with urllib.request.urlopen(req_tosdr, timeout=6) as resp_tosdr:
                tosdr_data = json.loads(resp_tosdr.read().decode())
            services = tosdr_data.get("parameters", {}).get("services", [])
            if services:
                tosdr_grade = services[0].get("tosdr", {}).get("grade")
            logger.info(f"[Domain Scraper - ToS;DR] ToS;DR Privacy Grade for {domain}: {tosdr_grade}")
        except Exception as tosdr_err:
            logger.warning(f"[Domain Scraper - ToS;DR] ToS;DR lookup failed: {tosdr_err}")

        # --- C. RDAP Domain Lookup ---
        creation_date = None
        expiration_date = None
        registrar = None
        try:
            rdap_url = f"https://rdap.org/domain/{domain}"
            logger.info(f"[Domain Scraper - RDAP] Fetching domain registration dates for '{domain}'")
            req_rdap = urllib.request.Request(rdap_url, headers={'Accept': 'application/json', 'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            with urllib.request.urlopen(req_rdap, timeout=6) as resp_rdap:
                rdap_data = json.loads(resp_rdap.read().decode())
            events = rdap_data.get("events", [])
            for event in events:
                action = event.get("eventAction")
                date_str = event.get("eventDate")
                if action == "registration" and date_str:
                    creation_date = date_str.split('T')[0]
                elif action == "expiration" and date_str:
                    expiration_date = date_str.split('T')[0]
            entities = rdap_data.get("entities", [])
            for entity in entities:
                roles = entity.get("roles", [])
                if "registrar" in roles:
                    registrar = entity.get("handle") or entity.get("fn")
                    vcard = entity.get("vcardArray", [])
                    if len(vcard) > 1:
                        for entry in vcard[1]:
                            if entry[0] == "fn":
                                registrar = entry[3]
            logger.info(f"[Domain Scraper - RDAP] RDAP Creation Date: {creation_date}, Expiration: {expiration_date}, Registrar: {registrar}")
        except Exception as rdap_err:
            logger.warning(f"[Domain Scraper - RDAP] RDAP lookup failed: {rdap_err}")

        raw_context = {
            "url": domain,
            "https_encrypted": primary_ssl,
            "discovered_domains": domain_objects,
            "homepage_html_snippet": merged_text,
            "compliance_frameworks": list(compliance_matches),
            "mozilla_observatory_grade": mozilla_grade,
            "tosdr_privacy_grade": tosdr_grade,
            "domain_creation_date": creation_date,
            "domain_expiration_date": expiration_date,
            "domain_registrar": registrar
        }

        try:
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "scraper_text": json.dumps(raw_context)
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)

            findings = {k: extracted.get(k) for k in self.config.target_fields}

            # Hard override verified domains list
            if "domains" in findings:
                findings["domains"] = domain_objects

            logger.info(f"[Domain Scraper Collector] Mapped findings: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.error(f"[Domain Scraper Collector] Collection failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"{e}\nTraceback:\n{traceback.format_exc()}",
                "findings": {
                    "domains": domain_objects
                }
            }


class ResponsesAPICollectorAgent(BaseCollectorAgent):

    def _query_tavily(self, query: str, api_key: str) -> dict:
        import urllib.request
        import json
        logger = self.get_logger()
        try:
            url = "https://api.tavily.com/search"
            payload = json.dumps({
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "include_answer": False
            }).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=payload,
                headers={'Content-Type': 'application/json', 'User-Agent': 'CyberRiskInsurancePOC/1.0'}
            )
            logger.info(f"[Responses API Collector - Tavily] Requesting URL: {url}")
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[Responses API Collector - Tavily] Received search response ({len(resp_bytes)} bytes)")
                return json.loads(resp_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"[Responses API Collector - Tavily] Fetch failed for '{query}': {e}")
            return {}

    def _query_brave(self, query: str, api_key: str) -> dict:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        try:
            q = urllib.parse.quote(query)
            url = f"https://api.search.brave.com/res/v1/web/search?q={q}"
            req = urllib.request.Request(
                url,
                headers={
                    'X-Subscription-Token': api_key,
                    'Accept': 'application/json',
                    'User-Agent': 'CyberRiskInsurancePOC/1.0'
                }
            )
            logger.info(f"[Responses API Collector - Brave] Requesting URL: {url}")
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[Responses API Collector - Brave] Received search response ({len(resp_bytes)} bytes)")
                return json.loads(resp_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"[Responses API Collector - Brave] Fetch failed for '{query}': {e}")
            return {}

    def _search_google(self, query: str, api_key: str) -> dict:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        try:
            q = urllib.parse.quote(query)
            url = f"https://serpapi.com/search.json?q={q}&api_key={api_key}&engine=google"
            logger.info(f"[Responses API Collector] Requesting URL: {url.split('api_key=')[0]}api_key=...")
            req = urllib.request.Request(url, headers={'User-Agent': 'CyberRiskInsurancePOC/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[Responses API Collector] Received search response ({len(resp_bytes)} bytes)")
                return json.loads(resp_bytes.decode('utf-8'))
        except Exception as e:
            logger.error(f"[Responses API Collector] SerpAPI fetch failed for '{query}': {e}")
            return {}

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import asyncio
        logger = self.get_logger()
        
        tavily_key = os.environ.get("TAVILY_API_KEY")
        brave_key = os.environ.get("BRAVE_SEARCH_API_KEY")
        serpapi_key = os.environ.get("SERPAPI_API_KEY")
        
        # Support ENABLE_RESPONSES_API flag for tests/backwards compatibility
        enable_flag = os.environ.get("ENABLE_RESPONSES_API", "false").lower() == "true"
        
        if not tavily_key and not brave_key and not serpapi_key and not enable_flag:
            logger.warning("[Responses API Collector] No Search API keys are configured (Tavily, Brave, or SerpAPI). Skipping collection.")
            return {
                "source": self.config.source_name,
                "status": "skipped",
                "message": "No search API key configured.",
                "findings": {}
            }

        # Fallback dummy API key for testing if ENABLE_RESPONSES_API is true but key is missing
        if not tavily_key and not brave_key and not serpapi_key:
            tavily_key = "test_key_dummy"

        logger.info(f"[Responses API Collector] Starting searches for '{company_name}'")
        queries = [
            f"{company_name} official website domains",
            f"{company_name} annual revenue acquisitions"
        ]

        # Query
        results = []
        search_engine_used = "SerpAPI"
        if tavily_key:
            search_engine_used = "Tavily"
            results = await asyncio.gather(*[asyncio.to_thread(self._query_tavily, q, tavily_key) for q in queries])
        elif brave_key:
            search_engine_used = "Brave"
            results = await asyncio.gather(*[asyncio.to_thread(self._query_brave, q, brave_key) for q in queries])
        else:
            search_engine_used = "SerpAPI"
            results = await asyncio.gather(*[asyncio.to_thread(self._search_google, q, serpapi_key) for q in queries])

        # Parse and format search results context
        search_text_parts = []
        for i, res in enumerate(results):
            query_used = queries[i]
            search_text_parts.append(f"=== Search Query ({search_engine_used}): {query_used} ===")
            
            if search_engine_used == "Tavily":
                items = res.get("results", [])
                if not items:
                    search_text_parts.append("No results found.")
                for rank, item in enumerate(items[:5], 1):
                    title = item.get("title", "")
                    link = item.get("url", "")
                    snippet = item.get("content", "")
                    search_text_parts.append(f"{rank}. {title}\n   Link: {link}\n   Snippet: {snippet}")
            elif search_engine_used == "Brave":
                items = res.get("web", {}).get("results", [])
                if not items:
                    search_text_parts.append("No results found.")
                for rank, item in enumerate(items[:5], 1):
                    title = item.get("title", "")
                    link = item.get("url", "")
                    snippet = item.get("description", "")
                    search_text_parts.append(f"{rank}. {title}\n   Link: {link}\n   Snippet: {snippet}")
            else: # SerpAPI
                answer_box = res.get("answer_box", {})
                if answer_box:
                    search_text_parts.append(f"Answer Box: {json.dumps(answer_box)}")
                kg = res.get("knowledge_graph", {})
                if kg:
                    search_text_parts.append(f"Knowledge Graph: {json.dumps(kg)}")
                organic = res.get("organic_results", [])
                if not organic and not answer_box and not kg:
                    search_text_parts.append("No results found.")
                for rank, item in enumerate(organic[:5], 1):
                    title = item.get("title", "")
                    link = item.get("link", "")
                    snippet = item.get("snippet", "")
                    search_text_parts.append(f"{rank}. {title}\n   Link: {link}\n   Snippet: {snippet}")
            search_text_parts.append("")

        combined_search_text = "\n".join(search_text_parts)
        logger.info(f"[Responses API Collector] Combined search results context prepared (length: {len(combined_search_text)} characters)")

        try:
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "search_text": combined_search_text
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)

            findings = {k: extracted.get(k) for k in self.config.target_fields}
            logger.info(f"[Responses API Collector] Extracted findings: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.error(f"[Responses API Collector] LLM extraction failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": f"LLM extraction failed: {e}\n{traceback.format_exc()}",
                "findings": {}
            }

class OpenCorporatesCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        token = os.environ.get("OPENCORPORATES_API_KEY")
        
        query = urllib.parse.quote(company_name)
        url = f"https://api.opencorporates.com/v0.4/companies/search?q={query}"
        if token:
            url += f"&api_token={token}"
            logger.debug(f"[OpenCorporates Collector] API token present (using authenticated request)")
        else:
            logger.debug(f"[OpenCorporates Collector] No API token set (unauthenticated, rate-limited)")
            
        logger.info(f"[OpenCorporates Collector] Requesting URL: {url.split('api_token=')[0]}")
        try:
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=8) as response:
                resp_bytes = response.read()
                logger.info(f"[OpenCorporates Collector] Received response ({len(resp_bytes)} bytes, status={response.status})")
                data = json.loads(resp_bytes.decode('utf-8'))
                
            companies = data.get("results", {}).get("companies", [])
            logger.info(f"[OpenCorporates Collector] Companies returned in result set: {len(companies)}")
            if companies:
                company = companies[0].get("company", {})
                logger.info(f"[OpenCorporates Collector] Matched company: '{company.get('name')}' | Jurisdiction: {company.get('jurisdiction_code')} | Status: {company.get('current_status')} | Number: {company.get('company_number')}")
                logger.debug(f"[OpenCorporates Collector] Full company record: {json.dumps(company)}")
                
                prompt_vars = {
                    "company_name": company_name,
                    "domain": domain,
                    "opencorporates_text": json.dumps(company)
                }
                prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
                response_text = self.call_llm(prompt)
                extracted = self.parse_json(response_text)
                findings = {k: extracted.get(k) for k in self.config.target_fields}
                logger.info(f"[OpenCorporates Collector] Mapped target fields: {findings}")
                return {
                    "source": self.config.source_name,
                    "status": "success",
                    "findings": findings
                }
            else:
                logger.info(f"[OpenCorporates Collector] No results found for query '{company_name}'")
                return {
                    "source": self.config.source_name,
                    "status": "skipped",
                    "message": "No registry match found.",
                    "findings": {}
                }
        except Exception as e:
            import traceback
            logger.warning(f"[OpenCorporates Collector] OpenCorporates search failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }

class GDELTCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        
        query_str = f'"{company_name}" (cybersecurity OR breach OR lawsuit OR fine)'
        query = urllib.parse.quote(query_str)
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={query}&mode=artlist&maxrecords=10&format=json&timespan=1M"
        logger.info(f"[GDELT Event Monitor] Requesting news URL: {url}")
        logger.info(f"[GDELT Event Monitor] Search query: {query_str}")
        
        try:
            req = urllib.request.Request(url, headers={'User-Agent': self.USER_AGENT})
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[GDELT Event Monitor] Received response ({len(resp_bytes)} bytes, status={response.status})")
                data = json.loads(resp_bytes.decode('utf-8'))
                
            articles = data.get("articles", [])
            logger.info(f"[GDELT Event Monitor] Found {len(articles)} matching articles.")
            for i, art in enumerate(articles[:5], 1):
                logger.info(f"[GDELT Event Monitor]   [{i}] Title: '{art.get('title', '')}' | Source: {art.get('domain', '')} | Date: {art.get('seendate', '')}")
            
            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "gdelt_text": json.dumps(articles)
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)
            findings = {k: extracted.get(k) for k in self.config.target_fields}
            logger.info(f"[GDELT Event Monitor] Mapped target fields: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.warning(f"[GDELT Event Monitor] GDELT query failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }

class CourtListenerCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import urllib.request
        import urllib.parse
        import json
        logger = self.get_logger()
        token = os.environ.get("COURTLISTENER_API_KEY")

        if not token:
            logger.info("[CourtListener Collector] No API key configured, skipping.")
            return {
                "source": self.config.source_name,
                "status": "skipped",
                "message": "COURTLISTENER_API_KEY not set.",
                "findings": {}
            }

        query = urllib.parse.quote(company_name)
        url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}&type=r&order_by=score+desc&page_size=5"
        logger.info(f"[CourtListener Collector] Requesting URL: {url}")

        try:
            req = urllib.request.Request(url, headers={
                'Authorization': f'Token {token}',
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_bytes = response.read()
                logger.info(f"[CourtListener Collector] Received response ({len(resp_bytes)} bytes, status={response.status})")
                data = json.loads(resp_bytes.decode('utf-8'))

            results = data.get("results", [])
            logger.info(f"[CourtListener Collector] Found {len(results)} docket results.")
            for i, res in enumerate(results[:5], 1):
                case_name = res.get('case_name', res.get('caseName', '?'))
                court = res.get('court', res.get('court_id', '?'))
                date_filed = res.get('date_filed', res.get('dateFiled', '?'))
                logger.info(f"[CourtListener Collector]   [{i}] Case: '{case_name}' | Court: {court} | Filed: {date_filed}")

            prompt_vars = {
                "company_name": company_name,
                "domain": domain,
                "courtlistener_text": json.dumps(results[:5])
            }
            prompt = self.format_prompt(self.config.prompt_template, **prompt_vars)
            response_text = self.call_llm(prompt)
            extracted = self.parse_json(response_text)
            findings = {k: extracted.get(k) for k in self.config.target_fields}
            logger.info(f"[CourtListener Collector] Mapped target fields: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.warning(f"[CourtListener Collector] CourtListener search failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }


class SSLLabsCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import urllib.request
        import json
        import time
        logger = self.get_logger()

        url = f"https://api.ssllabs.com/api/v3/analyze?host={domain}&fromCache=on&maxAge=72"
        logger.info(f"[SSL Labs Collector] Requesting URL: {url}")

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req, timeout=15) as response:
                resp_bytes = response.read()
                data = json.loads(resp_bytes.decode('utf-8'))

            status = data.get("status", "UNKNOWN")
            logger.info(f"[SSL Labs Collector] Analysis status: {status}")

            # If still processing, wait briefly and retry once
            if status in ("DNS", "IN_PROGRESS"):
                logger.info("[SSL Labs Collector] Analysis in progress, waiting 10s for cached result...")
                time.sleep(10)
                with urllib.request.urlopen(req, timeout=15) as response:
                    resp_bytes = response.read()
                    data = json.loads(resp_bytes.decode('utf-8'))

            endpoints = data.get("endpoints", [])
            grade = endpoints[0].get("grade", "Unknown") if endpoints else "Unknown"
            logger.info(f"[SSL Labs Collector] SSL Grade: {grade}")

            findings = {
                "ssl_grade": grade,
                "ssl_details": {
                    "status": data.get("status"),
                    "protocol": data.get("protocol"),
                    "endpoints_count": len(endpoints)
                }
            }
            # Map to target fields
            findings = {k: findings.get(k) for k in self.config.target_fields}
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            logger.warning(f"[SSL Labs Collector] SSL Labs scan failed: {e}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }


class FTCFeedCollectorAgent(BaseCollectorAgent):
    USER_AGENT = 'CyberRiskInsurancePOC/1.0 (https://github.com/ShivamModi09/CyberRiskInsurance)'

    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        import urllib.request
        import xml.etree.ElementTree as ET
        logger = self.get_logger()

        url = "https://www.ftc.gov/feeds/press-releases.xml"
        logger.info(f"[FTC Feed Collector] Fetching FTC RSS feed: {url}")

        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': self.USER_AGENT,
                'Accept': 'application/xml'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_bytes = response.read()
                logger.info(f"[FTC Feed Collector] Received feed ({len(xml_bytes)} bytes)")

            root = ET.fromstring(xml_bytes.decode('utf-8'))
            # RSS feed structure: <rss><channel><item>...</item></channel></rss>
            items = root.findall('.//item')
            logger.info(f"[FTC Feed Collector] Total RSS items: {len(items)}")

            company_lower = company_name.lower()
            matches = []
            for item in items:
                title = item.findtext('title', '') or ''
                description = item.findtext('description', '') or ''
                link = item.findtext('link', '') or ''
                pub_date = item.findtext('pubDate', '') or ''

                if company_lower in title.lower() or company_lower in description.lower():
                    matches.append({
                        "title": title,
                        "link": link,
                        "date": pub_date,
                        "snippet": description[:300]
                    })

            logger.info(f"[FTC Feed Collector] Matched {len(matches)} FTC actions for '{company_name}'.")
            for i, m in enumerate(matches[:5], 1):
                logger.info(f"[FTC Feed Collector]   [{i}] Title: '{m['title']}' | Date: {m['date']} | Link: {m['link']}")

            findings = {
                "ftc_actions_count": len(matches),
                "ftc_actions": matches[:5]
            }
            findings = {k: findings.get(k) for k in self.config.target_fields}
            logger.info(f"[FTC Feed Collector] Mapped target fields: {findings}")
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            import traceback
            logger.warning(f"[FTC Feed Collector] FTC feed fetch failed: {e}\n{traceback.format_exc()}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }


class WappalyzerCollectorAgent(BaseCollectorAgent):
    async def collect(self, company_name: str, domain: str, **kwargs) -> Dict[str, Any]:
        logger = self.get_logger()
        logger.info(f"[Wappalyzer Collector] Analyzing tech stack for domain: {domain}")

        try:
            from Wappalyzer import Wappalyzer, WebPage
        except ImportError:
            logger.warning("[Wappalyzer Collector] python-Wappalyzer not installed, skipping.")
            return {
                "source": self.config.source_name,
                "status": "skipped",
                "message": "python-Wappalyzer not installed. Run: pip install python-Wappalyzer",
                "findings": {}
            }

        try:
            wappalyzer = Wappalyzer.latest(update=False)
            target_url = f"https://{domain}"
            logger.info(f"[Wappalyzer Collector] Fetching page for analysis: {target_url}")
            webpage = WebPage.new_from_url(target_url, timeout=10)
            detected = wappalyzer.analyze_with_categories(webpage)
            logger.info(f"[Wappalyzer Collector] Detected {len(detected)} technologies.")

            tech_list = []
            has_ecommerce_platform = False
            ecommerce_keywords = {"ecommerce", "cart", "shopify", "magento", "woocommerce", "bigcommerce", "payment"}

            for tech_name, tech_info in detected.items():
                categories = tech_info.get("categories", [])
                tech_list.append({"name": tech_name, "categories": categories})
                # Check if any category hints at ecommerce
                for cat in categories:
                    if any(kw in cat.lower() for kw in ecommerce_keywords):
                        has_ecommerce_platform = True

            findings = {
                "detected_technologies": tech_list,
                "has_ecommerce_platform": has_ecommerce_platform
            }
            findings = {k: findings.get(k) for k in self.config.target_fields}
            return {
                "source": self.config.source_name,
                "status": "success",
                "findings": findings
            }
        except Exception as e:
            logger.warning(f"[Wappalyzer Collector] Tech detection failed: {e}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": str(e),
                "findings": {}
            }


class CensusNAICSCollectorAgent(BaseCollectorAgent):
    async def collect(self, company_name: str, domain: str, **kwargs) -> Dict[str, Any]:
        import json
        logger = self.get_logger()
        logger.info(f"[Census NAICS Collector] Starting data collection for {company_name} ({domain})")
        logger.info(f"[Census NAICS Collector] Looking up NAICS mapping for '{company_name}'")

        # Load the static SIC→NAICS map
        map_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'naics_sic_map.json')
        try:
            with open(map_path, 'r') as f:
                sic_naics_map = json.load(f)
        except FileNotFoundError:
            logger.warning(f"[Census NAICS Collector] Map file not found at: {map_path}")
            return {
                "source": self.config.source_name,
                "status": "error",
                "message": "naics_sic_map.json not found.",
                "findings": {}
            }

        # Try to get SIC codes from kwargs (passed from state by the workflow node)
        sic_codes = kwargs.get("sic_codes", [])
        if not sic_codes:
            logger.info("[Census NAICS Collector] No SIC codes provided, returning empty mapping.")
            return {
                "source": self.config.source_name,
                "status": "skipped",
                "message": "No SIC codes available for NAICS mapping.",
                "findings": {}
            }

        naics_results = []
        for sic in sic_codes:
            sic_str = str(sic).strip()
            entry = sic_naics_map.get(sic_str)
            if entry:
                naics_results.append({
                    "sic_code": sic_str,
                    "naics_code": entry["naics"],
                    "naics_description": entry["description"]
                })
                logger.info(f"[Census NAICS Collector] Mapped SIC {sic_str} → NAICS {entry['naics']} ({entry['description']})")
            else:
                logger.info(f"[Census NAICS Collector] No NAICS mapping found for SIC {sic_str}")

        findings = {
            "naics_code": naics_results[0]["naics_code"] if naics_results else None,
            "naics_description": naics_results[0]["naics_description"] if naics_results else None,
            "naics_mappings": naics_results
        }
        findings = {k: findings.get(k) for k in self.config.target_fields}
        return {
            "source": self.config.source_name,
            "status": "success",
            "findings": findings
        }


class WebSearchCollectorAgent(BaseCollectorAgent):
    async def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        # WebSearch is currently marked as 'future' in rule configurations and disabled.
        return {
            "source": self.config.source_name,
            "status": "skipped",
            "message": "WebSearch API key not configured.",
            "findings": {}
        }

