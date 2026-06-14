import os
import json
from langchain_huggingface import HuggingFaceEndpoint
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

def get_llm():
    """Returns the configured LLM based on environment variables."""
    hf_token = os.getenv("HF_TOKEN")
    openrouter_key = os.getenv("OPENROUTER_API_KEY")

    if openrouter_key:
        return ChatOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_key,
            model="qwen/qwen-2.5-72b-instruct",
            temperature=0.2,
            max_tokens=500
        )
    elif hf_token:
        return HuggingFaceEndpoint(
            repo_id="Qwen/Qwen2.5-72B-Instruct",
            temperature=0.2,
            huggingfacehub_api_token=hf_token,
            max_new_tokens=500
        )
    else:
        raise ValueError("Neither OPENROUTER_API_KEY nor HF_TOKEN is set.")

def classify_incident(parsed_log: dict) -> dict:
    """Uses LLM to classify the incident and extract root cause."""
    llm = get_llm()
    
    prompt = PromptTemplate.from_template("""
    Analyze the following incident log.

    Log Details:
    Service: {service}
    Raw Error: {raw_log}

    Determine:
    - severity: (e.g., "critical", "warning", "info")
    - root_cause: A brief probable root cause
    - confidence: A confidence score between 0.0 and 1.0

    Return ONLY a valid JSON object with the keys "severity", "root_cause", and "confidence".
    Do not wrap in markdown tags like ```json. Just return the raw JSON object.
    """)

    formatted_prompt = prompt.format(
        service=parsed_log.get("service"),
        raw_log=parsed_log.get("raw")
    )

    try:
        response = llm.invoke(formatted_prompt)
        # If response is an AIMessage (OpenRouter), extract content
        content = response.content if hasattr(response, "content") else response
        content = content.strip()
        
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)
        return result
    except Exception as e:
        print(f"Classification Error: {e}")
        # Fallback if LLM fails
        return {
            "severity": parsed_log.get("severity", "unknown"),
            "root_cause": parsed_log.get("error_type", "unknown_error"),
            "confidence": 0.5
        }
