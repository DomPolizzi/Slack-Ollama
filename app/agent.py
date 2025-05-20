from typing import Dict, List, Annotated, TypedDict, Literal
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from copilotkit import LangGraphAgent  # CoPilotKit integration
from copilotkit import LangGraphAgent  # CoPilotKit integration
from langfuse.callback import CallbackHandler  # Keep original import
from langfuse_wrapper import LangfuseWrapper
import os
import json

from config import config

# Initialize Langfuse for observability
raw_langfuse_handler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)

# Wrap with our compatibility wrapper
langfuse_handler = LangfuseWrapper(raw_langfuse_handler)

# Initialize Ollama LLM
ollama_params = {
    "model": config.ollama.llm_model,
    # Pass the raw Langfuse handler as a callback for full trace context
    "callbacks": [raw_langfuse_handler] if raw_langfuse_handler is not None else []
}

# Use Docker URL if provided, otherwise use base_url
if config.ollama.docker_url:
    ollama_params["base_url"] = config.ollama.docker_url
else:
    ollama_params["base_url"] = config.ollama.base_url

try:
    model = OllamaLLM(**ollama_params)
except Exception as e:
    print(f"[ERROR] OllamaLLM initialization failed: {e}")
    model = None  # Fallback for debugging

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

# DEBUG FUNCTIONS
def debug_print_state(prefix, state):
    """Print detailed state debugging information."""
    print(f"\n[DEBUG][{prefix}] STATE DUMP:")
    print(f"  - action: {state.get('action')}")
    print(f"  - current_input: {state.get('current_input')}")
    
    # Debug messages array
    messages = state.get('messages', [])
    print(f"  - messages (type: {type(messages)}, length: {len(messages)}):")
    for i, msg in enumerate(messages):
        if isinstance(msg, dict):
            msg_type = f"dict with keys {list(msg.keys())}"
            content_preview = str(msg.get('content', ''))[:50] + ('...' if len(str(msg.get('content', ''))) > 50 else '')
            print(f"    [{i}] Type: {msg_type}, Content: {content_preview}")
        else:
            print(f"    [{i}] Type: {type(msg)}, Value: {str(msg)[:50]}...")
    
    # Debug retrieval results
    retrieval_results = state.get('retrieval_results', [])
    print(f"  - retrieval_results (type: {type(retrieval_results)}, length: {len(retrieval_results)}):")
    for i, result in enumerate(retrieval_results[:2]):  # Print only first 2 for brevity
        print(f"    [{i}] {str(result)[:50]}...")
    if len(retrieval_results) > 2:
        print(f"    ... and {len(retrieval_results) - 2} more results")

# Define the retrieval function
def retrieve(state: AgentState) -> AgentState:
    """Retrieve relevant documents from the vector store."""
    print(f"\n[DEBUG][retrieve] ENTER with state action: {state.get('action')}")
    debug_print_state("retrieve-input", state)
    
    query = state["current_input"]
    print(f"[DEBUG][retrieve] Processing query: '{query}'")
    
    # Don't modify messages in this step
    try:
        docs = db.similarity_search(query, k=3)
        print(f"[DEBUG][retrieve] Found {len(docs)} documents")
        
        # Extract the content from the documents
        retrieval_results = [doc.page_content for doc in docs]
    except Exception as e:
        print(f"[ERROR][retrieve] Document search failed: {e}")
        retrieval_results = []
    
    # Log the retrieval to Langfuse
    try:
        langfuse_handler.log_event(
            name="retrieval",
            input=query,
            output=retrieval_results
        )
    except Exception as e:
        print(f"[ERROR][retrieve] Langfuse logging error: {e}")
    
    # Create a completely new state with minimal changes
    new_state = {
        **state,
        "retrieval_results": retrieval_results,
        "action": "think"
    }
    
    print(f"[DEBUG][retrieve] EXIT with state action: {new_state.get('action')}")
    debug_print_state("retrieve-output", new_state)
    
    # Return the state, making a clean copy of any collection to avoid reference issues
    return new_state

