import os
import sys

# Ensure project root is always in sys.path
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

# Automatically load environment variables from .env file
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(_env_path, override=True)
except ImportError:
    env_file = os.path.join(_project_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

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

from typing import Optional
class AnalysisRequest(BaseModel):
    company: str
    domain: str
    run_id: Optional[str] = None

import threading
import time

# Thread-safe in-memory status cache for fallback polling resiliency with configurable TTL
CACHE_TTL_SECONDS = int(os.getenv("RUN_STATUS_CACHE_TTL", "3600"))  # Default: 3600s (60 minutes)

from src.utils.run_status import run_status_cache, RunStatusCacheManager


@app.on_event("startup")
async def start_cache_cleanup_task():
    async def periodic_cleanup():
        while True:
            await asyncio.sleep(300)  # Lightweight check every 5 minutes
            try:
                run_status_cache.cleanup_expired()
            except Exception as e:
                pass
    asyncio.create_task(periodic_cleanup())

@app.get("/api/run-status/{run_id}")
@app.get("/run-status/{run_id}")
async def get_run_status(run_id: str):
    logger = run_status_cache._get_logger()
    logger.info(f"[RunStatusCache] Poll request received for run_id={run_id}")
    data = run_status_cache.get_run(run_id)
    if not data:
        logger.warning(
            f"[RunStatusCache] Cache miss for run_id={run_id}. "
            f"Explanation: The requested run_id does not exist in the active cache. "
            f"Why this happens: (1) The initial POST /api/analyze/stream request failed or was aborted before initializing the run on the backend, "
            f"(2) The run completed/failed and exceeded the {run_status_cache.ttl_seconds}s TTL and was removed by cleanup, "
            f"or (3) An invalid run_id was provided."
        )
        raise HTTPException(
            status_code=404,
            detail=f"Run ID '{run_id}' not found in active cache. It may have expired after TTL or failed to initialize."
        )
    logger.info(f"[RunStatusCache] Cache hit for run_id={run_id}, status={data.get('status')}, step={data.get('step')}")
    return data

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
@app.post("/analyze")
async def analyze_company(req: AnalysisRequest):
    import uuid, time
    rule_id = "cyber_risk_rating"
    company_name = req.company.strip()
    domain = req.domain.strip()
    run_id = req.run_id or f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    if not company_name or not domain:
        raise HTTPException(status_code=400, detail="Company and domain are required")

    run_status_cache.create_run(run_id, company_name, domain)

    # Compile the LangGraph workflow
    graph = build_cyber_risk_rating_graph(enable_cache=True)

    # Initial State
    initial_state = {
        "run_id": run_id,
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
        run_status_cache.fail_run(run_id, str(e))
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    if not final_state.get("valid"):
        run_status_cache.fail_run(run_id, "Invalid company name or domain")
        raise HTTPException(status_code=400, detail="The input company name or domain is invalid.")

    res = format_analysis_response(final_state, company_name, domain)
    run_status_cache.complete_run(run_id, 7, res)
    return res

@app.post("/api/analyze/stream")
@app.post("/analyze/stream")
async def analyze_company_stream(req: AnalysisRequest):
    import uuid, time
    rule_id = "cyber_risk_rating"
    company_name = req.company.strip()
    domain = req.domain.strip()
    run_id = req.run_id or f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    if not company_name or not domain:
        raise HTTPException(status_code=400, detail="Company and domain are required")

    run_status_cache.create_run(run_id, company_name, domain)

    # Compile the LangGraph workflow
    graph = build_cyber_risk_rating_graph(enable_cache=True)

    # Initial State
    initial_state = {
        "run_id": run_id,
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

    from src.utils.logger import start_run_logging, get_agent_logger
    start_run_logging(rule_id, company_name)
    api_logger = get_agent_logger("API")
    api_logger.info(f"Streaming request received for company: {company_name}, domain: {domain}, run_id: {run_id}")

    async def event_generator():
        final_state = None
        queue = asyncio.Queue()

        async def run_graph_stream():
            api_logger.info(f"[ASYNC TASK START] run_graph_stream for {company_name}")
            t_task = time.time()
            nonlocal final_state
            try:
                async for event in graph.astream_events(initial_state, version="v2"):
                    t_put_start = time.time()
                    await queue.put({"kind": "event", "data": event})
                    t_put_end = time.time()
                    if (t_put_end - t_put_start) > 0.1:
                        api_logger.warning(f"[QUEUE PUT] Slow put for event {event.get('event')}: {t_put_end - t_put_start:.3f}s")
            except asyncio.TimeoutError as e:
                api_logger.error(f"[ASYNC TASK TIMEOUT] run_graph_stream timed out for {company_name}: {e}")
                await queue.put({"kind": "error", "error": e})
            except Exception as e:
                api_logger.error(f"[ASYNC TASK FAILED] run_graph_stream failed for {company_name}: {type(e).__name__} - {e}")
                await queue.put({"kind": "error", "error": e})
            finally:
                elapsed_task = time.time() - t_task
                api_logger.info(f"[ASYNC TASK END] run_graph_stream for {company_name} (elapsed {elapsed_task:.2f}s)")
                await queue.put(None)


        stream_task = asyncio.create_task(run_graph_stream())
        api_logger.info(f"[{time.time():.3f}] [SSE STREAM OPENED] Stream opened for {company_name} (run_id: {run_id})")

        try:
            # Yield step 1: Initialized
            ts = time.time()
            run_status_cache.update_run(run_id, step=1, node="initial")
            api_logger.info(f"[{ts:.3f}] [SSE YIELD] Emitting step=1, node=initial")
            yield f"data: {json.dumps({'type': 'step', 'step': 1, 'node': 'initial', 'status': 'done', 'run_id': run_id})}\n\n"
            api_logger.info(f"[{time.time():.3f}] [SSE FLUSHED] Chunk sent to ASGI transport for step=1, node=initial")
            
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=1.5)
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive and defeat reverse proxy buffering
                    hb_time = int(time.time())
                    api_logger.debug(f"[{time.time():.3f}] [SSE YIELD] Emitting heartbeat {hb_time}")
                    yield f": heartbeat {hb_time}\n\n"
                    api_logger.debug(f"[{time.time():.3f}] [SSE FLUSHED] Heartbeat chunk sent to ASGI transport")
                    continue

                if msg is None:
                    break

                if msg.get("kind") == "error":
                    raise msg["error"]

                event = msg["data"]
                event_kind = event.get("event")
                
                # Check for node/chain ending
                if event_kind in ("on_chain_start", "on_chain_end"):
                    node = event.get("metadata", {}).get("langgraph_node") or event.get("name", "")
                    if node:
                        step = None
                        node_for_log = node
                        if node in ("supervisor_node", "supervisor"):
                            step = 2
                            node_for_log = "supervisor_node"
                        elif node in ("coordinator", "coordinator_node", "census_naics", "census_naics_node"):
                            step = 4
                            node_for_log = "coordinator_node"
                        elif node in ("fact_checker", "fact_checker_node"):
                            step = 5
                            node_for_log = "fact_checker_node"
                        elif node in ("underwriter", "underwriter_node"):
                            step = 6
                            node_for_log = "underwriter_node"
                        elif not node.startswith("__") and not any(k in node for k in ("coordinator", "fact_checker", "underwriter", "supervisor", "census_naics", "langgraph", "channel", "edge")):
                            step = 3
                            node_for_log = "collector_node"
                            
                        if step is not None:
                            ts = time.time()
                            run_status_cache.update_run(run_id, step=step, node=node_for_log)
                            api_logger.info(f"[{ts:.3f}] [SSE YIELD] Emitting step={step}, node={node_for_log}")
                            yield f"data: {json.dumps({'type': 'step', 'step': step, 'node': node_for_log, 'status': 'done', 'run_id': run_id})}\n\n"
                            api_logger.info(f"[{time.time():.3f}] [SSE FLUSHED] Chunk sent to ASGI transport for step={step}, node={node_for_log}")
                            
                # Capture the final result from the root LangGraph chain ending
                if event_kind == "on_chain_end" and not event.get("metadata", {}).get("langgraph_node"):
                    output = event.get("data", {}).get("output")
                    if isinstance(output, dict) and "risk_assessment" in output and "risk_category" in output:
                        final_state = output
            
            if final_state:
                if not final_state.get("valid"):
                    run_status_cache.fail_run(run_id, "Invalid company name or domain")
                    api_logger.warning("Streaming event error: Input company or domain invalid")
                    yield f"data: {json.dumps({'type': 'error', 'message': 'The input company name or domain is invalid.'})}\n\n"
                else:
                    formatted = format_analysis_response(final_state, company_name, domain)
                    ts = time.time()
                    run_status_cache.complete_run(run_id, 7, formatted)
                    api_logger.info(f"[{ts:.3f}] [SSE YIELD] Emitting step=7, result=success")
                    yield f"data: {json.dumps({'type': 'result', 'step': 7, 'data': formatted, 'run_id': run_id})}\n\n"
                    api_logger.info(f"[{time.time():.3f}] [SSE FLUSHED] Chunk sent to ASGI transport for step=7, result=success")
            else:
                run_status_cache.fail_run(run_id, "Graph execution completed without final state")
                api_logger.error("Streaming event error: Graph completed without final state")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Graph execution completed without final state.'})}\n\n"
                
        except Exception as e:
            error_msg = str(e) or type(e).__name__
            run_status_cache.fail_run(run_id, f"Error: {error_msg}")
            api_logger.error(f"Streaming event exception: {type(e).__name__} - {error_msg}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Graph execution failed: {error_msg}'})}\n\n"
        except asyncio.TimeoutError as e:
            run_status_cache.fail_run(run_id, "TimeoutError: Graph execution timed out")
            api_logger.error(f"Streaming event exception: TimeoutError")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Graph execution failed: TimeoutError'})}\n\n"

        finally:
            api_logger.info(f"[{time.time():.3f}] [SSE STREAM CLOSED] Streaming connection closed for {company_name}")

    headers = {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=headers)