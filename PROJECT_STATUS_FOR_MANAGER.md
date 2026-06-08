# Multi-Agent Cyber Risk Insurance Assessment Platform

## 1. Problem Statement
Underwriters manually research companies from multiple sources. This is slow, inconsistent, and error-prone. Our system automates company research and cyber risk assessment using multiple agents and real open-source data sources.

## 2. Current Input
The system accepts the following starting parameters:
- Company Name
- Company Domain

*Example Command:*
```bash
python -m src.main -n "Microsoft" -d "microsoft.com"
```

## 3. Current Architecture Flow
1. **User Input**
2. **Supervisor Agent**
3. **Revenue Router Agent**
4. **Collector Agents**
5. **Coordinator Agent**
6. **Fact Checker Agent**
7. **Underwriter Agent**
8. **Final Risk Report**

## 4. Implemented Agents

### Supervisor Agent
- Validates company name and domain.
- Checks local cache.
- Detects domain mismatch.
- Enriches data (e.g., country, TLD).

### Revenue Router Agent
- Identifies public/global companies.
- Selects the collector budget.
- Currently routes large companies to the full collector set.

### Collector Agents
- Collect evidence from external/open-source sources simultaneously.

### Coordinator Agent
- Merges collector outputs.
- Prioritizes trusted sources.
- Reconciles revenue, subsidiaries, countries, and domain evidence.
- Detects variance and conflicts among gathered evidence.

### Fact Checker Agent
- Verifies claims based on corroboration.
- Marks claims as Verified, Partial, Unsupported, or Contradicted.
- Calculates evidence accuracy score.

### Underwriter Agent
- Applies Excel-based underwriting modifier rules.
- Calculates risk category.
- Calculates confidence band based on accuracy.
- Triggers human escalation when needed.

## 5. Collector Details

| Collector Name | Source Used | API Key Required | What It Collects | Current Status |
|---|---|---|---|---|
| **DomainScraper** | Direct domain/SSL check using Python ssl/socket | No | HTTPS, SSL certificate, privacy policy, compliance mentions | Working |
| **Wikipedia Collector** | Wikipedia public API | No | Company summary, country, subsidiaries hints | Working |
| **Wikidata Collector** | Wikidata public API | No | Official name, country, industry, headquarters, website, revenue, employees, subsidiaries | Working |
| **DBCollector / GLEIF** | GLEIF public API | No | Legal entity name, LEI, country, legal status, parent relationship | Working |
| **SECCollector** | SEC EDGAR API | No (User-Agent required) | Annual revenue, public filings, subsidiaries from SEC data | Working for US public companies |
| **WebSearch Collector** | Bing Search API | Yes | Web search evidence, acquisitions, business profile | Skipped (No Bing API key) |
| **ResponsesAPI** | Mock/local data | Not used | Previously mock company profile | Disabled to avoid mock data |

## 6. Open-Source Sources Used
- **Wikipedia:** Free company profile and qualitative source.
- **Wikidata:** Structured company facts and figures.
- **GLEIF:** Legal entity validation and corporate structure.
- **SEC EDGAR:** US public company filings and certified annual revenue.
- **Domain/SSL:** Direct security posture and encryption signals.

## 7. Current Achievements
- Removed all mock data.
- Integrated real web collectors.
- Implemented collector-level caching for rapid re-runs.
- Coordinator and Fact Checker actively reconciling real data.
- Improved SEC revenue extraction explicitly for annual 10-K filings.
- Fixed domain alias mismatch logic (e.g., TCS to tcs.com).
- Fixed Underwriter escalation logic to stop falsely flagging partial matches.
- Pushed updates to GitHub.

## 8. Current Example Results

### Microsoft
- **Real sources used:** DomainScraper, DBCollector, Wikipedia, SECCollector, Wikidata
- **Revenue:** Sourced directly from SEC EDGAR.
- **Verification:** Revenue and Subsidiaries marked as partial evidence (due to slight differences between Wikidata and SEC).
- **Confidence:** ~50%
- **Human Escalation:** False

### Tata Consultancy Services
- **Entity Status:** Match
- **Revenue:** Not Available currently.
- **Reason:** SEC filings are not applicable for an Indian company.
- **Human Escalation:** True (due to missing critical evidence driving down the accuracy score).

## 9. Known Limitations
- Non-US revenue extraction is still pending.
- Acquisitions extraction is still weak without search capabilities.
- WebSearch Collector requires a Bing API key to function.
- Human validation loop is not fully implemented.
- More data sources are needed for Indian/Non-US companies to prevent automatic escalation.

## 10. Next Steps
- Add a non-US revenue source.
- Improve acquisitions extraction.
- Add a human validation loop.
- Add an architecture diagram with agent icons.
- Improve source reliability scoring.
- *(Optional)* Add Bing/OpenCorporates integration if approved.

## 11. One-Minute Manager Summary
We have built a working multi-agent cyber risk assessment MVP. It takes a company name and domain, collects evidence from real open-source sources, reconciles and fact-checks the information, applies underwriting rules, and produces a risk category, confidence score, and human escalation flag. The core architecture is working; remaining work is focused on improving data coverage and validation quality.