# Define the thinking function
def think(state: AgentState) -> AgentState:
    """Process the retrieved information and decide on the next action."""
    print(f"\n[DEBUG][think] ENTER with state action: {state.get('action')}")
    debug_print_state("think-input", state)
    
    # Get current state values without modifying them
    retrieval_results = state["retrieval_results"]
    
    # Format messages for model input
    prompt_messages = [
        HumanMessage(content=system_prompt),
        HumanMessage(content=f"Retrieved information: {retrieval_results}")
    ]
    
    # Add user's question
    prompt_messages.append(HumanMessage(content=state["current_input"]))
    
    print(f"[DEBUG][think] Sending {len(prompt_messages)} messages to model")
    for i, msg in enumerate(prompt_messages):
        content_preview = str(msg.content)[:50] + ('...' if len(str(msg.content)) > 50 else '')
        print(f"[DEBUG][think] Message {i}: {content_preview}")
    
    # Create a chain that will determine the next action
    try:
        # Get the raw response from the model using the messages directly
        print(f"[DEBUG][think] Calling model.invoke()")
        response = model.invoke(prompt_messages)
        print(f"[DEBUG][think] Model response type: {type(response)}")

        # Extract content from response
        if isinstance(response, str):
            content = response
        else:
            content = getattr(response, "content", str(response))
        
        content_preview = content[:100] + ('...' if len(content) > 100 else '')
        print(f"[DEBUG][think] Model content: {content_preview}")

        # Try to parse as JSON
        try:
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                print(f"[DEBUG][think] Extracted JSON: {json_str}")
                result = json.loads(json_str)
                print(f"[DEBUG][think] Parsed JSON: {result}")
            else:
                print(f"[DEBUG][think] No JSON found in response, using default")
                result = {"needs_more_info": False}
        except Exception as e:
            print(f"[ERROR][think] Error parsing JSON: {e}")
            result = {"needs_more_info": False}

        # Determine the next action
        next_action = "retrieve" if result.get("needs_more_info", False) else "respond"
        print(f"[DEBUG][think] Decided next action: {next_action}")
    except Exception as e:
        print(f"[ERROR][think] Error in think node: {e}")
        import traceback
        traceback.print_exc()
        next_action = "respond"

    # Create a new state with minimal changes
    new_state = {
        **state,
        "action": next_action
    }
    
    print(f"[DEBUG][think] EXIT with state action: {new_state.get('action')}")
    debug_print_state("think-output", new_state)
    
    return new_state

# Define the response function
def respond(state: AgentState) -> AgentState:
    """Generate a response to the user's query."""
    print(f"\n[DEBUG][respond] ENTER with state action: {state.get('action')}")
    debug_print_state("respond-input", state)
    
    retrieval_results = state["retrieval_results"]
    
    # Deep clone messages to avoid reference issues
    current_messages = []
    for m in state["messages"]:
        if isinstance(m, dict):
            current_messages.append(dict(m))
        else:
            current_messages.append(m)  # If it's not a dict, just add it
    
    print(f"[DEBUG][respond] Creating prompt with retrieval results length: {len(retrieval_results)}")
    
    # Create messages for the prompt
    prompt_messages = [
        HumanMessage(content=system_prompt),
        HumanMessage(content=f"Retrieved information: {retrieval_results}"),
        HumanMessage(content=state["current_input"])
    ]
    
    # Generate a response
    try:
        print(f"[DEBUG][respond] Calling model.invoke()")
        response = model.invoke(prompt_messages)
        print(f"[DEBUG][respond] Model response type: {type(response)}")
        
        # Extract response content
        if isinstance(response, str):
            response_content = response
        else:
            response_content = getattr(response, "content", str(response))
        
        content_preview = response_content[:100] + ('...' if len(response_content) > 100 else '')
        print(f"[DEBUG][respond] Response content: {content_preview}")
        
        # Log the response to Langfuse
        try:
            langfuse_handler.log_event(
                name="response",
                input=state["current_input"],
                output=response_content
            )
        except Exception as e:
            print(f"[ERROR][respond] Langfuse logging error: {e}")
            
    except Exception as e:
        print(f"[ERROR][respond] Error in respond node: {e}")
        import traceback
        traceback.print_exc()
        response_content = "I'm sorry, I encountered an issue while processing your request. Please try again."
    
    print(f"[DEBUG][respond] Current messages: {len(current_messages)}")
    print(f"[DEBUG][respond] Adding assistant response: {response_content[:50]}...")
    
    # Create a new message list with the assistant's response added
    result_messages = current_messages + [{"role": "assistant", "content": response_content}]
    
    # Create the result state avoiding any reference issues
    new_state = dict(state)  # Create a copy of the state
    new_state["messages"] = result_messages  # Update messages
    new_state["action"] = "end"  # Set final action
    
    print(f"[DEBUG][respond] EXIT with state action: {new_state.get('action')}")
    debug_print_state("respond-output", new_state)
    
    # Return a completely fresh copy of the state
    return {
        "messages": result_messages,
        "current_input": state["current_input"],
        "retrieval_results": state["retrieval_results"],
        "action": "end"
    }

# Define the router function
def router(state: AgentState) -> Literal["retrieve", "think", "respond", "end"]:
    """Route to the next node based on the action."""
    print(f"[DEBUG][router] State messages type: {type(state['messages'])}, value: {state['messages']}")
    return state["action"]

