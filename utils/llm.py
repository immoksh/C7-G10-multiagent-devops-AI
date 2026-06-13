import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Point the base_url to OpenRouter
llm = ChatOpenAI(
    model="gpt-4o", # Or whichever model you are using on OpenRouter
    openai_api_key=os.getenv("OPENAI_API_KEY"), # This now contains your OpenRouter key
    openai_api_base="https://openrouter.ai/api/v1" # This is the crucial part
)