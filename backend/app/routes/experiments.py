from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.db_models import Experiment, TestRun, PromptVersion
from app.models.schemas import RunRequest
from app.services import dataset_loader, prompt_store, test_runner

router = APIRouter(prefix="/api", tags=["experiments"])


@router.post("/prompts/seed")
def seed_prompts(db: Session = Depends(get_db)):
    """Load prompts/*.txt into the database."""
    return prompt_store.seed_prompts(db)


@router.get("/prompts")
def list_prompts(db: Session = Depends(get_db)):
    rows = db.query(PromptVersion).order_by(PromptVersion.id).all()
    return [{"id": r.id, "name": r.name, "technique": r.technique,
             "parent_id": r.parent_id, "content": r.content} for r in rows]


@router.get("/datasets/summary")
def dataset_summary():
    attacks = dataset_loader.load_attack_cases()
    legit = dataset_loader.load_legit_cases()
    per_cat = {c: sum(1 for a in attacks if a["category"] == c)
               for c in dataset_loader.ATTACK_CATEGORIES}
    return {"attack_total": len(attacks), "legit_total": len(legit), "attacks_per_category": per_cat}


@router.post("/experiments/run")
def run(req: RunRequest, db: Session = Depends(get_db)):
    """Run the fixed dataset on one prompt version and save real responses."""
    try:
        return test_runner.run_experiment(
            db, req.prompt_name, req.provider, req.model, req.temperature,
            req.repeats, req.categories, req.include_attacks, req.include_legit, req.limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/experiments")
def list_experiments(db: Session = Depends(get_db)):
    rows = db.query(Experiment).order_by(Experiment.id.desc()).all()
    return [{"id": r.id, "name": r.name, "prompt_version_id": r.prompt_version_id,
             "model": r.target_model, "temperature": r.temperature,
             "created_at": r.created_at.isoformat()} for r in rows]


@router.get("/experiments/{experiment_id}/runs")
def experiment_runs(experiment_id: int, db: Session = Depends(get_db)):
    runs = db.query(TestRun).filter(TestRun.experiment_id == experiment_id).order_by(TestRun.id).all()
    if not runs:
        raise HTTPException(status_code=404, detail="No runs for this experiment.")
    return [{"id": r.id, "test_id": r.test_id, "kind": r.kind, "category": r.category,
             "input": r.attack_input, "expected": r.expected_behavior,
             "response": r.target_response, "run_index": r.run_index} for r in runs]