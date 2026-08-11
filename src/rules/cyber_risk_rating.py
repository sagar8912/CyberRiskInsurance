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
- "subsidiaries": list of string names of ALL subsidiaries mentioned anywhere in the text.
- "acquisitions": list of objects for EVERY acquisition or company purchase mentioned in the text. Each object must have:
  - "name": string name of acquired company.
  - "deal_type": string - classify as "minor acquisition", "material acquisition", or "transitional acquisition" based on context.
  - "recency_years": float - the year of the acquisition (e.g. 2021.0), or estimate from context. Use the actual year mentioned, not years-ago.
  Do NOT return an empty list if acquisitions are mentioned anywhere in the text. Look carefully through ALL sections.
- "countries_of_operation": list of ALL country name strings where the company operates globally (e.g. ["United States", "United Kingdom", "Germany"]). Do NOT limit to only the primary country.
- "customer_type": "B2B" or "B2C" or "MIX" or null.
- "has_ecommerce": boolean or null (whether they sell products/services online directly via digital checkout).
- "country": string name of the primary headquarters country.
- "founding_year": numerical year when the company was founded (e.g. 1912), or null if not found.
- "industry_classification": list of strings covering primary industry AND all sub-industries mentioned (e.g. ["Insurance", "Property and Casualty", "Life Insurance", "Commercial Insurance"]).
- "company_breaches": list of breach strings or incident descriptions mentioned in the text (e.g., ["2023 Ransomware Incident", "2021 Data Breach"]), or empty list.
""",
    required_vars=["company_name", "domain", "wikipedia_text"]
)

WIKIPEDIA = CollectorAgentConfig(
    name="Wikipedia Collector",
    agent_type="wikipedia",
    prompt_template=WIKIPEDIA_PROMPT,
    target_fields=[
        "subsidiaries", "acquisitions", "customer_type", "has_ecommerce",
        "country", "countries_of_operation", "founding_year", "industry_classification", "company_breaches"
    ],
    source_name="Wikipedia"
)

WIKIDATA_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following raw Wikidata claims JSON for {company_name} ({domain}) and extract key details.
Note: IDs like Q12345 are Wikidata entity identifiers representing real-world entities (countries, companies, industries).
Wikidata Context:
{wikidata_text}

{format_instructions}
Your output JSON must contain:
- "revenue": numerical value of revenue or null if not found.
- "employees": numerical value of employee count or null.
- "country": string name of the primary headquarters country (infer from headquarters_ids or countries_ids).
- "headquarters": string name of the headquarters city.
- "industry": list of strings for ALL primary industry sectors mentioned (resolve Q IDs to industry names where you can).
- "sub_industries": list of strings for ALL sub-industries and business model keywords (e.g. Property insurance, Casualty insurance, Life insurance, Commercial insurance).
- "official_website": string primary URL from the websites list.
- "official_websites": list of ALL URLs found in the websites list (captures multiple domains like business.libertymutual.com, www.libertymutualgroup.com).
- "subsidiaries": list of string names of subsidiaries from subsidiaries_ids (use general knowledge to resolve Wikidata Q IDs to company names).
- "countries_of_operation": list of ALL country strings where the company operates globally. Use operating_area_ids, headquarters_ids, and your knowledge of the company to populate this — do NOT limit to one country.
- "parent_organization": string name of the parent or holding company if present in parent_org_ids, or null.
- "company_type": string describing the legal form (e.g. mutual company, public company, private company) inferred from instance_of_ids.
- "founding_year": numerical year when the company was founded (extracted from inception field), or null if not found.
- "acquisitions": list of acquisition objects. Use owned_by_ids and subsidiaries_ids and your general knowledge to infer known acquisitions. Each object: {{"name": string, "deal_type": string, "recency_years": float}}. Return empty list only if truly no acquisitions are known.
""",
    required_vars=["company_name", "domain", "wikidata_text"]
)

WIKIDATA = CollectorAgentConfig(
    name="Wikidata Collector",
    agent_type="wikidata",
    prompt_template=WIKIDATA_PROMPT,
    target_fields=[
        "revenue", "employees", "country", "headquarters", "industry", "sub_industries",
        "official_website", "official_websites", "subsidiaries", "founding_year",
        "countries_of_operation", "parent_organization", "company_type", "acquisitions"
    ],
    source_name="Wikidata"
)