# Create a simplified workflow without cross-function calls
from langchain_core.messages import SystemMessage

def simple_agent(state: Dict) -> Dict:
    """A simplified agent that doesn't use the complex LangGraph workflow."""
    print("\n[DEBUG][simple_agent] ENTER")
    
    # Extract key information from state
    query = state["current_input"]
    messages = state.get("messages", [])
    print(f"[DEBUG][simple_agent] Processing query: '{query}'")
    print(f"[DEBUG][simple_agent] Messages: {len(messages)}")
    
    # Attempt to retrieve information
    try:
        print(f"[DEBUG][simple_agent] Retrieving documents")
        docs = db.similarity_search(query, k=3)
        retrieval_results = [doc.page_content for doc in docs]
        print(f"[DEBUG][simple_agent] Found {len(retrieval_results)} documents")
    except Exception as e:
        print(f"[ERROR][simple_agent] Document search failed: {e}")
        retrieval_results = []
    
    # Format the prompt
    prompt_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Retrieved information: {retrieval_results}"),
        HumanMessage(content=query)
    ]
    
    # Generate response with LLM
    try:
        print(f"[DEBUG][simple_agent] Calling model.invoke()")
        response = model.invoke(prompt_messages)
        
        # Extract response content
        if isinstance(response, str):
            response_content = response
        else:
            response_content = getattr(response, "content", str(response))
        
        print(f"[DEBUG][simple_agent] Got response: {response_content[:50]}...")
    except Exception as e:
        print(f"[ERROR][simple_agent] Error calling model: {e}")
        response_content = "I'm sorry, I encountered an error while processing your request."
    
    # Create final message list
    result_messages = messages + [{"role": "assistant", "content": response_content}]
    
    # Log if possible
    try:
        langfuse_handler.log_event(
            name="simple_agent",
            input=query,
            output=response_content
        )
    except Exception as e:
        print(f"[ERROR][simple_agent] Logging error: {e}")
    
    print(f"[DEBUG][simple_agent] EXIT")
    
    # Return result
    return {
        "messages": result_messages
    }

# Create a simple executor function
def agent_executor(state: Dict) -> Dict:
    """Execute the simplified agent."""
    try:
        print(f"[DEBUG][agent_executor] ENTER")
        return simple_agent(state)
    except Exception as e:
        print(f"[ERROR][agent_executor] Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback result
        messages = state.get("messages", [])
        return {
            "messages": messages + [
                {"role": "assistant", "content": "I'm sorry, I encountered an error while processing your request."}
            ]
        }

# --- CoPilotKit Integration ---
# Simplified CoPilotKit agent that doesn't rely on LangGraph
def copilot_agent(state: Dict) -> Dict:
    """CoPilotKit-compatible agent function."""
    return simple_agent(state)

def run_agent(query: str, chat_history: List[Dict] = None) -> Dict:
    """Run the agent with a query and optional chat history."""
    print(f"\n[DEBUG][run_agent] Starting with query: '{query}'")
    
    if chat_history is None:
        chat_history = []
        print(f"[DEBUG][run_agent] No chat history provided, using empty list")
    else:
        print(f"[DEBUG][run_agent] Chat history provided, length: {len(chat_history)}")
        for i, msg in enumerate(chat_history[:2]):  # Show only first 2 for brevity
            if isinstance(msg, dict):
                role = msg.get('role', 'unknown')
                content = str(msg.get('content', ''))[:50] + ('...' if len(str(msg.get('content', ''))) > 50 else '')
                print(f"[DEBUG][run_agent] History[{i}]: {role} - {content}")
    
    # Create a simple starting state with just the user query
    initial_state = {
        "messages": chat_history + [{"role": "user", "content": query}],
        "current_input": query
    }
    
    debug_print_state("run_agent-initial_state", initial_state)
    
    # Run the agent with error handling
    try:
        print(f"[DEBUG][run_agent] Calling agent_executor")
        result = agent_executor(initial_state)
        print(f"[DEBUG][run_agent] Agent execution completed")
        debug_print_state("run_agent-result", result)
        return result
    except Exception as e:
        print(f"[ERROR][run_agent] Error in agent execution: {e}")
        import traceback
        traceback.print_exc()
        
        # Return a minimal valid result
        fallback_result = {
            "messages": initial_state["messages"] + [
                {"role": "assistant", "content": "I'm sorry, I encountered an error while processing your request."}
            ]
        }
        debug_print_state("run_agent-fallback_result", fallback_result)
        return fallback_result

# Example usage
if __name__ == "__main__":
    while True:
        query = input("\nEnter your question (or 'q' to quit): ")
        if query.lower() == 'q':
            break
        
        result = run_agent(query)
        print("\nAgent response:")
        print(result["messages"][-1]["content"])
