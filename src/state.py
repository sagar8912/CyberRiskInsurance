from typing import TypedDict, List, Dict, Any, Optional

class CyberRiskState(TypedDict):
    # Inputs
    company_name: str
    domain: str
    
    # Supervisor / Validation
    valid: bool
    enrichment: Dict[str, Any]       # Auto-detected country, TLD, etc.
    mismatch_flag: bool              # Entity mismatch flag
    cache_hit: bool
    cache_data: Optional[Dict[str, Any]]
    
    # Router / Tiered Strategy
    routing_tier: str                # e.g., "Public / $500M+", "$50M - $500M", "<$50M", "Unknown / Tiny"
    tool_budget: List[str]           # List of collector tools allowed for this run
    
    # Collectors Outputs (Evidence Reports)
    collected_evidence: Dict[str, Any]
    
    # Coordinator (Unified Profile)
    reconciled_profile: Dict[str, Any]
    conflict_flags: List[Dict[str, Any]]
    
    # Fact Checker
    claims_verification: Dict[str, Any]  # status (OK/I/X) and source counts for claims
    accuracy_score: float                # 0.0 to 1.0 overall accuracy estimate
    
    # Underwriter Decision
    risk_category: str
    underwriting_rationale: Dict[str, str] # justification for each modifier
    modifier_scores: Dict[str, Any]        # raw scores/ratings calculated for each modifier
    confidence_score: float                # final numerical score
    confidence_band: str                   # e.g., "High", "Medium", "Low"
    human_escalation_flag: bool
    
    # Audit trail
    audit_logs: List[str]