SEC_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following SEC EDGAR facts and submission data for {company_name} ({domain}) and extract findings.
Note: matched_entity_name is the actual SEC-registered entity name found (may differ from the input company name).
For insurance companies, revenue may be reported as PremiumsEarned or similar — use raw_annual_revenue directly if present.
SEC Context:
{sec_text}

{format_instructions}
Your output JSON must contain:
- "revenue": numerical annual revenue in USD (use raw_annual_revenue if present, else null). For insurance companies this is total premiums earned.
- "fiscal_year": numerical year of the latest 10-K (e.g., 2024).
- "business_segments": list of strings (operating segments mentioned, e.g. Personal Lines, Commercial Lines, Global Risk Solutions).
- "geographic_revenue_or_regions": list of strings (geographic regions mentioned in filings).
- "subsidiaries_count": numerical count of exhibit 21 subsidiaries.
- "subsidiaries_list": list of strings representing subsidiary names, if available.
- "acquisitions_mentions": list of strings representing recent acquisitions or M&A transactions explicitly mentioned in business or MD&A sections.
- "acquisitions": list of objects for acquisitions, each with "name" (string), "deal_type" (string: minor/material/transitional acquisition), "recency_years" (float year).
- "risk_factor_keywords": list of strings (e.g., cybersecurity, data privacy, service disruption).
- "cybersecurity_mentions": boolean (whether cybersecurity is explicitly mentioned as a risk or initiative).
- "cloud_technology_mentions": boolean (whether cloud technology/services are mentioned).
- "customer_data_mentions": boolean (whether handling customer data or PII is mentioned).
- "filing_url": string URL to the latest annual report or 10-K filing.
- "quarterly_revenue": list of numerical quarterly revenues or empty list.
- "sic_codes": list of strings (SIC codes for the company's industry, e.g. ["6311"] for life insurance, ["6331"] for fire/marine/casualty insurance).
- "company_type": string describing company legal form (e.g. mutual holding company, stock corporation).
- "sec_cyber_incidents": list of strings representing 8-K material cybersecurity incident disclosures.
- "company_breaches": list of strings representing confirmed cyber breach incidents or ransomware disclosures.
- "has_ciso_disclosure": boolean (whether a CISO, Chief Information Security Officer, or executive cybersecurity officer is disclosed in Item 1C / Item 10 / governance).
- "cybersecurity_frameworks": list of strings (cybersecurity frameworks mentioned in Item 1C or Item 1, e.g. ISO 27001, SOC 2, NIST CSF, CIS Controls).
""",
    required_vars=["company_name", "domain", "sec_text"]
)

SEC = CollectorAgentConfig(
    name="SEC EDGAR Collector",
    agent_type="sec",
    prompt_template=SEC_PROMPT,
    target_fields=[
        "revenue", "fiscal_year", "business_segments", "geographic_revenue_or_regions",
        "subsidiaries_count", "subsidiaries_list", "acquisitions_mentions", "acquisitions",
        "risk_factor_keywords", "cybersecurity_mentions", "cloud_technology_mentions",
        "customer_data_mentions", "filing_url", "quarterly_revenue", "sic_codes", "company_type",
        "sec_cyber_incidents", "company_breaches", "has_ciso_disclosure", "cybersecurity_frameworks"
    ],
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
- "relationships": object representing Level-2 corporate direct-parent/ultimate-parent relationship links, or null.
""",
    required_vars=["company_name", "domain", "dnb_text"]
)

DNB = CollectorAgentConfig(
    name="D&B GLEIF Collector",
    agent_type="dnb",
    prompt_template=DNB_PROMPT,
    target_fields=["legal_name", "country", "legal_address", "headquarters_address", "registration_authority", "legal_form", "founding_year", "relationships"],
    source_name="DBCollector"
)

