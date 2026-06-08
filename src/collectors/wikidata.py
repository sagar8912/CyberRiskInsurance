import urllib.request
import urllib.parse
import json
from typing import Dict, Any
from src.collectors.base import BaseCollector

class WikidataCollector(BaseCollector):
    """
    Queries the Wikidata Action API to extract company facts.
    Uses wbsearchentities and wbgetentities to avoid SPARQL rate limits.
    """
    
    def __init__(self):
        super().__init__("Wikidata")
    
    def collect(self, company_name: str, domain: str) -> Dict[str, Any]:
        result = {
            "source": "Wikidata",
            "status": "skipped",
            "is_mock": False,
            "findings": {}
        }
        
        try:
            # 1. Search for Entities
            query = urllib.parse.urlencode({
                'action': 'wbsearchentities',
                'search': company_name,
                'language': 'en',
                'format': 'json',
                'limit': 5
            })
            url = f'https://www.wikidata.org/w/api.php?{query}'
            req = urllib.request.Request(url, headers={'User-Agent': 'CyberRiskBot/1.1 (contact@example.com)'})
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            search_results = data.get('search', [])
            if not search_results:
                result["status"] = "unresolved"
                return result
                
            qids = [res['id'] for res in search_results]
            
            # 2. Get Entity Claims for all candidates to find best match
            query2 = urllib.parse.urlencode({
                'action': 'wbgetentities',
                'ids': '|'.join(qids),
                'format': 'json',
                'props': 'claims|labels'
            })
            url2 = f'https://www.wikidata.org/w/api.php?{query2}'
            req2 = urllib.request.Request(url2, headers={'User-Agent': 'CyberRiskBot/1.1 (contact@example.com)'})
            
            with urllib.request.urlopen(req2, timeout=10) as response:
                data2 = json.loads(response.read().decode())
                
            entities = data2.get('entities', {})
            
            best_qid = None
            best_claims = {}
            
            import difflib
            
            for qid_candidate in qids:
                entity = entities.get(qid_candidate, {})
                label = entity.get('labels', {}).get('en', {}).get('value', '').lower()
                candidate_claims = entity.get('claims', {})
                
                # Extract website
                websites = []
                for statement in candidate_claims.get('P856', []):
                    snak = statement.get('mainsnak', {})
                    if snak.get('snaktype') == 'value' and snak.get('datavalue', {}).get('type') == 'string':
                        websites.append(snak.get('datavalue', {}).get('value'))
                        
                # Check domain match
                domain_match = False
                for w in websites:
                    if domain.lower() in w.lower():
                        domain_match = True
                        break
                        
                # Similarity
                sim = difflib.SequenceMatcher(None, company_name.lower(), label).ratio()
                
                if domain_match or sim > 0.8:
                    best_qid = qid_candidate
                    best_claims = candidate_claims
                    break
                    
            if not best_qid:
                result["status"] = "unresolved"
                return result
                
            qid = best_qid
            claims = best_claims
                
            # Helper to extract values
            def get_snak_value(snak):
                if snak.get('snaktype') == 'value':
                    datavalue = snak.get('datavalue', {})
                    if datavalue.get('type') == 'wikibase-entityid':
                        return datavalue.get('value', {}).get('id')
                    elif datavalue.get('type') == 'string':
                        return datavalue.get('value')
                    elif datavalue.get('type') == 'monolingualtext':
                        return datavalue.get('value', {}).get('text')
                return None

            def extract_claim_values(prop_id):
                vals = []
                for statement in claims.get(prop_id, []):
                    val = get_snak_value(statement.get('mainsnak', {}))
                    if val:
                        vals.append(val)
                return vals

            def extract_amount(prop_id):
                for statement in claims.get(prop_id, []):
                    snak = statement.get('mainsnak', {})
                    if snak.get('snaktype') == 'value':
                        datavalue = snak.get('datavalue', {}).get('value', {})
                        if 'amount' in datavalue:
                            try:
                                return float(datavalue['amount'].replace('+', ''))
                            except ValueError:
                                pass
                return None

            official_names = extract_claim_values('P1448')
            countries = extract_claim_values('P17')
            hqs = extract_claim_values('P159')
            industries = extract_claim_values('P452')
            websites = extract_claim_values('P856')
            parents = extract_claim_values('P749')
            subsidiaries = extract_claim_values('P355')
            
            revenue = extract_amount('P2139')
            employees = extract_amount('P1128')
            market_cap = extract_amount('P2226')
            
            # 3. Resolve Q-IDs to Labels
            qids_to_resolve = set(countries + hqs + industries + parents + subsidiaries)
            resolved_labels = {}
            
            if qids_to_resolve:
                # Chunk up to 50 ids per request (API limit)
                qids_list = list(qids_to_resolve)
                for i in range(0, len(qids_list), 50):
                    chunk = qids_list[i:i+50]
                    query3 = urllib.parse.urlencode({
                        'action': 'wbgetentities',
                        'ids': '|'.join(chunk),
                        'format': 'json',
                        'props': 'labels',
                        'languages': 'en'
                    })
                    url3 = f'https://www.wikidata.org/w/api.php?{query3}'
                    req3 = urllib.request.Request(url3, headers={'User-Agent': 'CyberRiskBot/1.1 (contact@example.com)'})
                    with urllib.request.urlopen(req3, timeout=10) as response:
                        data3 = json.loads(response.read().decode())
                        for entity_id, entity_data in data3.get('entities', {}).items():
                            label = entity_data.get('labels', {}).get('en', {}).get('value')
                            if label:
                                resolved_labels[entity_id] = label
                                
            # 4. Map resolved labels
            def map_labels(id_list):
                return [resolved_labels[x] for x in id_list if x in resolved_labels]

            result["findings"] = {
                "official_name": official_names[0] if official_names else None,
                "country": map_labels(countries)[0] if map_labels(countries) else None,
                "headquarters": map_labels(hqs)[0] if map_labels(hqs) else None,
                "industry": map_labels(industries),
                "official_website": websites[0] if websites else None,
                "parent_company": map_labels(parents)[0] if map_labels(parents) else None,
                "subsidiaries": map_labels(subsidiaries),
                "revenue": revenue,
                "employees": employees,
                "market_cap": market_cap
            }
            result["status"] = "success"
            return result
            
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            return result
