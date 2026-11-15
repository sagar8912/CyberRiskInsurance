
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.graph import build_workflow

app = FastAPI(
    title="Cyber Risk Auto Underwriter API",
    description="Multi-agent cyber risk assessment using LangGraph",
    version="1.0.0"
)

# Build the workflow once when the application starts
workflow = build_workflow()


class CompanyRequest(BaseModel):
    company_name: str = Field(min_length=1)
    domain: str = Field(min_length=1)


@app.get("/")
def home():
    return {
        "message": "Cyber Risk Auto Underwriter API is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze")
def analyze_company(request: CompanyRequest):

    company_name = request.company_name.strip()
    domain = request.domain.strip()

    if not company_name or not domain:
        raise HTTPException(
            status_code=400,
            detail="Company name and domain are required"
        )

    initial_state = {
        "company_name": company_name,
        "domain": domain,
        "valid": False,
        "enrichment": {},
        "mismatch_flag": False,
        "entity_status": "Match",
        "entity_resolution_confidence": "High",
        "cache_hit": False,
        "cache_data": None,
        "routing_tier": "Unknown / Tiny",
        "tool_budget": [],
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
        final_state = workflow.invoke(initial_state)

        return {
            "company_name": company_name,
            "domain": domain,
            "valid": final_state.get("valid"),
            "entity_status": final_state.get("entity_status"),
            "risk_category": final_state.get("risk_category"),
            "confidence_score": final_state.get("confidence_score"),
            "confidence_band": final_state.get("confidence_band"),
            "human_escalation_flag": final_state.get(
                "human_escalation_flag"
            ),
            "reconciled_profile": final_state.get(
                "reconciled_profile", {}
            ),
            "claims_verification": final_state.get(
                "claims_verification", {}
            ),
            "modifier_scores": final_state.get(
                "modifier_scores", {}
            ),
            "underwriting_rationale": final_state.get(
                "underwriting_rationale", {}
            ),
            "collected_evidence": final_state.get(
                "collected_evidence", {}
            ),
            "audit_logs": final_state.get("audit_logs", [])
        }

    except Exception:
        # Log the full exception securely in production.
        raise HTTPException(
            status_code=500,
            detail="Company risk analysis failed. Check application logs."
        )
