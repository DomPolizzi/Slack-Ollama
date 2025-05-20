# LLM Agent with LangGraph, Langfuse, Ollama, and ChromaDB

This project implements an LLM Agent using LangGraph for orchestration, Langfuse for observability, Ollama for local LLM inference, and ChromaDB for vector storage.

## Features

- **LangGraph**: Orchestrates the agent's workflow with a state graph
- **Langfuse**: Provides observability and analytics for the agent
- **Ollama**: Runs LLMs locally for inference and embeddings
- **ChromaDB**: Stores document embeddings for retrieval
- **Modern Frontend**: Provides a responsive web interface for interacting with the agent

## Prerequisites

- Python 3.9+
- [Ollama](https://ollama.ai/) installed and running locally
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd llm-agent
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Make sure Ollama is running and has the required models:
   ```bash
   # Start Ollama (if not already running)
   ollama serve

   # In another terminal, pull the required models
   ollama pull llama3.2
   ollama pull nomic-embed-text-v1.5
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env` (or use the existing `.env` file)
   - Update the values as needed

## Usage

### Running with Docker Compose

The easiest way to run the entire stack is with Docker Compose:

```bash
docker-compose up -d
```

This will start:
- Ollama service for LLM inference
- ChromaDB service for vector storage
- Backend API service
- Frontend service

Then open your browser to http://localhost:3000 to access the frontend.

### Running Locally

If you prefer to run the components individually:

1. Run the API server:
   ```bash
   cd app
   uvicorn api:app --reload
   ```

2. In another terminal, run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

3. Open your browser to http://localhost:3000

### CLI Mode

You can also run the agent in CLI mode:

```bash
cd app
python main.py
```

The application will prompt you to load documents into the vector store (optional) and then you can start asking questions to the agent.

## Project Structure

```
llm-agent/
├── app/                  # Backend application
│   ├── agent.py          # LangGraph agent implementation
│   ├── config.py         # Configuration management
│   ├── document_loader.py # Document loading utilities
│   ├── main.py           # CLI entry point
│   └── api.py            # FastAPI server
├── frontend/             # Web frontend
│   ├── src/              # Source code
│   │   ├── app/          # Next.js app directory
│   │   └── components/   # React components
│   ├── public/           # Static assets
│   ├── package.json      # Frontend dependencies
│   └── tsconfig.json     # TypeScript configuration
├── .env                  # Environment variables
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile.api        # Dockerfile for the API
├── Dockerfile.frontend   # Dockerfile for the frontend
└── requirements.txt      # Python dependencies
```

## Configuration

The agent can be configured using environment variables or by modifying the `.env` file:

- **Langfuse Configuration**:
  - `LANGFUSE_PUBLIC_KEY`: Your Langfuse public key
  - `LANGFUSE_SECRET_KEY`: Your Langfuse secret key
  - `LANGFUSE_HOST`: Langfuse host URL

- **Ollama Configuration**:
  - `OLLAMA_BASE_URL`: URL for the Ollama API (default: http://localhost:11434)
  - `OLLAMA_DOCKER_URL`: URL for Ollama running in Docker (default: http://ollama:11434)
  - `OLLAMA_LLM_MODEL`: Model to use for LLM inference (default: llama3.2)
  - `OLLAMA_EMBEDDING_MODEL`: Model to use for embeddings (default: nomic-embed-text-v1.5)

- **ChromaDB Configuration**:
  - `CHROMA_PERSIST_DIRECTORY`: Directory to persist ChromaDB (default: ./chroma_db)
  - `CHROMA_COLLECTION_NAME`: Name of the ChromaDB collection (default: llm_agent)
  - `CHROMA_HOST`: Host for ChromaDB running in Docker (default: chroma)
  - `CHROMA_PORT`: Port for ChromaDB running in Docker (default: 8000)

## How It Works

1. The agent uses a LangGraph workflow with the following nodes:
   - `retrieve`: Retrieves relevant documents from ChromaDB
   - `think`: Processes the retrieved information and decides on the next action
   - `respond`: Generates a response to the user's query

2. The workflow is orchestrated by a state machine that transitions between these nodes based on the agent's decisions.

3. Langfuse is used to log events and track the agent's performance.

4. ChromaDB stores document embeddings for retrieval.

## Extending the Agent

To extend the agent with new capabilities:

1. Add new nodes to the LangGraph workflow in `agent.py`
2. Update the state schema to include new state variables
3. Add new edges to the graph to connect the new nodes
4. Update the router function to route to the new nodes

## Troubleshooting

### Common Errors and Solutions

#### LangchainCallbackHandler Error

If you encounter an error like `'LangchainCallbackHandler' object has no attribute 'log_event'`, it's likely due to an incompatibility between the code and your installed version of langfuse.

This project includes a robust solution using a compatibility wrapper (`langfuse_wrapper.py`) that handles differences in the Langfuse API across versions. The wrapper:

1. Attempts to use the appropriate API method based on what's available in your installed version
2. Falls back to console logging if no compatible API is found
3. Catches and handles any exceptions that might occur during logging

Implementation details:
```python
# In agent.py
from langfuse.callback import CallbackHandler
from langfuse_wrapper import LangfuseWrapper

# Initialize with original handler
raw_langfuse_handler = CallbackHandler(...)

# Wrap with our compatibility wrapper
langfuse_handler = LangfuseWrapper(raw_langfuse_handler)

# Then use the wrapper for logging
langfuse_handler.log_event(name="event_name", input=input_data, output=output_data)
```

#### LangGraph Concurrent Update Error

If you encounter an error like `"Can receive only one value per step. Use an Annotated key to handle multiple values."` or `"INVALID_CONCURRENT_GRAPH_UPDATE"`, this is likely due to conflicting updates to the LangGraph state.

The solution involves multiple improvements:

1. Remove callback handlers from the LLM initialization:
```python
# Initialize Ollama LLM without callbacks
ollama_params = {
    "model": config.ollama.llm_model,
    "callbacks": []  # Empty callbacks to avoid concurrent updates
}
```

2. Use proper deep copying of all state objects in each node function:
```python
messages = state["messages"].copy()  # Make a copy to avoid modifying the original
```

3. Always create fresh state dictionaries instead of using the spread operator:
```python
# Create a completely new state to avoid any reference issues
return {
    "messages": messages,
    "current_input": query,
    "retrieval_results": retrieval_results,
    "action": "think"
}
```

4. Use direct message objects instead of ChatPromptTemplate:
```python
# Create messages for the prompt
prompt_messages = [
    HumanMessage(content=system_prompt),
    HumanMessage(content=f"Retrieved information: {retrieval_results}")
]

# Add the chat history messages
for m in messages:
    role = m["role"]
    content = m["content"]
    if role == "user":
        prompt_messages.append(HumanMessage(content=content))
    elif role == "assistant":
        prompt_messages.append(AIMessage(content=content))

# Use the messages directly
response = model.invoke(prompt_messages)
```

These changes ensure proper state isolation and prevent concurrent updates to the graph state.

## License

[MIT License](LICENSE)
