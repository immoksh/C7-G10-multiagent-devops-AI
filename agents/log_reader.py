#from langchain_openai import ChatOpenAI
#from langchain_core.prompts import ChatPromptTemplate

#def log_reader_agent(raw_logs: str):
 #   llm = ChatOpenAI(model="gpt-4o", temperature=0)
 
    # Force structured output
#    structured_llm = llm.with_structured_output(ParsedLogs)
    
 #   prompt = ChatPromptTemplate.from_messages([
 #       ("system", "You are an expert SRE log parser. Extract key events, "
 #                  "identify error patterns, and structure the logs into JSON. "
 #                  "Ignore noise logs unless they provide context for an ERROR."),
 #       ("human", "Parse these raw logs:\n\n{log_content}")
 #   ])
    
 #   chain = prompt | structured_llm
 #   return chain.invoke({"log_content": raw_logs[:15000]}) # Truncate to stay within context limits

from utils.llm import llm

def log_reader_agent(state: dict):
    # Logic to parse raw_logs
    response = llm.invoke(f"Extract key errors from this: {state['raw_logs']}")
    return {"parsed_data": response.content}