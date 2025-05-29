import os
import uuid
from typing import List, Dict, Any, Optional
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import Document
from configs.config import config


def get_llm() -> OllamaLLM:
    """Instantiate Ollama LLM via LangChain."""
    return OllamaLLM(
        model=os.environ.get("OLLAMA_LLM_MODEL", config.ollama.llm_model),
        base_url=os.environ.get("OLLAMA_BASE_URL", config.ollama.base_url),
    )


def get_embeddings() -> OllamaEmbeddings:
    """Instantiate Ollama embeddings via LangChain."""
    return OllamaEmbeddings(
        model=os.environ.get("OLLAMA_EMBEDDING_MODEL", config.ollama.embedding_model),
        base_url=os.environ.get("OLLAMA_BASE_URL", config.ollama.base_url),
    )


def get_vectorstore() -> Chroma:
    """Load or connect to a Chroma vector store."""
    emb = get_embeddings()
    return Chroma(
        embedding_function=emb,
        collection_name=os.environ.get("CHROMA_COLLECTION_NAME")
    )


def retrieve_documents(query: str):
    """Stub placeholder for document retrieval."""
    #print(query)
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever()
    return retriever.invoke(input=query)


def classify_intent(query: str) -> str:
    """Simple classifier: small_talk or retrieve."""
    q = query.lower()
    if any(greet in q for greet in ("hello", "hi", "hey", "good morning", "good evening")):
        return "small_talk"
    if any(kw in q for kw in ("policy", "doc", "troubleshoot", "procedure", "guide")):
        return "retrieve"
    return "general"


def rank_documents(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Rank documents based on some criteria."""
    # Placeholder for ranking logic
    return sorted(docs, key=lambda x: x.get("score", 0), reverse=True)

    """Simple classifier: small_talk or retrieve."""
    q = query.lower()
    if any(greet in q for greet in ("hello", "hi", "hey", "good morning", "good evening")):
        return "small_talk"
    if any(kw in q for kw in ("policy", "doc", "troubleshoot", "procedure", "guide")):
        return "retrieve"
    return "general"


def ollama_generate(prompt: str) -> str:
    """Generate a response using the Ollama LLM."""
    llm = get_llm()
    return llm.invoke(prompt)


def run_supervisor_agent(query: str, history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Supervisor pipeline using LangChain:
    - Classify intent
    - For retrieval intents, use ConversationalRetrievalChain over Chroma
    - For small_talk or general, use direct chat LLM
    """
    history = history or []
    session_id = str(uuid.uuid4())
    intent = classify_intent(query)

    llm = get_llm()
    vectorstore = get_vectorstore()

    if intent == "small_talk":
        # direct chat response
        response = llm.invoke(query)
    else:
        # create conversational retrieval chain for RAG
        qa_chain = ConversationalRetrievalChain.from_llm(
            llm=llm,
            retriever=vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5}),
            return_source_documents=False
        )
        # history messages converted to tuples of (user, assistant)
        chat_history = [(m["content"], h["content"]) for m, h in zip(history[::2], history[1::2])] if history else []
        result = qa_chain({"question": query, "chat_history": chat_history})
        response = result["answer"]

    # append to history
    history.append({"role": "user", "content": query})
    history.append({"role": "assistant", "content": response})

    return {"session_id": session_id, "messages": history}
