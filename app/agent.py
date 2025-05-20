from typing import Dict, List, Annotated, TypedDict, Literal
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langfuse.callback import CallbackHandler
import os
import json

from config import config

# Initialize Langfuse for observability
langfuse_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)

# Initialize Ollama LLM
ollama_params = {
    "model": config.ollama.llm_model,
    "callbacks": [langfuse_handler]
}

# Use Docker URL if provided, otherwise use base_url
if config.ollama.docker_url:
    ollama_params["base_url"] = config.ollama.docker_url
else:
    ollama_params["base_url"] = config.ollama.base_url

model = OllamaLLM(**ollama_params)

# Initialize embeddings
embedding_params = {
    "model": config.ollama.embedding_model
}

# Use Docker URL if provided, otherwise use base_url
if config.ollama.docker_url:
    embedding_params["base_url"] = config.ollama.docker_url
else:
    embedding_params["base_url"] = config.ollama.base_url

embeddings = OllamaEmbeddings(**embedding_params)

# Set up ChromaDB
if config.chroma.host:
    # Use ChromaDB running in Docker
    import chromadb
    from chromadb.config import Settings
    
    chroma_client = chromadb.HttpClient(
        host=config.chroma.host,
        port=config.chroma.port,
        settings=Settings(allow_reset=True)
    )
    
    collection_name = config.chroma.collection_name or "llm_agent"
    
    # Check if collection exists, create if it doesn't
    try:
        collection = chroma_client.get_collection(collection_name)
    except:
        collection = chroma_client.create_collection(collection_name)
    
    db = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
else:
    # Use local ChromaDB
    try:
        db_location = config.chroma.persist_directory
        if not db_location:
            db_location = "./chroma_db"
        
        if not os.path.exists(db_location):
            os.makedirs(db_location, exist_ok=True)
            # Initialize empty DB if it doesn't exist
            db = Chroma.from_documents([], embeddings, persist_directory=db_location)
        else:
            db = Chroma(persist_directory=db_location, embedding_function=embeddings)
    except Exception as e:
        print(f"Error setting up ChromaDB: {e}")
        # Fallback to in-memory Chroma if persistence fails
        db = Chroma.from_documents([], embeddings)

# Define the state schema
class AgentState(TypedDict):
    messages: List[Dict]
    current_input: str
    retrieval_results: List[str]
    action: Literal["retrieve", "think", "respond", "end"]

# Define the system prompt
system_prompt = """
You are a helpful AI assistant with access to a knowledge base.
You can retrieve information from the knowledge base to help answer questions.
If you don't know the answer, you can say so.

Follow these steps:
1. Analyze the user's question
2. Decide if you need to retrieve information from the knowledge base
3. Formulate a response based on the retrieved information and your knowledge
"""

# Define the retrieval function
def retrieve(state: AgentState) -> AgentState:
    """Retrieve relevant documents from the vector store."""
    query = state["current_input"]
    docs = db.similarity_search(query, k=3)
    
    # Extract the content from the documents
    retrieval_results = [doc.page_content for doc in docs]
    
    # Log the retrieval to Langfuse
    langfuse_handler.log_event(
        name="retrieval",
        input=query,
        output=retrieval_results
    )
    
    return {
        **state,
        "retrieval_results": retrieval_results,
        "action": "think"
    }

# Define the thinking function
def think(state: AgentState) -> AgentState:
    """Process the retrieved information and decide on the next action."""
    messages = state["messages"]
    retrieval_results = state["retrieval_results"]
    
    # Create a prompt that includes the retrieved information
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("system", f"Retrieved information: {retrieval_results}"),
        *[
            (m["role"], m["content"]) 
            for m in messages
        ]
    ])
    
    # Create a chain that will determine the next action
    try:
        # First get the raw response from the model
        response = model.invoke(prompt)
        
        # Try to parse as JSON, but handle gracefully if it fails
        try:
            # Try to extract JSON from the response if it's embedded in text
            content = response.content
            # Look for JSON-like patterns
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
            else:
                # If no JSON pattern found, create a simple result
                result = {"needs_more_info": False}
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            # Default to responding if JSON parsing fails
            result = {"needs_more_info": False}
        
        # Determine the next action based on the result
        if result.get("needs_more_info", False):
            return {**state, "action": "retrieve"}
        else:
            return {**state, "action": "respond"}
    except Exception as e:
        print(f"Error in think node: {e}")
        # Default to respond if there's an error
        return {**state, "action": "respond"}

# Define the response function
def respond(state: AgentState) -> AgentState:
    """Generate a response to the user's query."""
    messages = state["messages"]
    retrieval_results = state["retrieval_results"]
    
    # Create a prompt that includes the retrieved information
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("system", f"Retrieved information: {retrieval_results}"),
        *[
            (m["role"], m["content"]) 
            for m in messages
        ]
    ])
    
    # Generate a response
    try:
        response = model.invoke(prompt)
        
        # Add the response to the messages
        new_messages = messages + [{"role": "assistant", "content": response.content}]
        
        # Log the response to Langfuse
        langfuse_handler.log_event(
            name="response",
            input=state["current_input"],
            output=response.content
        )
    except Exception as e:
        print(f"Error in respond node: {e}")
        # Provide a fallback response if there's an error
        fallback_response = "I'm sorry, I encountered an issue while processing your request. Please try again."
        new_messages = messages + [{"role": "assistant", "content": fallback_response}]
        
        # Log the error to Langfuse
        langfuse_handler.log_event(
            name="response_error",
            input=state["current_input"],
            output=str(e)
        )
    
    return {
        **state,
        "messages": new_messages,
        "action": "end"
    }

# Define the router function
def router(state: AgentState) -> Literal["retrieve", "think", "respond", "end"]:
    """Route to the next node based on the action."""
    return state["action"]

# Create the graph
workflow = StateGraph(AgentState)

# Add nodes to the graph
workflow.add_node("retrieve", retrieve)
workflow.add_node("think", think)
workflow.add_node("respond", respond)

# Add edges to the graph
workflow.add_edge("retrieve", "think")
workflow.add_edge("think", "retrieve")
workflow.add_edge("think", "respond")
workflow.add_edge("respond", END)
workflow.set_entry_point("retrieve")

# Compile the graph
agent_executor = workflow.compile()

def run_agent(query: str, chat_history: List[Dict] = None) -> Dict:
    """Run the agent with a query and optional chat history."""
    if chat_history is None:
        chat_history = []
    
    # Initialize the state
    initial_state = {
        "messages": chat_history + [{"role": "user", "content": query}],
        "current_input": query,
        "retrieval_results": [],
        "action": "retrieve"
    }
    
    # Run the agent
    result = agent_executor.invoke(initial_state)
    
    # Return the final state
    return result

# Example usage
if __name__ == "__main__":
    while True:
        query = input("\nEnter your question (or 'q' to quit): ")
        if query.lower() == 'q':
            break
        
        result = run_agent(query)
        print("\nAgent response:")
        print(result["messages"][-1]["content"])
