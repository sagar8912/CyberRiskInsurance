import json
import os
from typing import Dict, Any
from src.state import CyberRiskState

def router_node(state: CyberRiskState) -> Dict[str, Any]:
    name = state.get("company_name", "")
    logs = []
    
    # Fast check of local mock data to simulate finding initial revenue range
    revenue = None
    mock_data_path = "data/mock_sources/mock_companies.json"
    if os.path.exists(mock_data_path):
        with open(mock_data_path, "r") as f:
            mock_db = json.load(f)
            if name in mock_db:
                revenue = mock_db[name].get("revenue", None)
                
    if revenue is not None:
        logs.append(f"Router: Looked up initial estimated revenue for '{name}': ${revenue:,}")
        revenue_confidence = "high"
    else:
        known_large_companies = ["microsoft", "apple", "amazon", "google", "alphabet", "meta", "tcs", "tata consultancy services", "ibm", "oracle", "browserstack"]
        if name.lower() in known_large_companies:
            logs.append(f"Router: Revenue not available, but '{name}' is a known public/global company. Inferring large tier.")
            revenue_confidence = "high"
            revenue = 1000000000  # Fallback to trigger top tier
        else:
            logs.append(f"Router: Revenue not available for '{name}', inferring tier from signals.")
            revenue_confidence = "low"
            revenue = 0  # Fallback for tier logic
        
    # Determine Tier and Tool Budget
    enable_responses = os.environ.get("ENABLE_RESPONSES_API", "false").lower() == "true"
    base_tools = ["WebSearch", "DomainScraper", "Wikipedia", "Wikidata", "DBCollector", "SECCollector"]
    if enable_responses:
        base_tools.append("ResponsesAPI")

    if revenue >= 500000000:
        routing_tier = "Public / $500M+"
        tool_budget = list(base_tools)
    elif revenue >= 50000000:
        routing_tier = "$50M - $500M"
        tool_budget = list(base_tools)
    elif revenue > 0 and revenue < 50000000:
        routing_tier = "<$50M"
        tool_budget = list(base_tools) + ["GitHubSearch", "NewsSearch"]
    else:
        routing_tier = "Unknown / Tiny"
        tool_budget = list(base_tools)

    logs.append(f"Router: Mapped to tier '{routing_tier}' with tool budget: {tool_budget}. Confidence: {revenue_confidence}")

    enrichment = state.get("enrichment", {})
    enrichment["revenue_confidence"] = revenue_confidence

    return {
        "routing_tier": routing_tier,
        "tool_budget": tool_budget,
        "enrichment": enrichment,
        "audit_logs": state.get("audit_logs", []) + logs
    }
