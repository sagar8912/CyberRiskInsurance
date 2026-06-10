import os
import asyncio
from fastapi import FastAPI, HTTPException
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
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    company: str
    domain: str

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

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

    if not final_state.get("valid"):
        raise HTTPException(status_code=400, detail="The input company name or domain is invalid.")

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
    modifiers_formatted = []
    idx = 1
    for mod_name, details in modifier_scores.items():
        score_str = str(details.get("score", "0.0"))
            
        modifiers_formatted.append({
            "id": idx,
            "name": mod_name,
            "rating": details.get("rating", "Average").upper(),
            "score": score_str,
            "rationale": rationales.get(mod_name, "No rationale provided.")
        })
        idx += 1

    # Format Final Verdict
    final_verdict = {
        "riskCategory": final_state.get("risk_category", "Average").upper(),
        "underwritingScore": f"{final_state.get('confidence_score', 0)}%",
        "confidenceBand": final_state.get("confidence_band", "Low"),
        "humanEscalation": final_state.get("human_escalation_flag", False)
    }

    return {
        "target_entity": {"name": company_name, "domain": domain},
        "workflow_trace": final_state.get("audit_logs", []),
        "reconciled_profile": reconciled_profile_formatted,
        "fact_checker_claims": fact_checker_claims,
        "modifiers": modifiers_formatted,
        "final_verdict": final_verdict
    }
