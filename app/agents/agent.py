import os
import json
from typing import List, Dict
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langfuse.callback import CallbackHandler
from components.langfuse_wrapper import LangfuseWrapper
from configs.config import config

# Initialize Langfuse for observability
raw_langfuse_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)
langfuse_handler = LangfuseWrapper(raw_langfuse_handler)

# Initialize Ollama LLM
ollama_params = {
    "model": config.ollama.llm_model,
    "callbacks": [raw_langfuse_handler]
}
ollama_params["base_url"] = config.ollama.docker_url or config.ollama.base_url
model = OllamaLLM(**ollama_params)

# Initialize embeddings
emb_params = {"model": config.ollama.embedding_model}
emb_params["base_url"] = config.ollama.docker_url or config.ollama.base_url
embeddings = OllamaEmbeddings(**emb_params)

# Set up ChromaDB (remote or local)
if config.chroma.host:
    import chromadb
    from chromadb.config import Settings
    client = chromadb.HttpClient(
        host=config.chroma.host,
        port=config.chroma.port,
        settings=Settings(allow_reset=True)
    )
    coll_name = config.chroma.collection_name or "llm_agent"
    try:
        collection = client.get_collection(coll_name)
    except:
        collection = client.create_collection(coll_name)
    db = Chroma(client=client, collection_name=coll_name, embedding_function=embeddings)
else:
    persist_dir = config.chroma.persist_directory or "./chroma_db"
    os.makedirs(persist_dir, exist_ok=True)
    db = Chroma(persist_directory=persist_dir, embedding_function=embeddings)

# System prompt template
system_prompt = """
You are a helpful AI assistant with access to a knowledge base.
Use retrieved documents to inform your answer.
If you don't know the answer, say so directly.
"""

answer_prompt = """
Provide a concise answer based on the relevant internal articles.
If the answer is not in the articles, say you don't know.
"""

def retrieve(query: str, k: int = 3) -> List[str]:
    """Retrieve top-k documents for a query."""
    docs = db.similarity_search(query, k=k)
    return [doc.page_content for doc in docs]

def grade(docs: List[str]) -> List[str]:
    """Rank documents by relevance (Chroma returns sorted results)."""
    return docs

def generate_response(query: str, history: List[Dict], docs: List[str]) -> str:
    """Generate assistant response given query, history, and ranked docs."""
    # Build messages
    msgs = [SystemMessage(content=system_prompt), SystemMessage(content=answer_prompt)]
    for msg in history:
        if msg.get("role") == "user":
            msgs.append(HumanMessage(content=msg["content"]))
        else:
            msgs.append(AIMessage(content=msg["content"]))
    docs_text = "\n\n".join(f"{i+1}. {d}" for i, d in enumerate(docs))
    msgs.append(HumanMessage(content=f"Relevant documents:\n{docs_text}"))
    msgs.append(HumanMessage(content=query))
    # Invoke model
    resp = model.invoke(msgs)
    return getattr(resp, "content", str(resp))

def hr_agent(query: str, history: List[Dict] = None) -> Dict:
    """High-resolution agent: retrieve, grade, generate response."""
    history = history or []
    docs = retrieve(query)
    ranked = grade(docs)
    response = generate_response(query, history, ranked)
    # Log event
    try:
        langfuse_handler.log_event(name="hr_agent", input=query, output=response)
    except Exception:
        pass
    return {"messages": history + [{"role": "assistant", "content": response}]}

def master_agent(query: str, history: List[Dict] = None) -> Dict:
    """Master agent: info triage -> HR agent -> final response."""
    history = history or []
    # Info triage could be added here if needed
    return hr_agent(query, history)

def run_agent(query: str, chat_history: List[Dict] = None) -> Dict:
    """Entry point: run the master agent."""
    chat_history = chat_history or []
    return master_agent(query, chat_history)


if __name__ == "__main__":
    # CLI loop
    chat_history: List[Dict] = []
    while True:
        query = input("Enter question (or 'q' to quit): ").strip()
        if query.lower() == "q":
            break
        result = run_agent(query, chat_history)
        reply = result["messages"][-1]["content"]
        print("\nAssistant:", reply)
        chat_history = result["messages"]
