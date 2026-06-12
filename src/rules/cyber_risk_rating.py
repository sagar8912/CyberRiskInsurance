from src.config import (
    BusinessRuleConfig,
    CollectorAgentConfig,
    CoordinatorConfig,
    FactCheckerConfig,
    UnderwriterConfig,
    PromptTemplate
)
from src.registry import BusinessRuleRegistry

# Rule ID
RULE_ID = "cyber_risk_rating"

# Collectors configs
WIKIPEDIA_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following Wikipedia text for {company_name} ({domain}) and extract findings.
Wikipedia Text:
{wikipedia_text}

{format_instructions}
Your output JSON must contain:
- "subsidiaries": list of string names of subsidiaries mentioned.
- "acquisitions": list of objects representing acquisitions made, each with "deal_type" (string, e.g. "minor acquisition", "material acquisition", "transitional acquisition") and "recency_years" (number, float). Use an empty list if none are mentioned.
- "customer_type": "B2B" or "B2C" or "MIX" or null.
- "has_ecommerce": boolean or null (whether they sell products/services online directly via digital checkout).
- "country": string name of the primary country mentioned (e.g. USA, India).
- "founding_year": numerical year when the company was founded (e.g. 1998), or null if not found.
""",
    required_vars=["company_name", "domain", "wikipedia_text"]
)

WIKIPEDIA = CollectorAgentConfig(
    name="Wikipedia Collector",
    agent_type="wikipedia",
    prompt_template=WIKIPEDIA_PROMPT,
    target_fields=["subsidiaries", "acquisitions", "customer_type", "has_ecommerce", "country", "founding_year"],
    source_name="Wikipedia"
)

WIKIDATA_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following raw Wikidata claims JSON for {company_name} ({domain}) and extract key details.
Wikidata Context:
{wikidata_text}

{format_instructions}
Your output JSON must contain:
- "revenue": numerical value of revenue or null if not found.
- "employees": numerical value of employee count or null.
- "country": string name of primary country.
- "headquarters": string name of headquarters city.
- "industry": list of strings for industry sectors.
- "official_website": string URL.
- "subsidiaries": list of string names of subsidiaries.
- "founding_year": numerical year when the company was founded (extracted from inception property), or null if not found.
""",
    required_vars=["company_name", "domain", "wikidata_text"]
)

WIKIDATA = CollectorAgentConfig(
    name="Wikidata Collector",
    agent_type="wikidata",
    prompt_template=WIKIDATA_PROMPT,
    target_fields=["revenue", "employees", "country", "headquarters", "industry", "official_website", "subsidiaries", "founding_year"],
    source_name="Wikidata"
)

SEC_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following SEC EDGAR facts and submission data for {company_name} ({domain}) and extract findings.
SEC Context:
{sec_text}

{format_instructions}
Your output JSON must contain:
- "revenue": numerical annual revenue or null.
- "fiscal_year": numerical year of the latest 10-K (e.g., 2024).
- "subsidiaries_count": numerical count of exhibit 21 subsidiaries.
""",
    required_vars=["company_name", "domain", "sec_text"]
)

SEC = CollectorAgentConfig(
    name="SEC EDGAR Collector",
    agent_type="sec",
    prompt_template=SEC_PROMPT,
    target_fields=["revenue", "fiscal_year", "subsidiaries_count"],
    source_name="SECCollector"
)

DNB_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following GLEIF/DNB registration attributes for {company_name} ({domain}) and extract fields.
GLEIF Context:
{dnb_text}

{format_instructions}
Your output JSON must contain:
- "legal_name": string legal name.
- "country": string country code (e.g., US, IN).
- "legal_address": object address details.
- "headquarters_address": object address details.
- "registration_authority": object details.
- "legal_form": object details.
- "founding_year": numerical year extracted from incorporationDate or registrationDate, or null if not found.
""",
    required_vars=["company_name", "domain", "dnb_text"]
)

