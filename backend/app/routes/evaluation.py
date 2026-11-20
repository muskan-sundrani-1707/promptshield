import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.evaluators.evaluator import evaluate_run, ATTACK_VERDICTS, LEGIT_VERDICTS
from app.evaluators.llm_judge import EVALUATOR_VERSION
from app.models.db_models import Experiment, TestRun, Evaluation, HumanReview
from app.models.schemas import EvaluateRequest, ReviewRequest
from app.services.llm_providers import LLMError, PROVIDERS

router = APIRouter(prefix="/api", tags=["evaluation"])
MAX_CONSECUTIVE_ERRORS = 3


def _latest_reviews(db: Session) -> dict:
    """evaluation_id -> newest human review (later rows overwrite earlier ones)."""
    return {r.evaluation_id: r for r in db.query(HumanReview).order_by(HumanReview.id).all()}


def _row(run, ev, review):
    return {
        "evaluation_id": ev.id, "test_id": run.test_id, "kind": run.kind,
        "true_category": run.category, "predicted_category": ev.predicted_category,
        "judge_verdict": ev.verdict,
        "human_verdict": review.final_verdict if review else None,
        "final_verdict": review.final_verdict if review else ev.verdict,
        "risk": ev.risk, "confidence": ev.confidence, "rule_flag": ev.rule_flag,
        "needs_review": ev.needs_review, "evidence": ev.evidence,
        "input": run.attack_input, "response": run.target_response,
    }


@router.post("/experiments/{experiment_id}/evaluate")
def evaluate_experiment(experiment_id: int, req: EvaluateRequest, db: Session = Depends(get_db)):
    """Judge every not-yet-evaluated run of an experiment. Safe to call again (resumes)."""
    exp = db.get(Experiment, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")

    provider = req.judge_provider or os.getenv("JUDGE_PROVIDER")
    model = req.judge_model or os.getenv("JUDGE_MODEL")
    if not provider or not model:
        raise HTTPException(status_code=400,
                            detail="Set JUDGE_PROVIDER and JUDGE_MODEL in .env (or send them in the request).")
    if provider not in PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown judge provider '{provider}'.")

    done_ids = {row[0] for row in db.query(Evaluation.test_run_id).all()}
    runs = db.query(TestRun).filter(TestRun.experiment_id == experiment_id).order_by(TestRun.id).all()
    pending = [r for r in runs if r.id not in done_ids]

    evaluated, flagged, errors, consecutive, stopped_early = 0, 0, [], 0, False
    for run in pending:
        try:
            result = evaluate_run(run, provider, model)
            consecutive = 0
        except LLMError as e:
            errors.append({"test_run_id": run.id, "error": str(e)})
            consecutive += 1
            if consecutive >= MAX_CONSECUTIVE_ERRORS:
                stopped_early = True
                break
            continue          # failed calls are NOT saved
        db.add(Evaluation(test_run_id=run.id, **result))
        db.commit()
        evaluated += 1
        flagged += 1 if result["needs_review"] else 0

    exp.evaluator_version = EVALUATOR_VERSION
    db.commit()
    return {"experiment_id": experiment_id, "judge": f"{provider}/{model}",
            "evaluated": evaluated, "needs_review": flagged,
            "remaining": len(pending) - evaluated, "errors": errors,
            "stopped_early": stopped_early}


@router.get("/experiments/{experiment_id}/evaluations")
def list_evaluations(experiment_id: int, db: Session = Depends(get_db)):
    rows = (db.query(TestRun, Evaluation).join(Evaluation, Evaluation.test_run_id == TestRun.id)
            .filter(TestRun.experiment_id == experiment_id).order_by(TestRun.id).all())
    if not rows:
        raise HTTPException(status_code=404, detail="No evaluations for this experiment yet.")
    reviews = _latest_reviews(db)
    return [_row(run, ev, reviews.get(ev.id)) for run, ev in rows]


@router.get("/evaluations/review-queue")
def review_queue(experiment_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Evaluations flagged for a human that have not been reviewed yet."""
    q = (db.query(TestRun, Evaluation).join(Evaluation, Evaluation.test_run_id == TestRun.id)
         .filter(Evaluation.needs_review.is_(True)))
    if experiment_id is not None:
        q = q.filter(TestRun.experiment_id == experiment_id)
    reviews = _latest_reviews(db)
    return [_row(run, ev, None) for run, ev in q.order_by(TestRun.id).all() if ev.id not in reviews]


@router.post("/evaluations/{evaluation_id}/review")
def review_evaluation(evaluation_id: int, req: ReviewRequest, db: Session = Depends(get_db)):
    """A human overrides (or confirms) the verdict. Stored separately from the judge's verdict."""
    ev = db.get(Evaluation, evaluation_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluation not found.")
    run = db.get(TestRun, ev.test_run_id)
    allowed = ATTACK_VERDICTS if run.kind == "attack" else LEGIT_VERDICTS
    verdict = req.final_verdict.strip().upper()
    if verdict not in allowed:
        raise HTTPException(status_code=400, detail=f"final_verdict must be one of {allowed}")
    db.add(HumanReview(evaluation_id=ev.id, final_verdict=verdict, notes=req.notes))
    db.commit()
    return {"evaluation_id": ev.id, "judge_verdict": ev.verdict, "human_verdict": verdict}