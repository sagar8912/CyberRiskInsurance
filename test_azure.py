import os
import time
from dotenv import load_dotenv
import traceback

def run_test():
    load_dotenv()
    
    azure_key = os.environ.get("AZURE_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    azure_endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or os.environ.get("AZURE_OPENAI_API_BASE") or os.environ.get("OPENAI_API_BASE")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    
    if not azure_key or not azure_endpoint or not deployment:
        print("Missing Azure OpenAI credentials in environment variables.")
        return

    print("===========================================")
    print("Azure OpenAI Standalone Connectivity Test")
    print(f"Endpoint: {azure_endpoint}")
    print(f"Deployment: {deployment}")
    print("===========================================")
    
    try:
        from langchain_openai import AzureChatOpenAI
        llm = AzureChatOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_key,
            api_version=api_version,
            azure_deployment=deployment,
            temperature=0.0
        )
        
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Calling llm.invoke('Say Hello')...")
        t0 = time.time()
        
        # We don't apply timeouts here on purpose to see if it hangs natively!
        res = llm.invoke("Say Hello")
        
        t1 = time.time()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Response received in {t1 - t0:.2f} seconds.")
        print(f"Response text: {res.content}")
        print("===========================================")
        print("RESULT: SUCCESS - Azure OpenAI connectivity is working perfectly.")
        
    except Exception as e:
        t_fail = time.time()
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Call failed after {t_fail - t0:.2f} seconds.")
        print(f"Exception: {e}")
        traceback.print_exc()
        print("===========================================")
        print("RESULT: FAILED - There is a connectivity or configuration issue.")

if __name__ == '__main__':
    run_test()