DNB = CollectorAgentConfig(
    name="D&B GLEIF Collector",
    agent_type="dnb",
    prompt_template=DNB_PROMPT,
    target_fields=["legal_name", "country", "legal_address", "headquarters_address", "registration_authority", "legal_form", "founding_year"],
    source_name="DBCollector"
)

DOMAIN_PROMPT = PromptTemplate(
    template="""You are an expert domain scraper parser.
Analyze the following connection details and homepage HTML snippet for {company_name} ({domain}) and extract key details.
Context:
{scraper_text}

{format_instructions}
Your output JSON must contain:
- "domains": list of objects, each with "url" (string) and "https_encrypted" (boolean).
- "privacy_policy_published": boolean (whether a privacy policy link or page is found in the HTML snippet or mentioned).
- "compliance_mentions": list of strings (compliance frameworks mentioned in the HTML snippet, e.g. GDPR, CCPA, HIPAA).
- "customer_type": "B2B" or "B2C" or "MIX" or null.
- "has_ecommerce": boolean (whether there are e-commerce/store/checkout indicators like shopping cart, shop, pricing, payment buttons, or catalog purchase flows in the HTML snippet).
""",
    required_vars=["company_name", "domain", "scraper_text"]
)

DOMAIN = CollectorAgentConfig(
    name="Domain Scraper",
    agent_type="domain",
    prompt_template=DOMAIN_PROMPT,
    target_fields=["domains", "privacy_policy_published", "compliance_mentions", "customer_type", "has_ecommerce"],
    source_name="DomainScraper"
)

RESPONSES = CollectorAgentConfig(
    name="Responses API Collector",
    agent_type="responses",
    prompt_template=PromptTemplate(template=""),
    target_fields=[],
    source_name="ResponsesAPI"
)

# Coordinator config
COORD_PROMPT = PromptTemplate(
    template="""You are the lead underwriting coordinator agent.
Reconcile all parallel collector findings into a single combined profile for {company_name} ({domain}).
Reports JSON:
{reports_json}

Apply priority overrides (SEC > D&B > Wikidata > Wikipedia) and resolve differences.
{format_instructions}
Output a single consolidated profile with the following fields:
- "revenue": numerical value or null.
- "customer_type": "B2B" or "B2C".
- "has_ecommerce": boolean.
- "countries_of_operation": list of strings.
- "continent_spread": list of strings.
- "privacy_policy_published": boolean.
- "compliance_mentions": list of strings (e.g., ["GDPR", "CCPA"]).
- "quarterly_revenue": list of numbers or empty list.
- "sic_codes": list of strings.
- "services_appetite": "low_risk" or "medium_risk" or "high_risk".
- "internet_exposure_domains": number of domains.
- "customer_base_scale": "SMB (<1k)" or "Mid-Market" or "Enterprise".
- "digital_exposure": number (1 to 5).
- "disruption_speed": number (1 to 5).
- "recovery_complexity": number (1 to 5).
- "founding_year": numerical year or null.
""",
    required_vars=["company_name", "domain", "reports_json"]
)

COORD = CoordinatorConfig(
    name="Collection Coordinator",
    agent_type="coordinator",
    prompt_template=COORD_PROMPT,
    collector_fields=[
        "revenue", "subsidiaries", "acquisitions", "customer_type", "has_ecommerce",
        "domains", "countries_of_operation", "privacy_policy_published", "compliance_mentions",
        "quarterly_revenue", "sic_codes", "services_appetite", "internet_exposure_domains",
        "customer_base_scale", "founding_year"
    ],
    computed_fields=["usa_presence", "continent_spread"],
    report_sources=["Wikipedia", "Wikidata", "SECCollector", "DBCollector", "DomainScraper"]
)

