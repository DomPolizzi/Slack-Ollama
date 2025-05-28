import os
from typing import List, Dict, Optional
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from configs.config import config
from components.slack_integration import init_slack
from components.langgraph_supervisor import run_graph_supervisor
from langfuse.callback import CallbackHandler

class QueryRequest(BaseModel):
    query: str
    chat_history: Optional[List[Dict]] = None

class QueryResponse(BaseModel):
    response: str
    chat_history: List[Dict]

langfuse_hangler = CallbackHandler(
    public_key=config.langfuse.public_key,
    secret_key=config.langfuse.secret_key,
    host=config.langfuse.host
)


app = FastAPI(
    title="Pops",
    description="Supervisor agent API for LangGraph workflows",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Slack integration on startup
app.add_event_handler("startup", init_slack)

@app.get("/")
async def root():
    return {"message": "Supervisor API running"}

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    try:
        state = run_graph_supervisor({"query": request.query, "chat_history": request.chat_history or []})
        return QueryResponse(
            response=state["messages"][-1]["content"],
            chat_history=state["messages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)
