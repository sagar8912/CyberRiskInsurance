import os
import sys
import asyncio
import argparse
from src.registry import BusinessRuleRegistry
from src.workflows import build_cyber_risk_rating_graph
from src.cache import get_cache_manager

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title.upper()} ".center(60, "="))
    print("=" * 60)

async def main_async():
    # Load all rules to trigger registration
    import src.rules as _rules

    parser = argparse.ArgumentParser(description="Shared Agent Framework CLI")
    parser.add_argument("--list-rules", action="store_true", help="List all registered rules")
    parser.add_argument("--rule", type=str, help="Rule ID to run (e.g. cyber_risk_rating)")
    parser.add_argument("--company", type=str, help="Company name to evaluate")
    parser.add_argument("--domain", type=str, help="Company domain (e.g. techgiant.com)")
    parser.add_argument("--report", action="store_true", help="Generate HTML underwriting audit report")
    
    args = parser.parse_args()

    if args.list_rules:
        print_header("Registered Rules")
        rules = BusinessRuleRegistry.list_rules()
        for r in rules:
            cfg = BusinessRuleRegistry.get(r)
            print(f"- {cfg.rule_id}: {cfg.rule_name} ({cfg.description})")
        sys.exit(0)

    if not args.rule or not args.company or not args.domain:
        parser.print_help()
        sys.exit(1)

    rule_id = args.rule.strip()
    company_name = args.company.strip()
    domain = args.domain.strip()

    if rule_id != "cyber_risk_rating":
        print(f"[ERROR] Rule ID '{rule_id}' is not supported in the active configuration.")
        sys.exit(1)

    print_header("Initializing Cyber Risk Predictor")
    print(f"Rule Target:    {rule_id}")
    print(f"Company Target: {company_name}")
    print(f"Primary Domain: {domain}")

    # Compile the LangGraph workflow
    app = build_cyber_risk_rating_graph(enable_cache=True)

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
        final_state = await app.ainvoke(initial_state)
    except Exception as e:
        print(f"\n[ERROR] Graph execution failed: {e}")
        sys.exit(1)

    # 1. Validation check
    if not final_state.get("valid"):
        print_header("Validation Failed")
        print("[REJECTED] The input company name or domain is invalid.")
        for log in final_state.get("audit_logs", []):
            print(f"  > {log}")
        sys.exit(0)

    # 2. Print Trace & Audit Logs
    print_header("Execution Trace & Logs")
    for log in final_state.get("audit_logs", []):
        print(f"  > {log}")

    # 3. Print Results
    evidence = final_state.get("collected_evidence", {})
    real_sources = []
    for tool_name, data in evidence.items():
        if data.get("status") == "success":
            real_sources.append(tool_name)

    print_header("Collectors Run")
    print("Real Sources Used:")
    print(f"{', '.join(real_sources) if real_sources else 'None'}")

    reconciled = final_state.get("reconciled_profile", {})
    print_header("Reconciled Company Profile")
    rev = reconciled.get('revenue')
    rev_display = f"${rev:,}" if rev is not None else "Not Available"
    print(f"Reconciled Revenue:   {rev_display}")
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
        print(f"{claim:<30} | {info.get('status', 'Unsupported'):<15} | {info.get('sources_count', 0):<12}")

    print_header("Underwriter Modifier Evaluations")
    for idx, (mod, details) in enumerate(final_state.get("modifier_scores", {}).items(), 1):
        rating_str = details.get('rating').upper()
        if mod in [
            "Amount of sensitive information",
            "Applicability of Privacy Regulation",
            "B2C End Products",
            "Seasonality of sales"
        ]:
            print(f"  {idx}. {mod}: {rating_str}")
        else:
            print(f"  {idx}. {mod}: {rating_str} (Score: {details.get('score')})")
        print(f"     Rationale: {final_state.get('underwriting_rationale', {}).get(mod)}")

    print_header("Final Underwriting Verdict Report")
    
    # Calculate Risk Category evaluation metrics
    rating_scores_map = {
        "very favourable": 1.0,
        "favourable": 2.0,
        "partially favourable": 3.0,
        "average": 4.0,
        "partially unfavourable": 5.0,
        "unfavourable": 6.0
    }
    scores_list = []
    for mod, details in final_state.get("modifier_scores", {}).items():
        rat = details.get("rating", "average").lower()
        val = rating_scores_map.get(rat, 4.0)
        scores_list.append(val)
        
    sum_scores = sum(scores_list) if scores_list else 0.0
    avg_score = sum_scores / len(scores_list) if scores_list else 4.0
    
    risk_cat = final_state.get('risk_category', 'Average').upper()
    accuracy_score = final_state.get('confidence_score', 0.0)
    conf_band = final_state.get('confidence_band', 'Low').upper()
    
    escalation_flag = final_state.get('human_escalation_flag', False)
    if escalation_flag:
        esc_status = "HUMAN ESCALATION REQUIRED"
        if accuracy_score < 50.0:
            esc_reason = f"Automatically triggered because the corroboration Underwriting Score ({accuracy_score:.1f}%) is below 50.0%."
        elif final_state.get('mismatch_flag'):
            esc_reason = "Automatically triggered because an entity name or domain mismatch was detected."
        else:
            esc_reason = "Automatically triggered due to discrepancy flags or conflict warnings detected between sources."
    else:
        esc_status = "NO ESCALATION REQUIRED"
        esc_reason = "All underwriting data is verified with sufficient confidence."

    company_display = company_name[:32] + "..." if len(company_name) > 35 else company_name
    lines = [
        f"  Target Company:      {company_display}",
        f"  Risk Category:       {risk_cat}",
        f"  Average Score:       {avg_score:.3f} / 6.0",
        f"  Underwriting Score:  {accuracy_score:.1f}% ({conf_band})",
        f"  Escalation Status:   {esc_status}"
    ]

    print("┌──────────────────────────────────────────────────────────┐")
    print("│              UNDERWRITING DECISION SUMMARY               │")
    print("├──────────────────────────────────────────────────────────┤")
    for line in lines:
        print(f"│ {line:<56} │")
    print("└──────────────────────────────────────────────────────────┘")
    print("")
    
    print("--------------- STEPS & DETAILED CALCULATIONS ---------------")
    
    # Step 1: Entity Validation
    ent_status = final_state.get('entity_status', 'Match')
    ent_details = "Company name aligns with the primary domain slug and registrar records." if ent_status == "Match" else "Company name or domain mismatch detected during supervisor analysis."
    print("1. Entity Validation:")
    print(f"   - Status:  {ent_status.upper()}")
    print(f"   - Details: {ent_details}")
    print("")
    
    # Step 2: Risk Category Evaluation
    if avg_score < 1.5: range_str = "Very Favourable range of < 1.5"
    elif avg_score < 2.5: range_str = "Favourable range of 1.5 to 2.5"
    elif avg_score < 3.5: range_str = "Partially Favourable range of 2.5 to 3.5"
    elif avg_score < 4.5: range_str = "Average range of 3.5 to 4.5"
    elif avg_score < 5.5: range_str = "Partially Unfavourable range of 4.5 to 5.5"
    else: range_str = "Unfavourable range of > 5.5"
    
    print("2. Risk Category Evaluation (13 Modifiers):")
    print(f"   - Math:    Sum of scores ({sum_scores:.1f}) / 13 Modifiers = {avg_score:.3f} Average")
    print(f"   - Verdict: {risk_cat} (Average falls in the {range_str})")
    print("")
    
    # Step 3: Data Verification & Underwriting Score
    verified_claims = 0
    partially_verified_claims = 0
    unsupported_claims = 0
    verified_names = []
    partially_names = []
    unsupported_names = []
    
    for claim, info in final_state.get("claims_verification", {}).items():
        status = info.get("status", "Unsupported").lower()
        if "partial" in status:
            partially_verified_claims += 1
            partially_names.append(claim)
        elif "verified" in status or "ok" in status:
            verified_claims += 1
            verified_names.append(claim)
        else:
            unsupported_claims += 1
            unsupported_names.append(claim)
            
    total_claims = len(final_state.get("claims_verification", {}))
    
    print("3. Data Verification & Underwriting Score:")
    print(f"   - Claims:  {verified_claims} Verified, {partially_verified_claims} Partially Verified, {unsupported_claims} Unsupported")
    print(f"   - Math:    ({verified_claims:.1f} Verified + {partially_verified_claims * 0.5:.1f} Partially Verified) / {total_claims} total claims = {accuracy_score:.1f}%")
    print(f"   - Verdict: {accuracy_score:.1f}% (Confidence Band: {conf_band})")
    print("")
    
    # Step 4: Referral & Human Escalation
    print("4. Referral & Human Escalation:")
    print(f"   - Status:  {esc_status}")
    print(f"   - Reason:  {esc_reason}")
    print("────────────────────────────────────────────────────────────")

    # Write Cache on success
    if final_state.get("valid") and not final_state.get("cache_hit"):
        cache_mgr = get_cache_manager()
        profile_summary = {
            "collected_evidence": final_state.get("collected_evidence", {}),
            "cache_type": "collector_cache"
        }
        cache_mgr.write(company_name, domain, profile_summary)
        print("\n> Saved raw collector evidence to cache database.")

    if args.report:
        from reports.report_generator import generate_underwriting_audit_report
        report_path = generate_underwriting_audit_report(final_state, company_name, domain, rule_id)
        print(f"\nAudit report generated: {report_path}")


def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
