from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
from langgraph.graph.state import StateGraph
from langgraph.graph import END
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_core.messages import AnyMessage
from typing_extensions import Annotated

from components.trace_store import thread_run_map
from components.supervisor_agent import (
    classify_intent,
    retrieve_documents,
    rank_documents,
    ollama_generate
)
from components.langfuse_wrapper import LangfuseWrapper
## from langfuse.decorators import langfuse_context
from langfuse.decorators import observe

import inspect
### Debugging Graph
#print("Imported StateGraph from:", inspect.getfile(StateGraph))
#print("StateGraph.add_conditional_edges signature:", inspect.signature(StateGraph.add_conditional_edges))

class HRGraphState(BaseModel):
    query: str
    route: str
    docs: List[Dict[str, Any]]
    messages: Annotated[list[AnyMessage], add]
    _run_id: str

# Initialize tracing
_tracer = LangfuseWrapper()


@observe()
def _classify_node(state: Dict[str, Any]) -> Dict[str, Any]:
    route = classify_intent(state.query)
    state.route = route
    _tracer.log_event("classify", input=state.query, output=route, run_id=state._run_id)
    return {"route": route}

@observe()
def _retriever_node(state: Dict[str, Any]) -> Dict[str, Any]:
    docs = retrieve_documents(state.query)
    ranked = rank_documents(docs)
    state.docs = ranked
    _tracer.log_event("retrieve", input=state.query, output=[d["id"] for d in ranked], run_id=state._run_id)
    return {"docs": [d["id"] for d in ranked]}

@observe()
def _grader_node(state: Dict[str, Any]) -> Dict[str, Any]:
    # for simplicity, pass through and log
    _tracer.log_event("grade", input=[d["score"] for d in state.get("docs", [])], output=None, run_id=state["_run_id"])
    return {"docs": [d["id"] for d in ranked]}

@observe()
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
    #state.messages.append({"role": "assistant", "content": resp})
    _tracer.log_event("generate_response", input=state.query, output=resp, run_id=state._run_id)
    return {"messages": [{"role": "assistant", "content": resp}]} 

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
memory = MemorySaver()
executable_graph = _graph.compile(checkpointer=memory)

def run_graph_supervisor(state: Dict[str, Any]) -> Dict[str, Any]:
    thread_id = state.get("slack_thread_id")

    if thread_id and thread_id in thread_run_map:
        run_id = thread_run_map[thread_id]  
    else:
        run_id = str(uuid.uuid4())          # 🔄 New run_id
        if thread_id:
            thread_run_map[thread_id] = run_id

    state.setdefault("route", "")
    state.setdefault("docs", [])
    state.setdefault("messages", [])
    state["_run_id"] = run_id

    _tracer.session_start("supervisor_graph", input=state)
    _tracer.set_trace_context(run_id)
    result = executable_graph.invoke(state, {"configurable": {"thread_id": str(thread_id)}}, debug=True)
    _tracer.session_end("supervisor_graph", output=result, run_id=run_id)
    return result
