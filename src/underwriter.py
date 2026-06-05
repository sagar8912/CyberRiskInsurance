from typing import Dict, Any
from src.state import CyberRiskState
from src.utils.excel_parser import ExcelParser
from src.utils.rules_engine import CyberRulesEngine
from src.utils.cache_manager import CacheManager

RATING_SCORES = {
    "very favourable": 1.0,
    "favourable": 2.0,
    "partially favourable": 3.0,
    "average": 4.0,
    "partially unfavourable": 5.0,
    "unfavourable": 6.0
}

def underwriter_node(state: CyberRiskState) -> Dict[str, Any]:
    reconciled = state.get("reconciled_profile", {})
    accuracy = state.get("accuracy_score", 1.0)
    mismatch = state.get("mismatch_flag", False)
    conflicts = state.get("conflict_flags", [])
    logs = []
    
    logs.append("Underwriter: Parsing Excel guidelines and executing rules engine...")
    
    # 1. Initialize Excel Parser and Rules Engine
    parser = ExcelParser()
    rules_engine = CyberRulesEngine(parser=parser)
    
    # 2. Calculate Modifier Ratings
    modifier_results = rules_engine.calculate_modifiers(reconciled)
    
    # 3. Aggregate Final Risk Category
    numeric_scores = []
    underwriting_rationale = {}
    modifier_scores = {}
    
    for name, res in modifier_results.items():
        rating = res["rating"].lower()
        score_val = RATING_SCORES.get(rating, 4.0)
        numeric_scores.append(score_val)
        
        underwriting_rationale[name] = res["rationale"]
        modifier_scores[name] = {
            "score": res["score"],
            "rating": res["rating"]
        }
        
    avg_score = sum(numeric_scores) / len(numeric_scores) if numeric_scores else 4.0
    
    # Map back to risk category
    if avg_score < 2.0:
        risk_category = "Very Favourable"
    elif avg_score < 3.0:
        risk_category = "Favourable"
    elif avg_score < 4.0:
        risk_category = "Partially Favourable"
    elif avg_score < 4.5:
        risk_category = "Average"
    elif avg_score < 5.5:
        risk_category = "Partially Unfavourable"
    else:
        risk_category = "Unfavourable"
        
    logs.append(f"Underwriter: Aggregated Average Score = {avg_score:.2f} -> Risk Category: '{risk_category}'")

    # 4. Confidence Score & Band based on Fact Checker accuracy
    confidence_score = float(round(accuracy * 100.0, 1))
    if accuracy >= 0.8:
        confidence_band = "High"
    elif accuracy >= 0.5:
        confidence_band = "Medium"
    else:
        confidence_band = "Low"
        
    logs.append(f"Underwriter: Fact-checking Accuracy = {accuracy:.2f} -> Confidence: {confidence_score}% ({confidence_band})")

    # 5. Human-in-the-Loop Escalation Logic
    # Trigger if: accuracy < 50%, entity mismatch, or active contradictions
    human_escalation_flag = False
    reasons = []
    if accuracy < 0.5:
        human_escalation_flag = True
        reasons.append(f"Accuracy score ({accuracy:.2f}) below 50% threshold.")
    if mismatch:
        human_escalation_flag = True
        reasons.append("Supervisor flagged entity mismatch.")
    if len(conflicts) > 0:
        human_escalation_flag = True
        reasons.append(f"Active source contradictions detected: {len(conflicts)}")
        
    if human_escalation_flag:
        logs.append(f"Underwriter Escalation: Human routing triggered! Reasons: {reasons}")
    else:
        logs.append("Underwriter: Auto-approval path verified. No human escalation needed.")

    # 6. Cache Write
    profile_summary = {
        "risk_category": risk_category,
        "underwriting_rationale": underwriting_rationale,
        "modifier_scores": modifier_scores,
        "confidence_score": confidence_score,
        "confidence_band": confidence_band,
        "accuracy_score": accuracy,
        "human_escalation_flag": human_escalation_flag,
        "reconciled_profile": reconciled
    }
    
    # Only write to cache if it wasn't a cache hit and the data is valid
    if state.get("valid") and not state.get("cache_hit"):
        cache_mgr = CacheManager()
        cache_mgr.write(state.get("company_name"), state.get("domain"), profile_summary)
        logs.append("Underwriter: Saved final evaluation profile and aliases to cache database.")

    return {
        "risk_category": risk_category,
        "underwriting_rationale": underwriting_rationale,
        "modifier_scores": modifier_scores,
        "confidence_score": confidence_score,
        "confidence_band": confidence_band,
        "human_escalation_flag": human_escalation_flag,
        "audit_logs": state.get("audit_logs", []) + logs
    }
