# CyberRiskInsurance

# Project Structure
CyberRiskInsurance/
├── config/
│   └── config.json             # App configuration settings (cache path, etc.)
├── data/
│   ├── cyber_rater_modifier_summary.xlsx  # Underwriter modifier Excel sheet
│   ├── cache/
│   │   └── company_cache.json  # Local JSON cache database (ignored by Git)
│   └── mock_sources/
│       └── mock_companies.json # Mock search data for local demo run
├── src/
│   ├── main.py                 # CLI entrypoint to evaluate a company
│   ├── state.py                # LangGraph state definition
│   ├── graph.py                # LangGraph workflow setup and wiring
│   ├── supervisor.py           # Supervisor node (input validation & caching)
│   ├── coordinator.py          # Coordinator node (data reconciliation)
│   ├── fact_checker.py         # Fact Checker node (corroborating facts)
│   └── underwriter.py          # Underwriter node (calculates modifier ratings)
├── tests/
│   ├── test_modifiers.py       # Unit tests for the 10 Excel modifiers
│   └── test_workflow.py        # Integration tests for the LangGraph flow
├── requirements.txt            # Python dependencies
└── README.md                   # This project guide
