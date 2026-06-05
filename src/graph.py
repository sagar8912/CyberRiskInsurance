import concurrent.futures
from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END
from src.state import CyberRiskState
from src.supervisor import supervisor_node
from src.router import router_node
from src.coordinator import coordinator_node
from src.fact_checker import fact_checker_node
from src.underwriter import underwriter_node

from src.collectors import (
    WebSearchCollector,
    DomainScraperCollector,
    WikipediaCollector,
    DBCollector,
    SECCollector,
    ResponsesAPICollector
)

def collectors_node(state: CyberRiskState) -> Dict[str, Any]:
    name = state.get("company_name")
    domain = state.get("domain")
    budget = state.get("tool_budget", [])
    logs = []
    
    logs.append(f"Collectors: Initializing parallel collection for budget: {budget}...")
    
    collectors_map = {
        "WebSearch": WebSearchCollector(),
        "DomainScraper": DomainScraperCollector(),
        "Wikipedia": WikipediaCollector(),
        "DBCollector": DBCollector(),
        "SECCollector": SECCollector(),
        "ResponsesAPI": ResponsesAPICollector()
    }
    
    evidence = {}
    
    def run_collector(col_name: str):
        col_inst = collectors_map.get(col_name)
        if col_inst:
            try:
                return col_name, col_inst.collect(name, domain)
            except Exception as e:
                return col_name, {"status": "error", "error": str(e), "findings": {}}
        # If it is one of the extra budget tools (e.g. GitHubSearch, NewsSearch)
        return col_name, {"status": "success", "message": "Stub for extra search tool.", "findings": {}}

    # Execute in parallel to simulate "Do in 10 seconds what would take 60 sequentially"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_collector, col): col for col in budget}
        for future in concurrent.futures.as_completed(futures):
            col_name, res = future.result()
            evidence[col_name] = res
            logs.append(f"Collectors: '{col_name}' returned status: {res.get('status')}")

    return {
        "collected_evidence": evidence,
        "audit_logs": state.get("audit_logs", []) + logs
    }

def supervisor_routing(state: CyberRiskState) -> Literal["router_node", "__end__"]:
    """Determines whether to run collectors or exit early on invalid inputs or cache hits."""
    if not state.get("valid"):
        return "__end__"
    if state.get("cache_hit"):
        return "__end__"
    return "router_node"

def build_workflow():
    # 1. Initialize StateGraph
    workflow = StateGraph(CyberRiskState)
    
    # 2. Add Nodes
    workflow.add_node("supervisor_node", supervisor_node)
    workflow.add_node("router_node", router_node)
    workflow.add_node("collectors_node", collectors_node)
    workflow.add_node("coordinator_node", coordinator_node)
    workflow.add_node("fact_checker_node", fact_checker_node)
    workflow.add_node("underwriter_node", underwriter_node)
    
    # 3. Define Entrypoint and Connections
    workflow.set_entry_point("supervisor_node")
    
    # Conditional edge from supervisor
    workflow.add_conditional_edges(
        "supervisor_node",
        supervisor_routing,
        {
            "router_node": "router_node",
            "__end__": END
        }
    )
    
    # Sequential path
    workflow.add_edge("router_node", "collectors_node")
    workflow.add_edge("collectors_node", "coordinator_node")
    workflow.add_edge("coordinator_node", "fact_checker_node")
    workflow.add_edge("fact_checker_node", "underwriter_node")
    workflow.add_edge("underwriter_node", END)
    
    # 4. Compile Graph
    return workflow.compile()