# Fact Checker config
FACT_PROMPT = PromptTemplate(
    template="""You are an expert fact verifier.
Check consensus for these claims: {claims_json} against the evidence reports: {evidence_snippets}.
Context Provenance: {provenance}

{format_instructions}
For each claim, determine the verification status (Verified, Partially Verified, or Unsupported).
Provide output as:
{{
  "claims_verification": {{
     "<claim_name>": {{
        "status": "Verified | Partially Verified | Unsupported",
        "sources_count": 2,
        "evidence_consensus": "brief rationale"
     }}
  }}
}}
""",
    required_vars=["claims_json", "evidence_snippets", "provenance"]
)

FACT = FactCheckerConfig(
    name="Fact Checker",
    agent_type="fact_checker",
    prompt_template=FACT_PROMPT,
    verify_fields=["revenue", "subsidiaries_count", "acquisitions_count", "customer_type", "has_ecommerce", "privacy_policy_published"]
)

# Underwriter config
UW_RULES = """
UNDERWRITING MODIFIER RULES:
1. Mergers and Acquisitions: Sum(deal points * recency multiplier) compared against company revenue tiers.
2. Amount of sensitive information: Customer Type (B2B vs B2C) + Ecommerce Presence.
3. Domain Encryption: Ratio of https encrypted domains.
4. Geographic Spread: Country count + continent count + USA presence vs revenue tier.
5. Internet footprint: Domains count * Scale Multiplier (SMB=1, Mid-Market=2, Enterprise=3).
6. Nature of services: Appetite category (low_risk=favourable, high_risk=unfavourable).
7. Organizational Complexity: Subsidiary count vs revenue tier.
8. Privacy Regulation: Policy published + Compliance frameworks count.
9. Seasonality of sales: CV of quarterly revenue (CV < 0.1 Favourable, > 0.25 Unfavourable) or SIC benchmark.
10. Volatility/Recovery in Sales: Avg of digital exposure, disruption speed, recovery complexity.
11. Applicability of Privacy Regulation: Operates in strict regions (GDPR, CCPA) or has e-commerce.
12. B2C End Products: B2C = average risk, B2B = favourable.
13. Years in business: founding year vs current year compared against revenue-tier thresholds.
"""

UW_PROMPT = PromptTemplate(
    template="""You are the final underwriting decision agent.
Apply the guidelines:
{business_rule}

Evaluate this reconciled profile:
{inputs_json}

Fact checking results:
{fact_check_summary}

{format_instructions}
Output your qualitative assessment and underwriting rationale as a JSON block:
{{
  "risk_category": "Very Favourable | Favourable | Partially Favourable | Average | Partially Unfavourable | Unfavourable",
  "underwriting_rationale": {{
     "<modifier_name>": "brief textual explanation for this modifier"
  }}
}}
""",
    required_vars=["business_rule", "inputs_json", "fact_check_summary"]
)

UW = UnderwriterConfig(
    name="Underwriter",
    agent_type="underwriter",
    business_rule=UW_RULES,
    prompt_template=UW_PROMPT,
    input_fields=[
        "revenue", "customer_type", "has_ecommerce", "domains", "countries_of_operation",
        "continent_spread", "usa_presence", "privacy_policy_published", "compliance_mentions",
        "quarterly_revenue", "sic_codes", "services_appetite", "internet_exposure_domains",
        "customer_base_scale", "digital_exposure", "disruption_speed", "recovery_complexity",
        "founding_year"
    ],
    log_fields=[
        "revenue", "customer_type", "has_ecommerce"
    ],
    output_fields=["risk_category", "underwriting_rationale"]
)

# Combined master config
CONFIG = BusinessRuleConfig(
    rule_id=RULE_ID,
    rule_name="Cyber Risk Underwriting Rating",
    description="Evaluates all 13 modifiers end-to-end to output a single consolidated underwriting risk rating.",
    collector_configs={
        "wikipedia": WIKIPEDIA,
        "wikidata": WIKIDATA,
        "sec": SEC,
        "dnb": DNB,
        "domain": DOMAIN,
        "responses": RESPONSES
    },
    coordinator_config=COORD,
    fact_checker_config=FACT,
    underwriter_config=UW
)

# Register the config
BusinessRuleRegistry.register(CONFIG)
