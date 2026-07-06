from typing import Dict, Any, List, Annotated
from typing_extensions import TypedDict
import operator
import time

from langgraph.graph import START, END, StateGraph
from langgraph.types import RetryPolicy

from src.factory import AgentFactory
from src.collectors import (
    WikipediaCollectorAgent,
    WikidataCollectorAgent,
    SECCollectorAgent,
    DNBCollectorAgent,
    DomainScraperCollectorAgent,
    ResponsesAPICollectorAgent,
    OpenCorporatesCollectorAgent,
    GDELTCollectorAgent,
    CourtListenerCollectorAgent,
    SSLLabsCollectorAgent,
    FTCFeedCollectorAgent,
    WappalyzerCollectorAgent,
    CensusNAICSCollectorAgent
)
from src.processors import (
    CollectionCoordinatorAgent,
    FactCheckerAgent,
    UnderwriterAgent
)
from src.supervisor import supervisor_node
from src.cache import CachingCollectorWrapper, get_cache_manager
from src.utils.logger import get_agent_logger

# Reducer to merge reports dictionary
def merge_reports(left: dict, right: dict) -> dict:
    return {**left, **right}

class CyberRiskRatingState(TypedDict, total=False):
    # Inputs
    company_name: str
    domain: str
    business_rule: str
    rule_id: str
    run_id: str

    # Status / Supervisor
    valid: bool
    enrichment: dict
    mismatch_flag: bool
    entity_status: str
    entity_resolution_confidence: str
    cache_hit: bool
    cache_data: Any
    routing_tier: str
    tool_budget: list

    # Core workflow data
    reports: Annotated[dict, merge_reports]
    collected_evidence: Annotated[dict, merge_reports]
    reconciled_profile: dict
    merged: dict
    conflict_flags: list
    claims_verification: dict
    fact_check: dict
    accuracy_score: float

    # Output / Assessment
    risk_assessment: dict
    risk_category: str
    underwriting_rationale: dict
    modifier_scores: dict
    confidence_score: float
    confidence_band: str
    human_escalation_flag: bool
    audit_logs: Annotated[list, operator.add]
    token_summary: dict

def supervisor_routing(state: CyberRiskRatingState) -> str:
    wf_log = get_agent_logger("workflow")
    if not state.get("valid"):
        wf_log.info("[Workflow Supervisor] Entity validation FAILED — routing to END (no collection).")
        return "__end__"
    if state.get("cache_hit"):
        wf_log.info("[Workflow Supervisor] Cache HIT detected — routing to coordinator (skip collectors fanout).")
        return "coordinator"
    wf_log.info("[Workflow Supervisor] Cache MISS — routing to full collectors fanout.")
    return "collectors_fanout"

