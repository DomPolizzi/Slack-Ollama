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
from agent import run_agent
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
    allow_origins=["*"],  # Allow all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

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
            except json.JSONDecodeError:
                await manager.send_message(
                    json.dumps({
                        "error": "Invalid JSON"
                    }),
                    websocket
                )
            except Exception as e:
                await manager.send_message(
                    json.dumps({
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
        port=8000,
        reload=True
    )
