# LangGraph Supervisor API

Supervisor API provides a LangGraph-based orchestrator for Slack-driven HR workflows using Ollama, ChromaDB, LangChain, LangGraph, and Langfuse.

## Features

- **Supervisor Graph**: Multi-node pipeline with classification, retrieval, grading, and response stages
- **LangChain Integration**: Uses `Ollama` LLM & embeddings, `ConversationalRetrievalChain` over ChromaDB
- **LangGraph Orchestration**: `StateGraph` defines conditional workflow, compiled & executed dynamically
- **Langfuse Tracing**: Session and event logging for observability and debugging
- **Slack Bolt**: Socket Mode listener routes incoming messages into the graph

## Quickstart

1. Copy environment template:
   ```bash
   cd supervisor_api
   cp .env.example .env
   ```
2. Fill in your credentials in `.env`.
3. Build and run with Docker Compose:
   ```bash
   docker-compose up --build
   ```
4. Service endpoints:
   - `GET /` &rarr; health check  
   - `POST /query`  
     ```json
     {
       "query": "How do I update our time-off policy?",
       "chat_history": []
     }
     ```
     Response:
     ```json
     {
       "response": "<assistant reply>",
       "chat_history": [ {...}, {...} ]
     }
     ```

## Development

- Code lives under `app/`:
  - `configs/config.py` &rarr; Pydantic settings (Slack, Ollama, Chroma, Langfuse)
  - `components/langfuse_wrapper.py` &rarr; Langfuse compatibility & tracing
  - `components/supervisor_agent.py` &rarr; LangChain-based helper functions
  - `components/langgraph_supervisor.py` &rarr; Graph definition & execution
  - `components/slack_integration.py` &rarr; Slack Bolt event handler
  - `main.py` &rarr; FastAPI setup & `/query` endpoint

## Notes

- Ensure Ollama and ChromaDB services (or their Docker containers) are running and reachable via the URLs in `.env`.
- For advanced workflows, modify `langgraph_supervisor.py` to add or rewire graph nodes and edges.
- Langfuse tracing requires valid `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY`.

## License

MIT
