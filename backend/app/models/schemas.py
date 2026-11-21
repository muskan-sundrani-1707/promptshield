from typing import Literal, Optional
from pydantic import BaseModel, Field


class TargetConfig(BaseModel):
    provider: Literal["ollama", "anthropic", "openai"]
    model: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)


class ChatRequest(TargetConfig):
    system_prompt: str = Field(min_length=1, max_length=20000)
    user_message: str = Field(min_length=1, max_length=4000)
class RunRequest(TargetConfig):
    prompt_name: str = Field(min_length=1)               # e.g. "V0"
    repeats: int = Field(default=1, ge=1, le=5)          # LLMs vary, so repeat
    categories: Optional[list[str]] = None               # None = all categories
    include_attacks: bool = True
    include_legit: bool = True
    dataset: Literal["main", "heldout","fresh"] = "main"
    limit: Optional[int] = Field(default=None, ge=1)     # run only first N per kind (for quick tests)
class EvaluateRequest(BaseModel):
    # If left empty, JUDGE_PROVIDER / JUDGE_MODEL from .env are used
    judge_provider: Optional[Literal["ollama", "anthropic", "openai"]] = None
    judge_model: Optional[str] = None
class ApproveRequest(BaseModel):
    approved: bool
    edited_patch: Optional[str] = Field(default=None, max_length=500)   # human may reword the rule

class ReviewRequest(BaseModel):
    final_verdict: str = Field(min_length=1)
    notes: Optional[str] = Field(default=None, max_length=1000)