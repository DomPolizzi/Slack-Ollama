"""
API server for the LLM Agent.
This exposes the agent's functionality via a REST API.
"""

import os
import json
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Use package-relative imports
from agents.agent import run_agent
from components.slack_integration import init_slack
from components.langgraph_agent import run_graph_agent
from components.document_loader import load_documents
from configs.config import config

# Create FastAPI app
app = FastAPI(
    title="Pops Agent API",
    description="API for the Pops",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Initialize Slack integration on startup
app.add_event_handler("startup", init_slack)

# Pydantic models
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

@app.get("/")
async def root():
    return {"message": "LLM Agent API is running", "docs": "/docs"}

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        state = run_agent(request.query, request.chat_history)
        return QueryResponse(
            response=state["messages"][-1]["content"],
            chat_history=state["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/graph_query", response_model=QueryResponse)
async def graph_query_endpoint(request: QueryRequest):
    try:
        state = run_graph_agent(request.query, request.chat_history)
        return QueryResponse(
            response=state["messages"][-1]["content"],
            chat_history=state["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/chat")
async def v1_chat(request: QueryRequest):
    try:
        state = run_agent(request.query, request.chat_history)
        return {"response": state["messages"][-1]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/documents", response_model=DocumentResponse)
async def upload_documents(request: DocumentRequest):
    try:
        num = load_documents(request.path)
        return DocumentResponse(num_documents=num, message=f"Loaded {num} document chunks.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

    async def send(self, message: str, ws: WebSocket):
        await ws.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            try:
                payload = json.loads(data)
                query = payload.get("query", "")
                history = payload.get("chat_history", [])
                state = run_agent(query, history)
                msg = json.dumps({
                    "response": state["messages"][-1]["content"],
                    "chat_history": state["messages"]
                })
                await manager.send(msg, ws)
            except Exception as e:
                error_msg = json.dumps({"response": "Error", "error": str(e)})
                await manager.send(error_msg, ws)
    except WebSocketDisconnect:
        manager.disconnect(ws)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8080, reload=True)
