from pydantic import BaseModel
from typing import TypedDict, Literal
from langgraph.graph.message import MessagesState, add_messages
from langchain_core.messages import HumanMessage
from typing import List, Dict, Any
import uuid
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_core.messages import AnyMessage
from typing_extensions import Annotated

from components.trace_store import thread_run_map
from components.supervisor_agent import (
    classify_intent,
    retrieve_documents,
    rank_documents,
    ollama_generate,
)
from components.langfuse_wrapper import LangfuseWrapper

## from langfuse.decorators import langfuse_context
from langfuse.decorators import observe

import inspect
### Debugging Graph
# print("Imported StateGraph from:", inspect.getfile(StateGraph))
# print("StateGraph.add_conditional_edges signature:", inspect.signature(StateGraph.add_conditional_edges))

from langfuse.callback import CallbackHandler
langfuse_handler = CallbackHandler(
    public_key="pk-lf-96ceabbd-e7e7-4bb0-a862-aa96dcd3b982",
    secret_key="sk-lf-3554da03-7a7b-4d8f-96d5-e6f003cb9808",
    host="https://langfuse.offsec.com"
)

class HRGraphState(MessagesState):
    """
    State schema for the HR Graph Supervisor.
    This includes the query, route, retrieved documents, and messages.
    """

    query: str
    route: str
    docs: List[Dict[str, Any]]
    _run_id: str


# class HRGraphState(BaseModel):
#     query: str
#     route: str
#     docs: List[Dict[str, Any]]
#     messages: Annotated[list[AnyMessage], add]
#     _run_id: str

# Initialize tracing
_tracer = LangfuseWrapper()


def classify_node(state: HRGraphState):
###    messages = state["messages"]
###
###    if messages:
###        if isinstance(messages[-1], HumanMessage):
###            query = messages[-1].content
    query = state["query"]
    route = classify_intent(query)
    _tracer.log_event("classify", input=query, output=route, run_id=state["_run_id"])
    return {"route": route}

def retriever_node(state: HRGraphState):
    docs = retrieve_documents(state["query"])
    ranked = rank_documents(docs)
##    _tracer.log_event(
##        "retrieve",
##        input=state["query"],
##        output=[d["id"] for d in ranked],
##        run_id=state["_run_id"],
##    )
    return {"docs": ranked}

def grader_node(state: HRGraphState):
    # for simplicity, pass through and log
    ranked = state.get("docs", [])
    _tracer.log_event(
        "grade",
        input=[d["score"] for d in state.get("docs", [])],
        output=None,
        run_id=state["_run_id"],
    )
    return {"docs": ranked}


def response_node(state: HRGraphState):
    route = state.get("route")
    if route == "small_talk":
        resp = ollama_generate(state["query"])
    else:
        context_texts = "\n\n".join([d["text"] for d in state["docs"]])
        prompt = (
            f"You are an expert HR assistant.\n\n"
            f"Context Documents:\n{context_texts}\n\n"
            f"User Query: {state['query']}"
        )
        resp = ollama_generate(prompt)
    # state.messages.append({"role": "assistant", "content": resp})
    _tracer.log_event(
        "generate_response", input=state["query"], output=resp, run_id=state["_run_id"]
    )
    return {"messages": [{"role": "assistant", "content": resp}]}


# Build the supervisor workflow graph
# _graph = StateGraph(state_schema=HRGraphState)
# _graph.add_node("classify", RunnableLambda(_classify_node))
# _graph.add_node("retriever", RunnableLambda(_retriever_node))
# _graph.add_node("grader", RunnableLambda(_grader_node))
# _graph.add_node("response", RunnableLambda(_response_node))

_graph = StateGraph(state_schema=HRGraphState).add_sequence(
    [classify_node, retriever_node, grader_node, response_node]
)

# _graph.set_entry_point("classify")
_graph.add_edge(START, "classify_node")

# def route_selector(state: Dict[str, Any]) -> str:
#     return state.route

# _graph.add_conditional_edges(
#     source="classify",
#     path=route_selector,
#     path_map={
#         "retrieve": "retriever",
#         "small_talk": "response",
#         "general": "response"
#     }
# )

# _graph.add_edge("retriever", "grader")
# _graph.add_edge("grader", "response")
# _graph.add_edge("response", END)

# Compile the graph for execution
memory = MemorySaver()
executable_graph = _graph.compile(checkpointer=memory)
executable_graph.name = "Pops"


def run_graph_supervisor(query: str, slack_thread_id: str, user: str) -> Dict[str, Any]:
    thread_id = slack_thread_id

    if thread_id and thread_id in thread_run_map:
        run_id = thread_run_map[thread_id]
    else:
        run_id = str(uuid.uuid4())  # 🔄 New run_id
        if thread_id:
            thread_run_map[thread_id] = run_id

    # input["_run_id"] = run_id

    input = {
        "query": query,
        "_run_id": run_id
    }

    config = {
        "configurable": {"thread_id": str(thread_id)},
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_session_id": str(thread_id), "langfuse_user_id": user},
    }

    _tracer.session_start("supervisor_graph", input=input)
    _tracer.set_trace_context(run_id)
    result = executable_graph.invoke(input=input, config=config, debug=True)
    _tracer.session_end("supervisor_graph", output=result, run_id=run_id)
    return result