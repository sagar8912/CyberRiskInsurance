# Cyber Risk Predictor (Underwriting Rating Modifier System)

A production-ready, configuration-driven multi-agent underwriting assessment system built using **LangGraph** and **Groq LLM** (`llama-3.3-70b-versatile`). It automates harvesting corporate data from live public directories, coordinates fact-checks, and evaluates the target company across **13 underwriting risk modifiers** aligned with the CNA underwriting matrix.

---

## 🚀 Key Features

* **LangGraph Multi-Agent Workflows:** Orchestrates validation, parallel data collection, fact-checking, and risk evaluations under a unified graph structure.
* **13 Mathematical Risk Modifiers:** Programmatic scoring rules evaluating Mergers & Acquisitions, Sensitive Information, Domain Encryption, Geographic Spread, Internet Footprint, Nature of Services, Organizational Complexity, Privacy Regulation, Seasonality of Sales, Volatility/Recovery, Privacy Applicability, B2C End Products, and **Years in Business**.
* **Consensus Fact-Checking:** Analyzes fact consistency across sources (GLEIF/D&B, SEC EDGAR, Wikidata, Wikipedia, Domain HTTPS Scraper). Computes a rigorous **Accuracy Score** and triggers human escalation when consensus drops below $50\%$.
* **Robust Caching System:** Saves collected evidence locally to eliminate redundant network requests and accelerate subsequent analyses.
* **High-Speed Groq Integration:** Leverages Groq API's high throughput (`llama-3.3-70b-versatile`) for reliable unstructured extraction and consensus summary text generation.

---

## 📁 Project Structure

```text
CyberRiskInsurance/
├── config/
│   └── config.json             # App configurations (cache path, default model, etc.)
├── data/
│   ├── cyber_rater_modifier_summary.xlsx  # CNA reference underwriting sheet
│   └── cache/
│       └── company_cache.json  # Local caching database (git-ignored)
├── src/
│   ├── __init__.py             # Public package exports and .env loader
│   ├── base_agents.py          # BaseAgent calling live Groq API
│   ├── collectors.py           # Concrete parallel collectors (Wikipedia, Wikidata, SEC, D&B, Domain SSL)
│   ├── processors.py           # CollectionCoordinator, FactChecker, and Underwriter agents
│   ├── registry.py             # BusinessRuleRegistry class
│   ├── factory.py              # AgentFactory and TokenUsageTracker classes
│   ├── config.py               # PromptTemplate and configuration dataclasses
│   ├── cli.py                  # CLI executable entrypoint
│   │
│   ├── rules/                  # Underwriting rules and modifier configs
│   │   ├── __init__.py         # Dynamic rule registration
│   │   └── cyber_risk_rating.py # CNA Cyber risk rating rules config
│   │
│   ├── workflows/              # LangGraph wiring configurations
│   │   ├── __init__.py
│   │   └── cyber_risk_rating.py # Wired LangGraph workflow for cyber rating
│   │
│   ├── cache/                  # Cache lookup and wrappers
│   └── supervisor/             # Input validation & cache lookup node
│
├── tests/
│   ├── test_modifiers.py       # Unit tests for the 13 risk modifiers
│   └── test_workflow.py        # E2E cache and integration workflow tests
│
├── requirements.txt            # Python dependencies (langchain-groq, langgraph, etc.)
├── .env                        # Local API credentials (git-ignored)
├── .gitignore                  # Git configuration files to ignore
└── README.md                   # This project guide
```

---

## 🛠️ Setup & Installation

1. **Clone/Navigate to the project directory:**
   ```bash
   cd /Users/shimodi/Documents/AgenticProjects/CyberRiskInsurance
   ```

2. **Configure Virtual Environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Credentials:**
   Create a `.env` file in the root folder and add your Groq API key:
   ```env
   GROQ_API_KEY="your-groq-api-key-here"
   ```

---

## 💻 How to Use

To evaluate a company and calculate its rating modifiers, execute the CLI entrypoint:

```bash
# Run the evaluation graph
PYTHONPATH=. .venv/bin/python3 src/cli.py --rule cyber_risk_rating --company "Liberty Mutual" --domain "www.libertymutual.com"
```

### CLI Command Options:
* `--rule`: Rule configuration ID to run (e.g., `cyber_risk_rating`).
* `--company`: Legal/trading name of the company (e.g., `"Liberty Mutual"`).
* `--domain`: Primary domain address (e.g., `"www.libertymutual.com"`).

---

## 🧪 Running Unit & Integration Tests

The automated test suite runs local unit verification for the 13 risk modifiers and integration verification for the cache-lookup workflows.

```bash
# Discover and run all tests
PYTHONPATH=. .venv/bin/python3 -m unittest discover -s tests
```
===

## 📊 Underwriting Methodology: Code vs. Excel

Here is a comparison of how the **Excel sheet** (`data/cyber_rater_modifier_summary.xlsx`) calculates rates versus how the **Python code** (`src/processors.py`) processes risk:

```text
[Reconciled Profile Data]
           │
           ▼
[Evaluate Modifier Rules]  <-- Both Excel & Python use the same rules
           │
 ┌─────────┴─────────┐
 ▼                   ▼
[Excel Path]     [Python Code Path]
 -5% (Credit)     1.0 (Very Favourable)
  0% (Neutral)    4.0 (Average)
 +5% (Debit)      6.0 (Unfavourable)
 ┌─────────┴─────────┐
 ▼                   ▼
[Final Verdict]  [Final Verdict]
0.92 Multiplier   FAVOURABLE Risk Category
```

* **Excel Approach:** Modifiers directly adjust the financial cost (premium) of specific coverages (e.g. -5% to +5% adjustments). The final verdict is a multiplicative factor applied to the base premium.
* **Python Code Approach:** Modifiers are mapped to qualitative rating categories (Very Favourable = 1.0, Average = 4.0, Unfavourable = 6.0). The average score across all 13 modifiers determines the final overall risk category.

