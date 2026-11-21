import time
from fastapi import APIRouter, HTTPException
from app.models.schemas import TargetConfig, ChatRequest
from app.services.llm_providers import LLMError
from app.services.target_ai import ask_target

router = APIRouter(prefix="/api/target", tags=["target"])


@router.post("/test-connection")
def test_connection(cfg: TargetConfig):
    """Page 2 'Test connection' button: sends a tiny message to check the model works."""
    start = time.time()
    try:
        reply = ask_target("You are a connection test.", "Reply with the single word: OK",
                           cfg.provider, cfg.model, cfg.temperature)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"ok": True, "reply": reply.strip(),
            "latency_ms": int((time.time() - start) * 1000)}


@router.post("/chat")
def chat(req: ChatRequest):
    """Send one message to the target chatbot with a given system prompt."""
    try:
        reply = ask_target(req.system_prompt, req.user_message,
                           req.provider, req.model, req.temperature)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"response": reply}
from app.database.connection import get_db
from app.evaluators.rule_checks import canary_leaked
from app.services.prompt_store import get_latest
from app.services.chain import is_chain, ask_chain
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session


class RedTeamRequest(BaseModel):
    prompt_name: str = Field(min_length=1)
    user_message: str = Field(min_length=1, max_length=4000)
    provider: str = "ollama"
    model: str = "llama3.2"


@router.post("/redteam")
def redteam(req: RedTeamRequest, db: Session = Depends(get_db)):
    """Send one custom attack to a stored prompt version. Not saved, not scored."""
    prompt = get_latest(db, req.prompt_name)
    if prompt is None:
        raise HTTPException(status_code=404, detail=f"Prompt {req.prompt_name} not found.")
    try:
        if is_chain(prompt.content):
            reply = ask_chain(prompt.content, req.user_message, req.provider, req.model, 0.0)
        else:
            reply = ask_target(prompt.content, req.user_message, req.provider, req.model, 0.0)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    return {"prompt": req.prompt_name, "response": reply,
            "canary_leaked": canary_leaked(reply)}