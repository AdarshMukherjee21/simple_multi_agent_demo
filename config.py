import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()

# File paths
POLICY_FILE = "onboarding_guide.txt"
LEAVE_FILE = "company_policy.txt"
CONTACTS_FILE = "contacts.json"
DRAFTS_DIR = "drafts"

os.makedirs(DRAFTS_DIR, exist_ok=True)

# API Key Validation
api_key = os.environ.get("NVIDIA_API_KEY")

print("=" * 60)
if api_key:
    print(f"NVIDIA API Key Loaded: {api_key[:10]}...")
else:
    print("ERROR: NVIDIA_API_KEY is missing from environment or .env file.")
print("=" * 60)

# Replace with an exact model string outputted from your NVIDIA API Catalog
MODEL_NAME = "nvidia/nemotron-3.5-lightning-30b-a3b"

def get_llm(role="worker"):
    return ChatOpenAI(
        model=MODEL_NAME,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=os.environ.get("NVIDIA_API_KEY"),
        temperature=0.1 if role == "supervisor" else 0.7,
        max_tokens=4096
    )

def test_llm_connection():
    print("\n" + "=" * 60)
    print("STARTING LLM CONNECTION TEST")
    print(f"Target Model: {MODEL_NAME}")
    print(f"Endpoint: https://integrate.api.nvidia.com/v1")
    print("=" * 60)
    
    try:
        llm = get_llm(role="worker")
        print("Sending test message: 'hi' ...")
        response = llm.invoke([HumanMessage(content="hi")])
        
        print("\n" + "-" * 60)
        print("CONNECTION TEST PASSED")
        print(f"Response Content: {response.content.strip()}")
        print("-" * 60 + "\n")
        return True
    except Exception as e:
        print("\n" + "-" * 60)
        print("CONNECTION TEST FAILED")
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("-" * 60 + "\n")
        return False

# Run test on module import
test_llm_connection()