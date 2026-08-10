import os
import json
import re
from datetime import datetime
from typing import Dict, Any
from langchain_groq import ChatGroq
from src.config import PromptTemplate

class OpenAIResponse:
    def __init__(self, content: str, prompt_tokens: int, completion_tokens: int):
        self.content = content
        self.response_metadata = {
            "token_usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
            }
        }

class SimpleChatOpenAI:
    def __init__(
        self, 
        model: str, 
        api_key: str, 
        temperature: float = 0.0,
        azure_endpoint: str = None,
        azure_api_version: str = "2024-02-15-preview"
    ):
        self.model = model
        self.api_key = api_key
        self.temperature = temperature
        self.azure_endpoint = azure_endpoint
        self.azure_api_version = azure_api_version

    def invoke(self, prompt: str) -> OpenAIResponse:
        import urllib.request
        import json
        
        # Format URL and headers differently for Azure vs standard OpenAI
        if self.azure_endpoint:
            base_url = self.azure_endpoint.rstrip('/')
            url = f"{base_url}/openai/deployments/{self.model}/chat/completions?api-version={self.azure_api_version}"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
        else:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
        data = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.temperature
        }
        
        # Model parameter is only required in standard OpenAI payload, defined in URL path for Azure
        if not self.azure_endpoint:
            data["model"] = self.model
        
        req = urllib.request.Request(
            url, 
            data=json.dumps(data).encode("utf-8"), 
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                resp_data = json.loads(response.read().decode("utf-8"))
                content = resp_data["choices"][0]["message"]["content"]
                usage = resp_data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                return OpenAIResponse(content, prompt_tokens, completion_tokens)
        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {e}")

class BaseAgent:
    def __init__(self, config: Any, tracker: Any = None):
        self.config = config
        self.tracker = tracker

    def get_logger(self) -> Any:
        from src.utils.logger import get_agent_logger
        agent_name = getattr(self.config, 'name', self.__class__.__name__)
        return get_agent_logger(agent_name)

    def format_prompt(self, template: PromptTemplate, **kwargs) -> str:
        # Framework default variables
        now = datetime.now()
        framework_vars = {
            "current_year": str(now.year),
            "today_str": now.strftime("%Y-%m-%d"),
            "format_instructions": "Your output must be a single, valid JSON block. Do not include markdown ticks (like ```json), explanations, or notes."
        }
        
        # Merge prompt_vars from agent configuration if defined
        config_vars = {}
        if hasattr(self.config, 'prompt_vars') and self.config.prompt_vars:
            config_vars = self.config.prompt_vars
            
        merged = {**framework_vars, **config_vars, **kwargs}
        return template.format(**merged)

    def call_llm(self, prompt: str, temperature: float = 0.0) -> str:
        # Retrieve potential Azure OpenAI environment variables
        env_azure_key = os.environ.get("AZURE_OPENAI_API_KEY")
        env_azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_OPENAI_API_BASE") or os.environ.get("OPENAI_API_BASE") or os.environ.get("OPENAI_BASE_URL")
        env_api_version = os.environ.get("AZURE_OPENAI_API_VERSION") or os.environ.get("OPENAI_API_VERSION") or "2024-02-15-preview"
        env_deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT") or os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") or os.environ.get("DEPLOYMENT_NAME") or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        
        openai_key = os.environ.get("OPENAI_API_KEY")
        groq_key = os.environ.get("GROQ_API_KEY")
        azure_key = None
        
        # Check signs of Azure deployment
        is_azure = False
        if env_azure_key:
            is_azure = True
        elif os.environ.get("OPENAI_API_TYPE") == "azure":
            is_azure = True
        elif env_azure_endpoint and ("openai.azure.com" in env_azure_endpoint or "azure" in env_azure_endpoint.lower()):
            is_azure = True

        logger = self.get_logger()
        agent_name = getattr(self.config, 'name', self.__class__.__name__)
        logger.info(f"[{agent_name}] Invoking LLM for prompt/extraction...")
        logger.debug(f"[{agent_name}] Full prompt sent to LLM:\n{'='*60}\n{prompt}\n{'='*60}")

        if is_azure:
            azure_key = env_azure_key or openai_key
            if not azure_key:
                raise ValueError("Azure OpenAI detected but no API key configured. Set AZURE_OPENAI_API_KEY or OPENAI_API_KEY.")
            if not env_azure_endpoint:
                raise ValueError("Azure OpenAI detected but no endpoint configured. Set AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_BASE or OPENAI_API_BASE.")
            model_name = env_deployment_name
            groq_models = [model_name]
        elif openai_key:
            model_name = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            groq_models = [model_name]
        elif groq_key:
            model_name = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
            base_fallbacks = ["llama-3.3-70b-versatile", "llama-3.3-70b-specdec", "llama-3.1-8b-instant", "llama-3.2-3b-preview"]
            groq_models = [model_name] + [m for m in base_fallbacks if m != model_name]
        else:
            raise ValueError(
                "No LLM credentials configured. Please set AZURE_OPENAI_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY."
            )

        last_exception = None
        for m_name in groq_models:
            try:
                if is_azure:
                    logger.info(f"[{agent_name}] LLM Provider: Azure OpenAI | Deployment: {m_name} | Endpoint: {env_azure_endpoint} | API Version: {env_api_version} | Temperature: {temperature}")
                    from langchain_openai import AzureChatOpenAI
                    llm = AzureChatOpenAI(
                        azure_endpoint=env_azure_endpoint,
                        azure_deployment=m_name,
                        api_key=azure_key,
                        api_version=env_api_version,
                        temperature=temperature
                    )
                elif openai_key:
                    logger.info(f"[{agent_name}] LLM Provider: OpenAI | Model: {m_name} | Temperature: {temperature}")
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model=m_name,
                        api_key=openai_key,
                        temperature=temperature
                    )
                elif groq_key:
                    logger.info(f"[{agent_name}] LLM Provider: Groq | Model: {m_name} | Temperature: {temperature}")
                    llm = ChatGroq(
                        model=m_name,
                        api_key=groq_key,
                        temperature=temperature
                    )

                res = llm.invoke(prompt)
                prompt_tokens = 0
                completion_tokens = 0
                
                if hasattr(res, 'response_metadata') and res.response_metadata:
                    token_usage = res.response_metadata.get('token_usage', {})
                    if token_usage:
                        prompt_tokens = token_usage.get('prompt_tokens', 0)
                        completion_tokens = token_usage.get('completion_tokens', 0)
                        if self.tracker:
                            self.tracker.add_usage(prompt_tokens, completion_tokens)
                
                if azure_key or openai_key:
                    if "gpt-4o-mini" in m_name:
                        input_rate = 0.15
                        output_rate = 0.60
                    elif "gpt-4o" in m_name:
                        input_rate = 2.50
                        output_rate = 10.00
                    else:
                        input_rate = 0.15
                        output_rate = 0.60
                else:
                    input_rate = 0.59
                    output_rate = 0.79
                    
                cost = (prompt_tokens * input_rate + completion_tokens * output_rate) / 1000000.0
                
                logger.info(f"[{agent_name}] LLM Response received ({m_name}). Usage: input={prompt_tokens}, output={completion_tokens}, cost=${cost:.6f}")
                logger.info(f"[{agent_name}] Output text:\n{str(res.content)}")
                
                return str(res.content)
            except Exception as e:
                last_exception = e
                logger.warning(f"[{agent_name}] LLM invocation failed on model '{m_name}': {e}. Retrying with next fallback model...")
                continue

        raise RuntimeError(f"Error calling live model across all fallback models: {last_exception}")

    def parse_json(self, text: str) -> Dict[str, Any]:
        logger = self.get_logger()
        agent_name = getattr(self.config, 'name', self.__class__.__name__)
        cleaned = text.strip()
        # Clean any markdown code blocks
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        logger.debug(f"[{agent_name}] parse_json input ({len(text)} chars): {text[:300]}{'...' if len(text) > 300 else ''}")
        try:
            result = json.loads(cleaned)
            logger.debug(f"[{agent_name}] parse_json success. Keys extracted: {list(result.keys()) if isinstance(result, dict) else type(result).__name__}")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"[{agent_name}] parse_json direct decode failed ({e}), attempting regex fallback...")
            # Fallback regex to find JSON object structure
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(0))
                    logger.debug(f"[{agent_name}] parse_json regex fallback succeeded. Keys: {list(result.keys()) if isinstance(result, dict) else type(result).__name__}")
                    return result
                except json.JSONDecodeError:
                    pass
            logger.error(f"[{agent_name}] parse_json failed entirely. Raw text:\n{text}")
            truncated = text[:500] + ("..." if len(text) > 500 else "")
            raise ValueError(f"Failed to parse LLM output as JSON. Output (truncated): {truncated}. Error: {e}")

class BaseCollectorAgent(BaseAgent):
    pass

class BaseCoordinatorAgent(BaseAgent):
    pass

class BaseFactCheckerAgent(BaseAgent):
    pass

class BaseUnderwriterAgent(BaseAgent):
    pass
