import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from src.registry import BusinessRuleRegistry
from src.workflows import build_cyber_risk_rating_graph
from src.cache import get_cache_manager
import src.rules as _rules  # Load all rules to trigger registration

app = FastAPI(title="Cyber Risk Underwriter API")

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    company: str
    domain: str

def format_analysis_response(final_state: dict, company_name: str, domain: str) -> dict:
    from src.utils.logger import get_agent_logger
    api_logger = get_agent_logger("API")
    api_logger.info("START Response Serialization")

    # Write Cache on success (same as cli.py)
    if final_state.get("valid") and not final_state.get("cache_hit"):
        try:
            cache_mgr = get_cache_manager()
            profile_summary = {
                "collected_evidence": final_state.get("collected_evidence", {}),
                "cache_type": "collector_cache"
            }
            cache_mgr.write(company_name, domain, profile_summary)
        except Exception as e:
            pass # Non-fatal if cache fails

    # Format Reconciled Profile
    reconciled = final_state.get("reconciled_profile", {})
    rev = reconciled.get('revenue')
    rev_display = f"${rev:,}" if rev is not None else "Not Available"
    
    reconciled_profile_formatted = {
        "revenue": rev_display,
        "subsidiariesCount": len(reconciled.get("subsidiaries", [])),
        "acquisitionsCount": len(reconciled.get("acquisitions", [])),
        "customerType": reconciled.get("customer_type", "Unknown"),
        "ecommercePlatform": reconciled.get("has_ecommerce", False),
        "countriesOfOps": ", ".join(reconciled.get("countries_of_operation", [])),
        "privacyPolicy": reconciled.get("privacy_policy_published", False)
    }

    # Format Fact Checker Claims
    claims_verification = final_state.get("claims_verification", {})
    fact_checker_claims = []
    for claim, info in claims_verification.items():
        fact_checker_claims.append({
            "claim": claim,
            "status": info.get("status", "Unsupported"),
            "sourceCount": info.get("sources_count", 0)
        })

    # Format Modifiers
    modifier_scores = final_state.get("modifier_scores", {})
    rationales = final_state.get("underwriting_rationale", {})
    fact_check = final_state.get("fact_check", {})
    merged = final_state.get("merged", {})
    risk_assess = final_state.get("risk_assessment", {})
    collected = final_state.get("collected_evidence", {})
    llm_prompts = final_state.get("llm_prompts", {})
    
    modifiers_formatted = []
    idx = 1
    for mod_name, details in modifier_scores.items():
        score_str = str(details.get("score", "0.0"))
            
        mod_obj = {
            "id": idx,
            "name": mod_name,
            "rating": details.get("rating", "Average").upper(),
            "score": score_str,
            "rationale": rationales.get(mod_name, "No rationale provided."),
            "decision_summary": rationales.get(mod_name, "No rationale provided."),
            # Spread all inner backend fields
            **{k: v for k, v in details.items() if k not in ["rating", "score"]}
        }
        
        # Fallbacks to global logs if modifier didn't attach them
        if "fact_checker_output" not in mod_obj:
            mod_obj["fact_checker_output"] = fact_check.get(mod_name) or fact_check
        if "coordinator_output" not in mod_obj:
            mod_obj["coordinator_output"] = merged.get(mod_name) or merged
        if "underwriter_output" not in mod_obj:
            mod_obj["underwriter_output"] = risk_assess.get(mod_name) or risk_assess
        if "collector_outputs" not in mod_obj:
            mod_obj["collector_outputs"] = collected
        if "prompt_used" not in mod_obj:
            mod_obj["prompt_used"] = llm_prompts.get(mod_name) or llm_prompts
            
        modifiers_formatted.append(mod_obj)
        idx += 1

    # Format Final Verdict
    final_verdict = {
        "riskCategory": final_state.get("risk_category", "Average").upper(),
        "underwritingScore": f"{final_state.get('confidence_score', 0)}%",
        "confidenceBand": final_state.get("confidence_band", "Low"),
        "humanEscalation": final_state.get("human_escalation_flag", False)
    }

    # Format Wikidata Output
    wikidata_report = final_state.get("collected_evidence", {}).get("Wikidata", {})
    if wikidata_report.get("status") == "success":
        wd_findings = wikidata_report.get("findings", {})
        
        ind = wd_findings.get("industry")
        if isinstance(ind, list) and ind:
            industry_str = ", ".join(str(i) for i in ind)
        elif ind:
            industry_str = str(ind)
        else:
            industry_str = "Not Available"
            
        subs = wd_findings.get("subsidiaries")
        if isinstance(subs, list) and subs:
            subs_str = ", ".join(str(s) for s in subs)
        elif subs:
            subs_str = str(subs)
        else:
            subs_str = "Not Available"
            
        wikidata_output_formatted = {
            "entity_name": company_name,
            "industry": industry_str,
            "headquarters": str(wd_findings.get("headquarters")) if wd_findings.get("headquarters") else "Not Available",
            "country": str(wd_findings.get("country")) if wd_findings.get("country") else "Not Available",
            "official_website": str(wd_findings.get("official_website")) if wd_findings.get("official_website") else "Not Available",
            "founded_year": str(wd_findings.get("founding_year")) if wd_findings.get("founding_year") else "Not Available",
            "parent_organization": "Not Available",
            "subsidiaries": subs_str
        }
    else:
        wikidata_output_formatted = {
            "entity_name": company_name,
            "industry": "Not Available",
            "headquarters": "Not Available",
            "country": "Not Available",
            "official_website": "Not Available",
            "founded_year": "Not Available",
            "parent_organization": "Not Available",
            "subsidiaries": "Not Available"
        }

    return {
        "target_entity": {"name": company_name, "domain": domain},
        "workflow_trace": final_state.get("audit_logs", []),
        "reconciled_profile": reconciled_profile_formatted,
        "wikidata_output": wikidata_output_formatted,
        "fact_checker_claims": fact_checker_claims,
        "modifiers": modifiers_formatted,
        "final_verdict": final_verdict,
        "logs": final_state.get("audit_logs", []),
        "executionTimeline": [{"time": i, "event": l} for i, l in enumerate(final_state.get("audit_logs", []))],
        "collectorOutputs": final_state.get("collected_evidence", {}),
        "coordinatorOutput": final_state.get("merged", {}),
        "factCheckerOutput": final_state.get("fact_check", {}),
        "underwriterOutput": final_state.get("risk_assessment", {}),
        "nodeStatus": final_state.get("token_summary", {}),
        "promptResponses": final_state.get("llm_prompts", {}),
        "executionTime": final_state.get("execution_time", None)
    }

