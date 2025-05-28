from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
from langgraph.graph.state import StateGraph
from langgraph.graph import END
from langchain_core.runnables import RunnableLambda

from components.supervisor_agent import (
    classify_intent,
    retrieve_documents,
    rank_documents,
    ollama_generate
)
from components.langfuse_wrapper import LangfuseWrapper

import inspect
print("Imported StateGraph from:", inspect.getfile(StateGraph))
print("StateGraph.add_conditional_edges signature:", inspect.signature(StateGraph.add_conditional_edges))

class HRGraphState(BaseModel):
    query: str
    route: str
    docs: List[Dict[str, Any]]
    messages: List[Dict[str, str]]
    _run_id: str

# Initialize tracing
_tracer = LangfuseWrapper()

def _classify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    route = classify_intent(state.query)
    state.route = route
    _tracer.log_event("classify", input=state.query, output=route, run_id=state._run_id)
    return state

def _retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
    docs = retrieve_documents(state.query)
    ranked = rank_documents(docs)
    state.docs = ranked
    _tracer.log_event("retrieve", input=state.query, output=[d["id"] for d in ranked], run_id=state._run_id)
    return state

def _grader_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # for simplicity, pass through and log
    _tracer.log_event("grade", input=[d["score"] for d in state.get("docs", [])], output=None, run_id=state["_run_id"])
    return state

def _response_node(state: Dict[str, Any]) -> Dict[str, Any]:
    if state.route == "small_talk":
        resp = ollama_generate(state.query)
    else:
        context_texts = "\n\n".join([d["text"] for d in state.docs])
        prompt = (
            f"You are an expert HR assistant.\n\n"
            f"Context Documents:\n{context_texts}\n\n"
            f"User Query: {state.query}"
        )
        resp = ollama_generate(prompt)
    state.messages.append({"role": "assistant", "content": resp})
    _tracer.log_event("generate_response", input=state.query, output=resp, run_id=state._run_id)
    return state

# Build the supervisor workflow graph
_graph = StateGraph(state_schema=HRGraphState)
_graph.add_node("classify", RunnableLambda(_classify_node))
_graph.add_node("retriever", RunnableLambda(_retriever_node))
_graph.add_node("grader", RunnableLambda(_grader_node))
_graph.add_node("response", RunnableLambda(_response_node))

_graph.set_entry_point("classify")

def route_selector(state: Dict[str, Any]) -> str:
    return state.route

_graph.add_conditional_edges(
    source="classify",
    path=route_selector,
    path_map={
        "retrieve": "retriever",
        "small_talk": "response",
        "general": "response"
    }
)

_graph.add_edge("retriever", "grader")
_graph.add_edge("grader", "response")
_graph.add_edge("response", END)

# Compile the graph for execution
executable_graph = _graph.compile()

def run_graph_supervisor(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Initialize run_id, inject into state, invoke the compiled graph,
    then return the final state dict.
    """
    run_id = str(uuid.uuid4())
    state.setdefault("route", "")
    state.setdefault("docs", [])
    state.setdefault("messages", [])
    state["_run_id"] = run_id
    _tracer.session_start("supervisor_graph", input=state)
    result = executable_graph.invoke(state)
    _tracer.session_end("supervisor_graph", output=result, run_id=run_id)
    return result
