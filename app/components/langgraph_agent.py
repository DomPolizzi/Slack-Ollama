"""
Manual pipeline for HR Agent with Langfuse tracing (no StateGraph).
"""
import uuid
from typing import Dict, List
from configs.config import config
from langfuse.callback import CallbackHandler
from components.langfuse_wrapper import LangfuseWrapper
from agents.agent import retrieve as retrieve_fn, grade as grade_fn, generate_response

# Initialize Langfuse tracing
raw_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)
langfuse_handler = LangfuseWrapper(raw_handler)

def run_graph_agent(query: str, history: List[Dict] = None) -> Dict:
    """Execute HR Agent steps: info_triage, retrieve, grade, generate_response."""
    history = history or []
    run_id = str(uuid.uuid4())
    langfuse_handler.session_start("hr_agent", input=query)

    # Info triage
    q = query.lower()
    keywords = ["policy", "doc", "troubleshoot"]
    need_retrieve = any(kw in q for kw in keywords)
    langfuse_handler.log_event("info_triage", input=query, output=need_retrieve)

    ranked_docs: List[str] = []
    if need_retrieve:
        docs = retrieve_fn(query)
        langfuse_handler.log_event("retrieve", input=query, output=docs)
        ranked_docs = grade_fn(docs)
        langfuse_handler.log_event("grade_retrieval", input=query, output=ranked_docs)

    # Generate response
    response = generate_response(query, history, ranked_docs)
    langfuse_handler.log_event("generate_response", input=query, output=response)

    # End session
    result = {"messages": history + [{"role": "assistant", "content": response}]}
    langfuse_handler.session_end("hr_agent", output={"num_messages": len(result["messages"])})
    return result
