import os
import re
import sys
import logging
import contextvars
from datetime import datetime

# Context variables for thread/async-isolated log runs
current_run_id = contextvars.ContextVar("current_run_id", default="")
current_log_date = contextvars.ContextVar("current_log_date", default="")
current_log_time = contextvars.ContextVar("current_log_time", default="")
current_company_name = contextvars.ContextVar("current_company_name", default="")
current_rule_id = contextvars.ContextVar("current_rule_id", default="cyber_risk_rating")

MODIFIER_FOLDER_MAPPING = {
    "mergers and acquisitions": "mergers_and_acquisitions",
    "amount of sensitive information": "sensitive_information",
    "domain encryption": "domain_encryption",
    "geographic spread": "geographic_spread",
    "internet footprint": "internet_footprint",
    "nature of services": "nature_of_services",
    "organizational complexity": "organizational_complexity",
    "privacy regulation": "privacy_regulation",
    "seasonality of sales": "seasonality_of_sales",
    "volatility/recovery in sales": "volatility_recovery_in_sales",
    "volatilityrecovery in sales": "volatility_recovery_in_sales",
    "applicability of privacy regulation": "applicability_privacy_regulation",
    "b2c end products": "b2c_end_products",
    "years in business": "years_in_business"
}

def slugify(text: str) -> str:
    """Converts a text string into a clean lowercase filename-friendly slug."""
    text = text.lower().strip()
    text = text.replace("/", "_")
    text = re.sub(r'[^a-z0-9\s_-]', '', text)
    text = re.sub(r'[\s_]+', '_', text)
    return text

def start_run_logging(rule_id: str, company_name: str) -> str:
    """Initializes the logging context variables for a single execution run."""
    import uuid
    run_id = str(uuid.uuid4())[:8]
    now = datetime.now()
    
    current_run_id.set(run_id)
    current_log_date.set(now.strftime("%Y-%m-%d"))
    current_log_time.set(now.strftime("%H-%M-%S"))
    current_company_name.set(company_name)
    current_rule_id.set(rule_id)

    # Write a startup banner to every agent log so each run file has clear context
    banner_logger = get_agent_logger("run_init")
    banner_logger.info("=" * 60)
    banner_logger.info(f"RUN STARTED  |  run_id={run_id}")
    banner_logger.info(f"Company      |  {company_name}")
    banner_logger.info(f"Rule         |  {rule_id}")
    banner_logger.info(f"Timestamp    |  {now.strftime('%Y-%m-%d %H:%M:%S')}")
    banner_logger.info("=" * 60)
    
    return run_id

class ContextAwareFileHandler(logging.Handler):
    """
    A custom file handler that dynamically determines the target log file path
    based on the active execution context variables, and safely opens and closes
    the file on every log emit to avoid file descriptor and memory leaks.
    """
    def __init__(self, formatter=None):
        super().__init__()
        if formatter:
            self.setFormatter(formatter)

    def emit(self, record):
        run_id = current_run_id.get()
        if not run_id:
            return  # No active run context, skip writing to file

        try:
            log_date = current_log_date.get()
            log_time = current_log_time.get()
            company_name = current_company_name.get()
            
            # Extract agent/modifier name from logger name
            # e.g., "cyber_risk_insurance.Wikipedia Collector" -> "Wikipedia Collector"
            parts = record.name.split(".")
            agent_name = parts[-1] if len(parts) > 1 else record.name
            
            cleaned_name = agent_name.lower()
            if "collector" in cleaned_name or "scraper" in cleaned_name:
                folder_slug = "collectors"
            elif "coordinator" in cleaned_name:
                folder_slug = "coordinator"
            elif "factchecker" in cleaned_name or "fact_checker" in cleaned_name or "fact checker" in cleaned_name:
                folder_slug = "fact_checker"
            elif "underwriter" in cleaned_name:
                folder_slug = "underwriter"
            else:
                folder_slug = MODIFIER_FOLDER_MAPPING.get(cleaned_name, slugify(agent_name))
                
            company_slug = slugify(company_name)
            
            log_dir = os.path.join("logs", log_date, folder_slug, company_slug)
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, f"run_{log_time}.txt")
            
            msg = self.format(record)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except Exception:
            self.handleError(record)

def get_agent_logger(agent_name: str) -> logging.Logger:
    """Gets a static, thread-safe, memory-efficient logger for a specific agent/modifier.
    
    Logs at DEBUG level to capture the finest granularity of events. Both console and
    file handlers receive all records — use log level filtering at the handler level if
    you need quieter console output in production.
    """
    logger_name = f"cyber_risk_insurance.{agent_name}"
    logger = logging.getLogger(logger_name)
    
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)   # Capture all levels (DEBUG, INFO, WARNING, ERROR)
        logger.propagate = False
        
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console Stream Handler — INFO and above to keep terminal readable
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
        
        # Context-aware dynamic file handler — DEBUG and above for full detail
        cfh = ContextAwareFileHandler(formatter)
        cfh.setLevel(logging.DEBUG)
        logger.addHandler(cfh)
        
    return logger
