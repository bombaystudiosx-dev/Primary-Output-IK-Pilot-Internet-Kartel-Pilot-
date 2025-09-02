import os
import uuid
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx

from agent.core import Agent, ToolRegistry
from tools.kubernetes_tool import KubernetesTool
from tools.shell_tool import ShellTool

load_dotenv()

app = FastAPI(title="IK-Pilot", version="0.1.0")

MODEL = os.getenv("MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
HUMAN_APPROVAL = os.getenv("HUMAN_APPROVAL", "true").lower() == "true"
ALLOW_DANGEROUS_TOOLS = os.getenv("ALLOW_DANGEROUS_TOOLS", "false").lower() == "true"

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None
    force: Optional[bool] = None   # bypass approval if True

class ChatOut(BaseModel):
    session_id: str
    thought: str
    actions: List[Dict[str, Any]]
    output: str

@app.get("/healthz")
def healthz():
    return {"ok": True}

def openai_client():
    # minimal client for chat completions compatible with OpenAI API v1
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    return OPENAI_API_BASE, headers

def build_agent() -> Agent:
    registry = ToolRegistry()
    registry.register(KubernetesTool())
    # Register shell only if explicitly allowed
    if ALLOW_DANGEROUS_TOOLS:
        registry.register(ShellTool())
    agent = Agent(model=MODEL, approval_required=HUMAN_APPROVAL, tool_registry=registry)
    return agent

@app.post("/chat", response_model=ChatOut)
async def chat(payload: ChatIn):
    if not OPENAI_API_KEY and "openai" in OPENAI_API_BASE:
        raise HTTPException(status_code=400, detail="OPENAI_API_KEY missing. Set it in .env")
    session_id = payload.session_id or str(uuid.uuid4())
    agent = build_agent()
    base, headers = openai_client()
    try:
        result = await agent.run(message=payload.message, session_id=session_id, api_base=base, headers=headers, force=payload.force)
        return ChatOut(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