@app.post("/api/analyze")
async def analyze_company(req: AnalysisRequest):
    rule_id = "cyber_risk_rating"
    company_name = req.company.strip()
    domain = req.domain.strip()

    if not company_name or not domain:
        raise HTTPException(status_code=400, detail="Company and domain are required")

    # Compile the LangGraph workflow
    graph = build_cyber_risk_rating_graph(enable_cache=True)

    # Initial State
    initial_state = {
        "company_name": company_name,
        "domain": domain,
        "rule_id": rule_id,
        "valid": False,
        "enrichment": {},
        "mismatch_flag": False,
        "entity_status": "Match",
        "entity_resolution_confidence": "High",
        "cache_hit": False,
        "cache_data": None,
        "routing_tier": "Unknown / Tiny",
        "tool_budget": [],
        "reports": {},
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

    from src.utils.logger import start_run_logging
    start_run_logging(rule_id, company_name)

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    if not final_state.get("valid"):
        raise HTTPException(status_code=400, detail="The input company name or domain is invalid.")

    return format_analysis_response(final_state, company_name, domain)

@app.post("/api/analyze/stream")
async def analyze_company_stream(req: AnalysisRequest):
    rule_id = "cyber_risk_rating"
    company_name = req.company.strip()
    domain = req.domain.strip()

    if not company_name or not domain:
        raise HTTPException(status_code=400, detail="Company and domain are required")

    # Compile the LangGraph workflow
    graph = build_cyber_risk_rating_graph(enable_cache=True)

    # Initial State
    initial_state = {
        "company_name": company_name,
        "domain": domain,
        "rule_id": rule_id,
        "valid": False,
        "enrichment": {},
        "mismatch_flag": False,
        "entity_status": "Match",
        "entity_resolution_confidence": "High",
        "cache_hit": False,
        "cache_data": None,
        "routing_tier": "Unknown / Tiny",
        "tool_budget": [],
        "reports": {},
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

    from src.utils.logger import start_run_logging
    start_run_logging(rule_id, company_name)

    async def event_generator():
        final_state = None
        try:
            # Yield step 1: Initialized
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'node': 'initial', 'status': 'done'})}\n\n"
            
            async for event in graph.astream_events(initial_state, version="v2"):
                event_kind = event.get("event")
                
                # Check for node/chain ending
                if event_kind == "on_chain_end":
                    node = event.get("metadata", {}).get("langgraph_node")
                    if node:
                        step = None
                        if node == "supervisor_node":
                            step = 2
                        elif node in ["wiki", "wikidata", "sec", "dnb", "domain", "responses"]:
                            step = 3
                        elif node == "coordinator":
                            step = 4
                        elif node == "fact_checker":
                            step = 5
                        elif node == "underwriter":
                            step = 6
                            
                        if step is not None:
                            yield f"data: {json.dumps({'type': 'step', 'step': step, 'node': node, 'status': 'done'})}\n\n"
                            
                # Capture the final result from the root LangGraph chain ending
                if event_kind == "on_chain_end" and not event.get("metadata", {}).get("langgraph_node"):
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict) and "risk_category" in output and "confidence_score" in output:
                        final_state = output
            
            if final_state:
                if not final_state.get("valid"):
                    yield f"data: {json.dumps({'type': 'error', 'message': 'The input company name or domain is invalid.'})}\n\n"
                else:
                    formatted = format_analysis_response(final_state, company_name, domain)
                    from src.utils.logger import get_agent_logger
                    get_agent_logger("API").info("START API Return")
                    yield f"data: {json.dumps({'type': 'result', 'step': 7, 'data': formatted})}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Graph execution completed without final state.'})}\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Graph execution failed: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")