DOMAIN_PROMPT = PromptTemplate(
    template="""You are an expert domain scraper parser.
Analyze the following connection details and combined HTML content scraped from multiple discovered domains for {company_name} ({domain}) and extract key details.
Context (includes primary and discovered subdomains/aliases, TLS grades, ToS;DR data, and registration dates):
{scraper_text}

{format_instructions}
Your output JSON must contain:
- "domains": list of objects from the discovered_domains list, each with "url" (string) and "https_encrypted" (boolean). Include ALL discovered domains.
- "privacy_policy_published": boolean (whether a privacy policy link or page is found in the HTML snippet or mentioned).
- "compliance_mentions": list of strings (compliance frameworks mentioned in the HTML snippet, e.g. GDPR, CCPA, HIPAA).
- "customer_type": "B2B" or "B2C" or "MIX" or null. Consider all domains — if one is consumer-facing and another is business-facing, use "MIX".
- "has_ecommerce": boolean (whether there are e-commerce/store/checkout indicators like shopping cart, shop, pricing, payment buttons, or catalog purchase flows in the HTML snippet).
- "industries_served": list of strings (e.g. insurance, healthcare, banking, retail).
- "customer_segments": list of strings (e.g. enterprise, business clients, personal, small business).
- "business_model": string (e.g. B2B services / consulting).
- "b2b_b2c_confidence": string (e.g. high, medium, low).
- "ecommerce_evidence": string (e.g. No checkout/cart/payment flow detected).
- "cloud_saas_indicators": list of strings (e.g. platform, analytics, AI).
- "data_sensitive_indicators": list of strings (e.g. healthcare, insurance, financial services).
- "privacy_policy_url": string (extracted URL).
- "terms_url": string (extracted URL).
- "products_services_portfolio": list of strings (e.g. products, services, platforms, SaaS indicators, cloud offerings, payment offerings, healthcare offerings, insurance offerings).
- "mozilla_observatory_grade": string (the TLS/security grade from mozilla observatory context, e.g. "B+", or null).
- "tosdr_privacy_grade": string (the privacy rating grade from ToS;DR context, e.g. "C", or null).
- "domain_creation_date": string (the domain creation date from RDAP/WHOIS, e.g. "2005-12-01", or null).
- "domain_expiration_date": string (the domain expiration date from RDAP/WHOIS, e.g. "2026-12-01", or null).
- "domain_registrar": string (the domain registrar name from RDAP/WHOIS, e.g. "GoDaddy", or null).
- "has_dmarc_spf": boolean (whether DMARC and/or SPF email protection records are active in DNS context).
- "has_security_headers": boolean (whether HTTP security headers like HSTS, X-Frame-Options, or CSP are active).
- "has_security_txt": boolean (whether security.txt vulnerability disclosure file is present).
- "has_ciso_disclosure": boolean (whether a CISO or Chief Information Security Officer is disclosed or mentioned).
- "cybersecurity_frameworks": list of strings (e.g. ISO 27001, SOC 2, NIST CSF, FedRAMP).
""",
    required_vars=["company_name", "domain", "scraper_text"]
)


DOMAIN = CollectorAgentConfig(
    name="Domain Scraper",
    agent_type="domain",
    prompt_template=DOMAIN_PROMPT,
    target_fields=[
        "domains", "privacy_policy_published", "compliance_mentions", "customer_type", "has_ecommerce",
        "industries_served", "customer_segments", "business_model", "b2b_b2c_confidence",
        "ecommerce_evidence", "cloud_saas_indicators", "data_sensitive_indicators",
        "privacy_policy_url", "terms_url", "products_services_portfolio",
        "mozilla_observatory_grade", "tosdr_privacy_grade", "domain_creation_date",
        "domain_expiration_date", "domain_registrar", "has_dmarc_spf", "has_security_headers",
        "has_security_txt", "has_ciso_disclosure", "cybersecurity_frameworks"
    ],
    source_name="DomainScraper"
)

RESPONSES_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following Google search results and snippets for {company_name} ({domain}) and extract key findings.
Search Results:
{search_text}

{format_instructions}
Your output JSON must contain:
- "official_websites": list of string URLs or domains of the company and its subsidiaries found in search results.
- "revenue": numerical value of revenue in USD (e.g. 15000000000) if explicitly found in the snippets or title, or null.
- "acquisitions": list of objects for recent acquisitions found. Each object: {{"name": string, "deal_type": string, "recency_years": float}}.
""",
    required_vars=["company_name", "domain", "search_text"]
)

RESPONSES = CollectorAgentConfig(
    name="Responses API Collector",
    agent_type="responses",
    prompt_template=RESPONSES_PROMPT,
    target_fields=["official_websites", "revenue", "acquisitions"],
    source_name="ResponsesAPI"
)



GDELT_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following GDELT news events and articles context for {company_name} ({domain}) and extract cybersecurity, breach, or negative media events.
GDELT Context:
{gdelt_text}

{format_instructions}
Your output JSON must contain:
- "negative_events_count": numerical count of relevant negative events found.
- "negative_events_details": list of objects representing events. Each object: {{"title": string, "url": string, "date": string, "summary": string}}.
- "has_cyber_breach": boolean (whether a ransomware, leak, cyberattack or data breach incident is explicitly mentioned).
""",
    required_vars=["company_name", "domain", "gdelt_text"]
)

