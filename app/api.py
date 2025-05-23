"""
API server for the LLM Agent.
This exposes the agent's functionality via a REST API.
"""

import os
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import json
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Import agent functionality
from agent import run_agent, copilot_agent
from document_loader import load_documents
from config import config


# Create FastAPI app
app = FastAPI(
    title="LLM Agent API",
    description="API for the LLM Agent with LangGraph, Langfuse, Ollama, and ChromaDB",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins including localhost
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"]  # Expose all headers
)

# Print app setup info
print(f"FastAPI app initialized with CORS: allow_origins=['*']")
print(f"WebSocket endpoint available at: /ws")

from slack_integration import init_slack
app.add_event_handler("startup", init_slack)

# Define request and response models
class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict]] = None

class QueryResponse(BaseModel):
    response: str
    chat_history: List[Dict]

class DocumentRequest(BaseModel):
    path: str

class DocumentResponse(BaseModel):
    num_documents: int
    message: str

# Define API endpoints

from fastapi import Request, Header, Response

@app.post("/coagent")
async def coagent_endpoint(request: Request):
    """Endpoint for CoPilotKit to interact with the agent."""
    try:
        print("[DEBUG][coagent_endpoint] Received request")
        payload = await request.json()
        # CoPilotKit expects the agent to be called with the full state dict
        state = payload.get("state", {})
        
        print(f"[DEBUG][coagent_endpoint] State: {state}")
        
        # Run the agent using the simplified function
        result = copilot_agent(state)
        
        print(f"[DEBUG][coagent_endpoint] Result: {result}")
        return result
    except Exception as e:
        print(f"[ERROR][coagent_endpoint] CoPilotKit agent error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"CoPilotKit agent error: {e}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "LLM Agent API is running",
        "docs": "/docs",
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query the agent."""
    try:
        # Run the agent
        result = run_agent(request.query, request.chat_history)
        
        # Extract the response
        response = result["messages"][-1]["content"]
        
        # Return the response and updated chat history
        return QueryResponse(
            response=response,
            chat_history=result["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Alias chat endpoint for v1 compatibility
class ChatRequest(BaseModel):
    message: str

@app.post("/v1/chat")
async def v1_chat(request: ChatRequest):
    """Chat endpoint alias for frontend compatibility."""
    try:
        result = run_agent(request.message)
        response = result["messages"][-1]["content"]
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_alias(request: ChatRequest):
    """Chat endpoint alias at /chat for compatibility."""
    return await v1_chat(request)

@app.post("/documents", response_model=DocumentResponse)
async def upload_documents(request: DocumentRequest):
    """Upload documents to the vector store."""
    try:
        # Load documents
        num_docs = load_documents(request.path)
        
        # Return the number of documents loaded
        return DocumentResponse(
            num_documents=num_docs,
            message=f"Successfully loaded {num_docs} document chunks into the vector store."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            # Parse the message
            try:
                message = json.loads(data)
                query = message.get("query", "")
                chat_history = message.get("chat_history", [])
                
                print(f"WebSocket received query: {query}")
                
                try:
                    # Run the agent
                    result = run_agent(query, chat_history)
                    
                    # Extract the response
                    response = result["messages"][-1]["content"]
                    
                    # Send the response back to the client
                    await manager.send_message(
                        json.dumps({
                            "response": response,
                            "chat_history": result["messages"]
                        }),
                        websocket
                    )
                except Exception as e:
                    print(f"Error running agent: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    
                    # Send error response with fallback message
                    await manager.send_message(
                        json.dumps({
                            "response": "I'm sorry, I encountered an issue while processing your request.",
                            "error": str(e)
                        }),
                        websocket
                    )
            except json.JSONDecodeError as json_err:
                print(f"JSON decode error: {str(json_err)}")
                await manager.send_message(
                    json.dumps({
                        "response": "I couldn't understand your message format.",
                        "error": "Invalid JSON format"
                    }),
                    websocket
                )
            except Exception as e:
                print(f"Unexpected WebSocket error: {str(e)}")
                import traceback
                traceback.print_exc()
                
                await manager.send_message(
                    json.dumps({
                        "response": "I'm sorry, an unexpected error occurred.",
                        "error": str(e)
                    }),
                    websocket
                )
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
        ws_ping_interval=20,  # Send ping frames every 20 seconds
        ws_ping_timeout=30    # Wait 30 seconds for pong response before closing
    )
