from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services import metrics

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get("/experiments/{experiment_id}/metrics")
def experiment_metrics(experiment_id: int, db: Session = Depends(get_db)):
    result = metrics.compute_metrics(db, experiment_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    return result


@router.get("/metrics/compare")
def compare_experiments(ids: str = Query(..., description="comma separated, e.g. 2,3,4"),
                        db: Session = Depends(get_db)):
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="ids must be numbers like 2,3,4")
    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Give at least two experiment ids.")
    try:
        return metrics.compare(db, id_list)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))