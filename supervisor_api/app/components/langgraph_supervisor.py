import uuid
from pydantic import BaseModel
from typing import TypedDict, Literal
from langgraph.graph.message import MessagesState, add_messages
from langchain_core.messages import HumanMessage
from typing import List, Dict, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from langchain_core.messages import AnyMessage
from typing_extensions import Annotated
from configs.config import config
from langfuse.callback import CallbackHandler
from components.trace_store import thread_run_map
from components.supervisor_agent import (
    classify_intent,
    retrieve_documents,
    rank_documents,
    ollama_generate,
)


langfuse_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host,
    environment=config.langfuse.environment
)


### Debugging Graph
###import inspect
# print("Imported StateGraph from:", inspect.getfile(StateGraph))
# print("StateGraph.add_conditional_edges signature:", inspect.signature(StateGraph.add_conditional_edges))


class HRGraphState(MessagesState):
    """
    State schema for the HR Graph Supervisor.
    This includes the query, route, retrieved documents, and messages.
    """

    query: str
    route: str
    docs: List[Dict[str, Any]]
    _run_id: str


def classify_node(state: HRGraphState):
    query = state["query"]
    route = classify_intent(query)
    return {"route": route}


def retriever_node(state: HRGraphState):
    docs = retrieve_documents(state["query"])
    ranked = rank_documents(docs)
    return {"docs": ranked}


def grader_node(state: HRGraphState):
    # for simplicity, pass through and log
    ranked = state.get("docs", [])
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
    return {"messages": [{"role": "assistant", "content": resp}]}


# Build the supervisor workflow graph
_graph = StateGraph(state_schema=HRGraphState).add_sequence(
    [classify_node, retriever_node, grader_node, response_node]
)

_graph.add_edge(START, "classify_node")

# Compile the graph for execution
memory = MemorySaver()
executable_graph = _graph.compile(checkpointer=memory)
executable_graph.name = "Pops"


def run_graph_supervisor(query: str, slack_thread_id: str, user: str) -> Dict[str, Any]:
    thread_id = slack_thread_id

    if thread_id and thread_id in thread_run_map:
        run_id = thread_run_map[thread_id]
    else:
        run_id = str(uuid.uuid4())
        if thread_id:
            thread_run_map[thread_id] = run_id

    input = {
        "query": query,
        "_run_id": run_id
    }

    config = {
        "configurable": {"thread_id": str(thread_id)},
        "callbacks": [langfuse_handler],
        "metadata": {"langfuse_session_id": str(thread_id), "langfuse_user_id": user},
    }

    result = executable_graph.invoke(input=input, config=config, debug=False) # set to True for debugging
    return result