GDELT = CollectorAgentConfig(
    name="GDELT Event Monitor",
    agent_type="gdelt",
    prompt_template=GDELT_PROMPT,
    target_fields=["negative_events_count", "negative_events_details", "has_cyber_breach"],
    source_name="GDELT"
)


COURTLISTENER_PROMPT = PromptTemplate(
    template="""You are an expert underwriter extraction agent.
Analyze the following CourtListener docket search results for {company_name} ({domain}) and extract litigation findings.
CourtListener Context:
{courtlistener_text}

{format_instructions}
Your output JSON must contain:
- "has_active_litigation": boolean (whether any active, pending, or recent cyber/data/IP litigation cases were found).
- "litigation_cases": list of objects. Each: {{"case_name": string, "court": string, "date_filed": string, "relevance": string}}.
""",
    required_vars=["company_name", "domain", "courtlistener_text"]
)

COURTLISTENER = CollectorAgentConfig(
    name="CourtListener Collector",
    agent_type="courtlistener",
    prompt_template=COURTLISTENER_PROMPT,
    target_fields=["has_active_litigation", "litigation_cases"],
    source_name="CourtListener"
)

SSLLABS = CollectorAgentConfig(
    name="SSL Labs Collector",
    agent_type="ssllabs",
    prompt_template=PromptTemplate(
        template="SSL Labs grade lookup for {company_name} ({domain}). No LLM needed.",
        required_vars=["company_name", "domain"]
    ),
    target_fields=["ssl_grade", "ssl_details"],
    source_name="SSLLabs"
)

FTC = CollectorAgentConfig(
    name="FTC Feed Collector",
    agent_type="ftc",
    prompt_template=PromptTemplate(
        template="FTC RSS feed scan for {company_name} ({domain}). No LLM needed.",
        required_vars=["company_name", "domain"]
    ),
    target_fields=["ftc_actions_count", "ftc_actions"],
    source_name="FTC"
)

WAPPALYZER = CollectorAgentConfig(
    name="Wappalyzer Collector",
    agent_type="wappalyzer",
    prompt_template=PromptTemplate(
        template="Wappalyzer tech detection for {company_name} ({domain}). No LLM needed.",
        required_vars=["company_name", "domain"]
    ),
    target_fields=["detected_technologies", "has_ecommerce"],
    source_name="Wappalyzer"
)

CENSUS_NAICS = CollectorAgentConfig(
    name="Census NAICS Collector",
    agent_type="census_naics",
    prompt_template=PromptTemplate(
        template="Census NAICS lookup for {company_name} ({domain}). No LLM needed.",
        required_vars=["company_name", "domain"]
    ),
    target_fields=["naics_code", "naics_description"],
    source_name="CensusNAICS"
)

