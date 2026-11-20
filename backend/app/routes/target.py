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