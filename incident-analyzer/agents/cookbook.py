from langchain_core.prompts import PromptTemplate
from .classifier import get_llm

def generate_cookbook(classification: dict, remediation_docs: list) -> str:
    """
    Synthesizes the retrieved runbooks and incident context into an actionable checklist.
    """
    llm = get_llm()

    docs_text = "\n\n".join(remediation_docs) if remediation_docs else "No specific runbooks found."

    prompt = PromptTemplate.from_template("""
    You are an expert SRE and DevOps engineer.
    An incident has occurred. Based on the classification and the available runbooks,
    generate a clear, step-by-step markdown checklist for recovering from this incident.

    Incident Classification:
    {classification}

    Available Runbook Context:
    {docs_text}

    Provide the output strictly as a Markdown checklist starting with an H1 header `# Recovery Checklist`.
    Make it actionable, precise, and suitable for junior engineers.
    """)

    formatted_prompt = prompt.format(
        classification=str(classification),
        docs_text=docs_text
    )

    try:
        response = llm.invoke(formatted_prompt)
        content = response.content if hasattr(response, "content") else response
        return content.strip()
    except Exception as e:
        print(f"Cookbook Generation Error: {e}")
        return "# Recovery Checklist\n- Check logs\n- Identify root cause\n- Restart service if needed"
