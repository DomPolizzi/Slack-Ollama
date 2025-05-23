from typing import Dict, List
from copilotkit import LangGraphAgent  # imported but not used for now
from langfuse.callback import CallbackHandler
from components.langfuse_wrapper import LangfuseWrapper
from agents.agent import retrieve, think, respond
from configs.config import config

# Initialize raw Langfuse handler and compatibility wrapper
_raw_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)
langfuse_handler = LangfuseWrapper(_raw_handler)

def run_graph_agent(query: str, chat_history: List[Dict] = None) -> Dict:
    """
    Execute the agent workflow manually with Langfuse session and graph tracing.
    This replaces the LangGraphAgent approach.
    """
    if chat_history is None:
        chat_history = []
    # initial state
    state = {
        "messages": chat_history + [{"role": "user", "content": query}],
        "current_input": query,
        "retrieval_results": [],
        "action": "retrieve"
    }

    # Langfuse session start
    langfuse_handler.session_start(name="manual_session", input={"query": query})
    langfuse_handler.graph_start(graph="manual_agent_flow")

    # Run each step
    state = retrieve(state)
    state = think(state)
    state = respond(state)

    # Graph end and session end
    langfuse_handler.graph_end(graph="manual_agent_flow")
    last_response = state.get("messages", [])[-1].get("content")
    langfuse_handler.session_end(name="manual_session", output={"response": last_response})

    return state
