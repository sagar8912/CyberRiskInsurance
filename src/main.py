import sys
import argparse
from src.graph import build_workflow

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, "="))
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Cyber Risk Underwriting Predictor (LangGraph Local CLI)")
    parser.add_argument("-n", "--name", required=True, help="Company name to evaluate")
    parser.add_argument("-d", "--domain", required=True, help="Company primary domain (e.g. example.com)")
    
    args = parser.parse_args()
    company_name = args.name.strip()
    domain = args.domain.strip()

    print_header("Initializing Cyber Risk Predictor")
    print(f"Company Target: {company_name}")
    print(f"Primary Domain: {domain}")

    # Compile the graph
    app = build_workflow()

    # Initial State
    initial_state = {
        "company_name": company_name,
        "domain": domain,
        "valid": False,
        "enrichment": {},
        "mismatch_flag": False,
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

    # Run the graph
    try:
        final_state = app.invoke(initial_state)
    except Exception as e:
        print(f"\n[ERROR] Graph execution failed: {e}")
        sys.exit(1)

    # 1. Check early validation reject
    if not final_state.get("valid"):
        print_header("Validation Failed")
        print("[REJECTED] The input company name or domain is invalid or blank.")
        for log in final_state.get("audit_logs", []):
            print(f"  > {log}")
        sys.exit(0)

    # 2. Print Audit logs
    print_header("Execution Trace & Logs")
    for log in final_state.get("audit_logs", []):
        print(f"  > {log}")

    # 3. Check Cache Hit vs Normal Run output
    if final_state.get("cache_hit"):
        print_header("Cache Lookup Outcome")
        print("[CACHE HIT] Returning verified record from database...")
        cache_data = final_state.get("cache_data", {})
        
        print(f"\nFinal Risk Category:   {cache_data.get('risk_category')}")
        print(f"Confidence Rating:     {cache_data.get('confidence_score')}% ({cache_data.get('confidence_band')})")
        print(f"Escalate to Human:     {cache_data.get('human_escalation_flag')}")
        
        print("\nModifier Scores:")
        for mod, details in cache_data.get("modifier_scores", {}).items():
            print(f"  - {mod}: {details.get('rating').upper()} (Score: {details.get('score')})")
            print(f"    Rationale: {cache_data.get('underwriting_rationale', {}).get(mod)}")
        sys.exit(0)

    # 4. Standard Run results
    reconciled = final_state.get("reconciled_profile", {})
    print_header("Reconciled Company Profile")
    print(f"Reconciled Revenue:   ${reconciled.get('revenue', 0):,}")
    print(f"Subsidiaries Count:   {len(reconciled.get('subsidiaries', []))}")
    print(f"Acquisitions Count:   {len(reconciled.get('acquisitions', []))}")
    print(f"Customer Type:        {reconciled.get('customer_type')}")
    print(f"E-commerce Platform:  {reconciled.get('has_ecommerce')}")
    print(f"Countries of Ops:     {', '.join(reconciled.get('countries_of_operation', []))}")
    print(f"Privacy Policy:       {reconciled.get('privacy_policy_published')}")

    print_header("Fact Checker Corroboration Claims")
    print(f"{'Underwriting Claim':<30} | {'Status':<15} | {'Source Count':<12}")
    print("-" * 65)
    for claim, info in final_state.get("claims_verification", {}).items():
        print(f"{claim:<30} | {info['status']:<15} | {info['sources_count']:<12}")

    print_header("Underwriter Modifier Evaluations")
    for mod, details in final_state.get("modifier_scores", {}).items():
        print(f"  * {mod}: {details.get('rating').upper()} (Score: {details.get('score')})")
        print(f"    Rationale: {final_state.get('underwriting_rationale', {}).get(mod)}")

    print_header("Final Underwriting Modifier Verdict")
    print(f"Risk Category:       {final_state.get('risk_category').upper()}")
    print(f"Underwriting Score:  {final_state.get('confidence_score')}%")
    print(f"Confidence Band:     {final_state.get('confidence_band')}")
    print(f"Human Escalation:    {final_state.get('human_escalation_flag')}")

if __name__ == "__main__":
    main()
