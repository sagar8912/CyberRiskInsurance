import json
import os
from typing import Dict, Any
from src.state import CyberRiskState

def router_node(state: CyberRiskState) -> Dict[str, Any]:
    name = state.get("company_name", "")
    logs = []
    
    # Fast check of local mock data to simulate finding initial revenue range
    revenue = 0
    mock_data_path = "data/mock_sources/mock_companies.json"
    if os.path.exists(mock_data_path):
        with open(mock_data_path, "r") as f:
            mock_db = json.load(f)
            if name in mock_db:
                revenue = mock_db[name].get("revenue", 0)
                
    logs.append(f"Router: Looked up initial estimated revenue for '{name}': ${revenue:,}")

    # Determine Tier and Tool Budget
    if revenue >= 500000000:
        routing_tier = "Public / $500M+"
        tool_budget = ["WebSearch", "DomainScraper", "Wikipedia", "DBCollector", "SECCollector", "ResponsesAPI"]
    elif revenue >= 50000000:
        routing_tier = "$50M - $500M"
        tool_budget = ["WebSearch", "DomainScraper", "Wikipedia", "DBCollector", "SECCollector", "ResponsesAPI"]
    elif revenue > 0 and revenue < 50000000:
        routing_tier = "<$50M"
        # 8 tools budget: 6 core + 2 additional mock tools (GitHubSearch, NewsSearch)
        tool_budget = ["WebSearch", "DomainScraper", "Wikipedia", "DBCollector", "SECCollector", "ResponsesAPI", "GitHubSearch", "NewsSearch"]
    else:
        routing_tier = "Unknown / Tiny"
        # 3 tools budget
        tool_budget = ["WebSearch", "DomainScraper", "Wikipedia"]

    logs.append(f"Router: Mapped to tier '{routing_tier}' with tool budget: {tool_budget}")

    return {
        "routing_tier": routing_tier,
        "tool_budget": tool_budget,
        "audit_logs": state.get("audit_logs", []) + logs
    }
