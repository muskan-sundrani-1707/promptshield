import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.evaluators.rule_checks import canary_leaked
from app.generators import defense_generator
from app.models.db_models import Defense, Experiment
from app.models.schemas import ApproveRequest, EvaluateRequest
from app.services.llm_providers import LLMError, PROVIDERS

router = APIRouter(prefix="/api", tags=["defenses"])


@router.post("/experiments/{experiment_id}/defenses/generate")
def generate(experiment_id: int, req: EvaluateRequest, db: Session = Depends(get_db)):
    if db.get(Experiment, experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    provider = req.judge_provider or os.getenv("JUDGE_PROVIDER")
    model = req.judge_model or os.getenv("JUDGE_MODEL")
    if not provider or not model or provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail="Set JUDGE_PROVIDER and JUDGE_MODEL (or send them).")
    try:
        result = defense_generator.generate_defenses(db, experiment_id, provider, model)
    except LLMError as e:
        raise HTTPException(status_code=502, detail=str(e))
    if not result["created"] and not result["skipped"]:
        result["message"] = "No new failures to build defenses from (or they already exist)."
    return result


@router.get("/defenses")
def list_defenses(experiment_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Defense)
    if experiment_id is not None:
        q = q.filter(Defense.experiment_id == experiment_id)
    return [{"id": d.id, "experiment_id": d.experiment_id, "observed_failure": d.observed_failure,
             "explanation": d.explanation, "suggested_patch": d.suggested_patch,
             "approved": d.approved, "new_prompt_version_id": d.new_prompt_version_id}
            for d in q.order_by(Defense.id).all()]


@router.post("/defenses/{defense_id}/approve")
def approve(defense_id: int, req: ApproveRequest, db: Session = Depends(get_db)):
    d = db.get(Defense, defense_id)
    if d is None:
        raise HTTPException(status_code=404, detail="Defense not found.")
    if req.edited_patch:
        if canary_leaked(req.edited_patch):
            raise HTTPException(status_code=400, detail="Patch must not contain the secret value.")
        d.suggested_patch = req.edited_patch.strip()
    d.approved = req.approved
    db.commit()
    return {"id": d.id, "approved": d.approved, "suggested_patch": d.suggested_patch}


@router.post("/experiments/{experiment_id}/defenses/build-prompt")
def build_prompt(experiment_id: int, db: Session = Depends(get_db)):
    """Create prompt version V6 = base prompt + all approved patches."""
    if db.get(Experiment, experiment_id) is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    try:
        return defense_generator.build_v6(db, experiment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))