CISAKEV = CollectorAgentConfig(
    name="CISA KEV Collector",
    agent_type="cisakev",
    prompt_template=PromptTemplate(
        template="CISA Known Exploited Vulnerabilities lookup for {company_name} ({domain}). No LLM needed.",
        required_vars=["company_name", "domain"]
    ),
    target_fields=["cisa_kev_matches", "cisa_kev_count", "has_cisa_kev_vulnerabilities"],
    source_name="CISAKEVCollector"
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
- "sic_codes": list of strings (e.g., ["6331"] for insurance carriers, ["7372"] for prepackaged software, ["5311"] for department stores. If not explicitly found in collector findings, you must dynamically infer the most likely 4-digit SIC code based on the company's business activities or name, do not default to "7372" unless it is a software/tech company).
- "sub_industries": list of predominant sub-industry strings.
- "worst_sub_industry_appetite": "prohibited" or "restricted" or "acceptable" or "target".
- "services_appetite": "low_risk" or "medium_risk" or "high_risk".
- "internet_exposure_domains": number of domains.
- "customer_base_scale": "SMB (<1k)" or "Mid-Market" or "Enterprise".
- "estimated_customers_count": estimated total unique customers count (number).
- "digital_exposure": number (1 to 5).
- "disruption_speed": number (1 to 5).
- "recovery_complexity": number (1 to 5).
- "founding_year": numerical year or null.
- "has_cyber_breach": boolean.
- "cybersecurity_frameworks": list of strings (e.g., ["ISO 27001", "SOC 2 Type II"]).
- "has_dmarc_spf": boolean.
- "has_security_headers": boolean.
- "has_security_txt": boolean.
- "has_ciso_disclosure": boolean.
- "company_breaches": list of breach strings or incident objects (e.g., ["2023 Ransomware Incident", "2021 Data Breach"]).
- "industry_breach_tier": "Very Low" or "Low" or "Moderate" or "High" or "Very High".
- "cisa_kev_matches": list of CISA Known Exploited Vulnerability objects.
- "has_cisa_kev_vulnerabilities": boolean.
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
        "quarterly_revenue", "sic_codes", "sub_industries", "worst_sub_industry_appetite", "services_appetite", "internet_exposure_domains",
        "customer_base_scale", "estimated_customers_count", "founding_year", "has_cyber_breach",
        "has_active_litigation", "ssl_grade", "ftc_actions_count",
        "detected_technologies", "has_ecommerce", "naics_code", "naics_description",
        "cybersecurity_frameworks", "has_dmarc_spf", "has_security_headers", "has_security_txt", "has_ciso_disclosure",
        "company_breaches", "industry_breach_tier", "sec_cyber_incidents", "cisa_kev_matches", "has_cisa_kev_vulnerabilities"
    ],
    computed_fields=["usa_presence", "continent_spread"],
    report_sources=[
        "Wikipedia", "Wikidata", "SECCollector", "DBCollector", "DomainScraper",
        "GDELT", "CourtListener", "SSLLabs", "FTC", "Wappalyzer", "CensusNAICS", "CISAKEVCollector"
    ]
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
5. Internet footprint: Unique Web Domains Count * Customer Scale Multiplier (10k=1.0, 10k-100k=1.5, 100k-1M=2.0, 1M-10M=2.5, 10M-100M=3.0, 100M-1B=3.5, 1B+=4.0) evaluated against revenue tier matrix.
6. Nature of services: Unique Predominant Sub-Industries Count * Worst Appetite Multiplier (Prohibited x3, Restricted x2, Acceptable x1, Target x0.1) evaluated against revenue tier matrix.
7. Organizational Complexity: Subsidiary count vs revenue tier.
8. Privacy Regulation: Policy published + Compliance frameworks count.
9. Seasonality of sales: CV of quarterly revenue (CV < 0.1 Favourable, > 0.25 Unfavourable) or SIC benchmark.
10. Volatility/Recovery in Sales: D1 (Digital Exposure) + D2 (Disruption Velocity) + D3 (Recovery Complexity) + Sales Overlay (Score 2-16: 2-4 Favourable, 5-8 Partially Favourable, 9-12 Average, 13-16 Partially Unfavourable).
11. Applicability of Privacy Regulation: Operates in strict regions (GDPR, CCPA) or has e-commerce.
12. B2C End Products: B2C = average risk, B2B = favourable.
13. Years in business: founding year vs current year compared against revenue-tier thresholds.
14. Cybersecurity Info: Policy Frameworks (ISO 27001, SOC 2, NIST, CIS, OWASP, CSA) + Live Web Security (DMARC/SPF, headers, security.txt) + SEC CISO Governance. Public: 40%/40%/20%, Private: 50%/50%.
15. Industry & Company Breach History: Systemic Industry Risk Score (0-4 pts from DBIR sector tiers) + Company Breach Score (Base severity [0-4] * Recency [2.0x-0x] + Repeat kicker [0-3]). Private zero-breach floor-capped at Average rating.
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
        "quarterly_revenue", "sic_codes", "sub_industries", "worst_sub_industry_appetite", "services_appetite", "internet_exposure_domains",
        "customer_base_scale", "digital_exposure", "disruption_speed", "recovery_complexity",
        "founding_year", "has_cyber_breach", "cybersecurity_frameworks", "has_dmarc_spf", "has_security_headers", "has_security_txt", "has_ciso_disclosure",
        "company_breaches", "industry_breach_tier"
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
    description="Evaluates all 15 modifiers end-to-end to output a single consolidated underwriting risk rating.",
    collector_configs={
        "wikipedia": WIKIPEDIA,
        "wikidata": WIKIDATA,
        "sec": SEC,
        "dnb": DNB,
        "domain": DOMAIN,
        "responses": RESPONSES,
        "gdelt": GDELT,
        "courtlistener": COURTLISTENER,
        "ssllabs": SSLLABS,
        "ftc": FTC,
        "wappalyzer": WAPPALYZER,
        "census_naics": CENSUS_NAICS,
        "cisakev": CISAKEV
    },
    coordinator_config=COORD,
    fact_checker_config=FACT,
    underwriter_config=UW
)

# Register the config
BusinessRuleRegistry.register(CONFIG)