def build_cyber_risk_rating_graph(enable_cache: bool = True):
    rule_id = "cyber_risk_rating"
    factory = AgentFactory.for_rule(rule_id)
    cache = get_cache_manager()

    # Create collectors
    wiki_base = factory.create_collector_agent("wikipedia", WikipediaCollectorAgent)
    wikidata_base = factory.create_collector_agent("wikidata", WikidataCollectorAgent)
    sec_base = factory.create_collector_agent("sec", SECCollectorAgent)
    dnb_base = factory.create_collector_agent("dnb", DNBCollectorAgent)
    domain_base = factory.create_collector_agent("domain", DomainScraperCollectorAgent)
    responses_base = factory.create_collector_agent("responses", ResponsesAPICollectorAgent)
    opencorporates_base = factory.create_collector_agent("opencorporates", OpenCorporatesCollectorAgent)
    gdelt_base = factory.create_collector_agent("gdelt", GDELTCollectorAgent)
    courtlistener_base = factory.create_collector_agent("courtlistener", CourtListenerCollectorAgent)
    ssllabs_base = factory.create_collector_agent("ssllabs", SSLLabsCollectorAgent)
    ftc_base = factory.create_collector_agent("ftc", FTCFeedCollectorAgent)
    wappalyzer_base = factory.create_collector_agent("wappalyzer", WappalyzerCollectorAgent)
    census_naics_base = factory.create_collector_agent("census_naics", CensusNAICSCollectorAgent)

    # Wrap with cache if enabled
    wiki = CachingCollectorWrapper(wiki_base, "wikipedia", rule_id, cache) if enable_cache and cache.enabled else wiki_base
    wikidata = CachingCollectorWrapper(wikidata_base, "wikidata", rule_id, cache) if enable_cache and cache.enabled else wikidata_base
    sec = CachingCollectorWrapper(sec_base, "sec", rule_id, cache) if enable_cache and cache.enabled else sec_base
    dnb = CachingCollectorWrapper(dnb_base, "dnb", rule_id, cache) if enable_cache and cache.enabled else dnb_base
    domain_agent = CachingCollectorWrapper(domain_base, "domain", rule_id, cache) if enable_cache and cache.enabled else domain_base
    responses = CachingCollectorWrapper(responses_base, "responses", rule_id, cache) if enable_cache and cache.enabled else responses_base
    opencorporates = CachingCollectorWrapper(opencorporates_base, "opencorporates", rule_id, cache) if enable_cache and cache.enabled else opencorporates_base
    gdelt_agent = CachingCollectorWrapper(gdelt_base, "gdelt", rule_id, cache) if enable_cache and cache.enabled else gdelt_base
    courtlistener = CachingCollectorWrapper(courtlistener_base, "courtlistener", rule_id, cache) if enable_cache and cache.enabled else courtlistener_base
    ssllabs = CachingCollectorWrapper(ssllabs_base, "ssllabs", rule_id, cache) if enable_cache and cache.enabled else ssllabs_base
    ftc = CachingCollectorWrapper(ftc_base, "ftc", rule_id, cache) if enable_cache and cache.enabled else ftc_base
    wappalyzer = CachingCollectorWrapper(wappalyzer_base, "wappalyzer", rule_id, cache) if enable_cache and cache.enabled else wappalyzer_base
    census_naics = CachingCollectorWrapper(census_naics_base, "census_naics", rule_id, cache) if enable_cache and cache.enabled else census_naics_base

    # Create processors
    coordinator = factory.create_coordinator(CollectionCoordinatorAgent)
    fact_checker = factory.create_fact_checker(FactCheckerAgent)
    underwriter = factory.create_underwriter(UnderwriterAgent)

    # Retries for Groq API limits
    api_retry = RetryPolicy(max_attempts=3, initial_interval=2.0, backoff_factor=2.0)

    # 1. Define Node functions
    async def wiki_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] wiki_node → START")
        rep = await wiki.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] wiki_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        # Format results for both state layouts (reports and collected_evidence)
        return {"reports": {"Wikipedia": rep}, "collected_evidence": {"Wikipedia": rep}}

    async def wikidata_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] wikidata_node → START")
        rep = await wikidata.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] wikidata_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"Wikidata": rep}, "collected_evidence": {"Wikidata": rep}}

    async def sec_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] sec_node → START")
        rep = await sec.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] sec_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"SECCollector": rep}, "collected_evidence": {"SECCollector": rep}}

    async def dnb_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] dnb_node → START")
        rep = await dnb.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] dnb_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"DBCollector": rep}, "collected_evidence": {"DBCollector": rep}}

    async def domain_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] domain_node → START")
        responses_report = state.get("reports", {}).get("ResponsesAPI", {})
        discovered = responses_report.get("findings", {}).get("official_websites", [])
        wf_log.debug(f"[Workflow Node] domain_node received {len(discovered)} discovered_domains from ResponsesAPI: {discovered}")
        rep = await domain_agent.collect(state["company_name"], state["domain"], discovered_domains=discovered)
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] domain_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"DomainScraper": rep}, "collected_evidence": {"DomainScraper": rep}}

    async def responses_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] responses_node → START")
        rep = await responses.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] responses_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"ResponsesAPI": rep}, "collected_evidence": {"ResponsesAPI": rep}}

    async def opencorporates_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] opencorporates_node → START")
        rep = await opencorporates.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] opencorporates_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"OpenCorporates": rep}, "collected_evidence": {"OpenCorporates": rep}}

    async def gdelt_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] gdelt_node → START")
        rep = await gdelt_agent.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] gdelt_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"GDELT": rep}, "collected_evidence": {"GDELT": rep}}

    async def courtlistener_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] courtlistener_node → START")
        rep = await courtlistener.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] courtlistener_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"CourtListener": rep}, "collected_evidence": {"CourtListener": rep}}

    async def ssllabs_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] ssllabs_node → START")
        rep = await ssllabs.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] ssllabs_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"SSLLabs": rep}, "collected_evidence": {"SSLLabs": rep}}

    async def ftc_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] ftc_node → START")
        rep = await ftc.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] ftc_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"FTC": rep}, "collected_evidence": {"FTC": rep}}

    async def wappalyzer_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] wappalyzer_node → START")
        rep = await wappalyzer.collect(state["company_name"], state["domain"])
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] wappalyzer_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"Wappalyzer": rep}, "collected_evidence": {"Wappalyzer": rep}}

    async def census_naics_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        # Pass SIC codes from reconciled_profile or collected evidence to enable mapping
        sic_codes = state.get("reconciled_profile", {}).get("sic_codes", [])
        wf_log.info(f"[Workflow Node] census_naics_node → START (sic_codes={sic_codes})")
        rep = await census_naics.collect(state["company_name"], state["domain"], sic_codes=sic_codes)
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] census_naics_node → DONE (status={rep.get('status', '?')}, elapsed={elapsed:.0f}ms)")
        return {"reports": {"CensusNAICS": rep}, "collected_evidence": {"CensusNAICS": rep}}

    async def coordinator_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        # If cache hit, restore reports/collected_evidence from cached data
        if state.get("cache_hit") and state.get("cache_data"):
            wf_log.info("[Workflow Node] coordinator_node → START (restoring from CACHE)")
            cache_data = state["cache_data"]
            evidence = cache_data.get("collected_evidence", {})
            wf_log.info(f"[Workflow Node] coordinator_node: cache evidence sources = {list(evidence.keys())}")
            result = {
                "reports": evidence,
                "collected_evidence": evidence,
                **(await coordinator.coordinate({**state, "reports": evidence}))
            }
        else:
            wf_log.info(f"[Workflow Node] coordinator_node → START (live run, reports from {list(state.get('reports', {}).keys())})")
            result = await coordinator.coordinate(state)
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] coordinator_node → DONE (elapsed={elapsed:.0f}ms)")
        return result

    async def fact_checker_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] fact_checker_node → START")
        res = await fact_checker.verify(state)
        elapsed = (time.time() - t0) * 1000
        wf_log.info(f"[Workflow Node] fact_checker_node → DONE (elapsed={elapsed:.0f}ms)")
        return {"fact_check": res, **res}

    async def underwriter_node(state: CyberRiskRatingState) -> dict:
        wf_log = get_agent_logger("workflow")
        t0 = time.time()
        wf_log.info("[Workflow Node] underwriter_node → START")
        # Add Business Rule to input variables
        state["business_rule"] = underwriter.config.business_rule
        res = underwriter.underwrite(state)
        elapsed = (time.time() - t0) * 1000
        token_sum = factory.tracker.get_summary()
        wf_log.info(f"[Workflow Node] underwriter_node → DONE (elapsed={elapsed:.0f}ms, total_tokens={token_sum.get('total_tokens', '?')}, total_cost=${token_sum.get('total_cost', 0):.4f})")
        return {"risk_assessment": res, **res, "token_summary": token_sum}

    def _update_step(state: dict, step: int, node: str):
        run_id = state.get("run_id")
        if run_id:
            try:
                from src.utils.run_status import run_status_cache
                run_status_cache.update_run(run_id, step=step, node=node)
            except Exception:
                pass

    def with_step(fn, step: int, node_name: str, is_underwriter: bool = False):
        async def wrapped(state: CyberRiskRatingState) -> dict:
            _update_step(state, step, node_name)
            res = await fn(state)
            if not is_underwriter:
                _update_step(state, step, node_name)
            else:
                run_id = state.get("run_id")
                if run_id:
                    try:
                        from src.api import format_analysis_response
                        from src.utils.run_status import run_status_cache
                        merged_final = {**state, **res}
                        formatted = format_analysis_response(merged_final, state.get("company_name", ""), state.get("domain", ""))
                        run_status_cache.complete_run(run_id, 7, formatted)
                    except Exception as e:
                        wf_log = get_agent_logger("workflow")
                        wf_log.error(f"Error completing run status cache in underwriter_node: {e}")
            return res
        return wrapped

    # 2. Build graph structure
    g = StateGraph(CyberRiskRatingState)
    g.add_node("supervisor_node", supervisor_node)
    
    # Collectors
    g.add_node("wiki", with_step(wiki_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("wikidata", with_step(wikidata_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("sec", with_step(sec_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("dnb", with_step(dnb_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("domain", with_step(domain_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("responses", with_step(responses_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("opencorporates", with_step(opencorporates_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("gdelt", with_step(gdelt_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("courtlistener", with_step(courtlistener_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("ssllabs", with_step(ssllabs_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("ftc", with_step(ftc_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("wappalyzer", with_step(wappalyzer_node, 3, "collector_node"), retry_policy=api_retry)
    g.add_node("census_naics", with_step(census_naics_node, 4, "coordinator_node"), retry_policy=api_retry)

    # Processors
    g.add_node("coordinator", with_step(coordinator_node, 4, "coordinator_node"), retry_policy=api_retry)
    g.add_node("fact_checker", with_step(fact_checker_node, 5, "fact_checker_node"), retry_policy=api_retry)
    g.add_node("underwriter", with_step(underwriter_node, 6, "underwriter_node", is_underwriter=True), retry_policy=api_retry)

    # Entrypoint
    g.set_entry_point("supervisor_node")

    # Routing from Supervisor
    g.add_conditional_edges(
        "supervisor_node",
        supervisor_routing,
        {
            "collectors_fanout": "wiki",
            "coordinator": "coordinator",
            "__end__": END
        }
    )
    # Fanout connections (domain is now run sequentially after responses)
    g.add_conditional_edges(
        "supervisor_node",
        lambda x: [
            "wikidata", "sec", "dnb", "responses",
            "opencorporates", "gdelt", "courtlistener", "ssllabs", "ftc", "wappalyzer"
        ] if (x.get("valid") and not x.get("cache_hit")) else [],
        {
            "wikidata": "wikidata",
            "sec": "sec",
            "dnb": "dnb",
            "responses": "responses",
            "opencorporates": "opencorporates",
            "gdelt": "gdelt",
            "courtlistener": "courtlistener",
            "ssllabs": "ssllabs",
            "ftc": "ftc",
            "wappalyzer": "wappalyzer"
        }
    )

    # Fanin connections to Coordinator
    g.add_edge("wiki", "coordinator")
    g.add_edge("wikidata", "coordinator")
    g.add_edge("sec", "coordinator")
    g.add_edge("dnb", "coordinator")
    g.add_edge("responses", "domain")
    g.add_edge("domain", "coordinator")
    g.add_edge("opencorporates", "coordinator")
    g.add_edge("gdelt", "coordinator")
    g.add_edge("courtlistener", "coordinator")
    g.add_edge("ssllabs", "coordinator")
    g.add_edge("ftc", "coordinator")
    g.add_edge("wappalyzer", "coordinator")

    # Census NAICS runs after coordinator (needs SIC codes from reconciled profile)
    g.add_edge("coordinator", "census_naics")
    g.add_edge("census_naics", "fact_checker")

    # Sequential processors
    g.add_edge("fact_checker", "underwriter")
    g.add_edge("underwriter", END)

    return g.compile()
