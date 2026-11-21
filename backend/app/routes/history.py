"""Experiment history + export. All numbers come from the metrics engine (real DB data)."""
import csv
import io
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.models.db_models import Experiment, TestRun, Evaluation, HumanReview
from app.services import metrics

router = APIRouter(prefix="/api", tags=["history"])


def _summary(db: Session, exp: Experiment) -> dict:
    m = metrics.compute_metrics(db, exp.id)
    return {
        "experiment_id": exp.id, "name": exp.name, "prompt": m["prompt_version"],
        "model": m["model"], "temperature": exp.temperature,
        "created_at": exp.created_at.isoformat(),
        "dataset": exp.name.split("-")[2] if exp.name.count("-") >= 4 else "main",
        "attack_tests": m["attack"]["total"], "legit_tests": m["legit"]["total"],
        "asr": m["attack"]["asr"], "asr_lenient": m["attack"]["asr_lenient"],
        "resistance": m["attack"]["resistance_rate"],
        "legit_success": m["legit"]["success_rate"],
        "false_positive_rate": m["legit"]["false_positive_rate"],
        "legit_canary_leaks": m["legit"]["canary_leaks"],
        "robustness": m["robustness"], "status": m["coverage"]["status"],
        "runs_saved": m["coverage"]["runs_saved"],
        "pending_review": m["coverage"]["pending_human_review"],
    }


@router.get("/history")
def history(only_final: bool = False, db: Session = Depends(get_db)):
    rows = [_summary(db, e) for e in db.query(Experiment).order_by(Experiment.id.desc()).all()]
    # an experiment with no evaluated runs is not a result
    rows = [r for r in rows if r["runs_saved"] > 0]
    if only_final:
        rows = [r for r in rows if r["status"] == "final" and r["attack_tests"] + r["legit_tests"] > 0]
    return rows


@router.get("/history/stats")
def history_stats(db: Session = Depends(get_db)):
    """Dashboard numbers computed from FINAL experiments only (human-reviewed)."""
    final = [r for r in history(only_final=True, db=db)]
    attacks = sum(r["attack_tests"] for r in final)
    succeeded = sum(round(r["asr"] / 100 * r["attack_tests"]) for r in final if r["asr"] is not None)
    resisted = sum(round(r["resistance"] / 100 * r["attack_tests"])
                   for r in final if r["resistance"] is not None)
    return {"final_experiments": len(final), "attack_tests": attacks,
            "attacks_succeeded": succeeded, "attacks_resisted": resisted,
            "human_reviews": db.query(HumanReview).count()}


@router.get("/experiments/{experiment_id}/export")
def export_experiment(experiment_id: int, format: str = "json", db: Session = Depends(get_db)):
    """Download every test run + judge verdict + human verdict of one experiment."""
    exp = db.get(Experiment, experiment_id)
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found.")
    if format not in ("json", "csv"):
        raise HTTPException(status_code=400, detail="format must be json or csv")

    reviews = {r.evaluation_id: r for r in db.query(HumanReview).order_by(HumanReview.id).all()}
    rows = (db.query(TestRun, Evaluation)
            .outerjoin(Evaluation, Evaluation.test_run_id == TestRun.id)
            .filter(TestRun.experiment_id == experiment_id).order_by(TestRun.id).all())
    data = []
    for run, ev in rows:
        rev = reviews.get(ev.id) if ev else None
        data.append({
            "experiment_id": experiment_id, "test_id": run.test_id, "kind": run.kind,
            "true_category": run.category, "input": run.attack_input,
            "expected": run.expected_behavior, "response": run.target_response,
            "predicted_category": ev.predicted_category if ev else None,
            "judge_verdict": ev.verdict if ev else None,
            "human_verdict": rev.final_verdict if rev else None,
            "final_verdict": (rev.final_verdict if rev else (ev.verdict if ev else None)),
            "risk": ev.risk if ev else None, "confidence": ev.confidence if ev else None,
            "rule_flag": ev.rule_flag if ev else None,
            "evidence": ev.evidence if ev else None,
            "human_notes": rev.notes if rev else None,
        })

    if format == "json":
        body = json.dumps({"experiment": _summary(db, exp), "runs": data}, indent=2, ensure_ascii=False)
        media = "application/json"
    else:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(data[0].keys()) if data else ["empty"])
        writer.writeheader()
        writer.writerows(data)
        body, media = buf.getvalue(), "text/csv"

    return Response(content=body, media_type=media, headers={
        "Content-Disposition": f'attachment; filename="experiment_{experiment_id}.{format}"'})

from app.models.db_models import Defense


@router.get("/vulnerabilities")
def vulnerabilities(experiment_id: int = None, db: Session = Depends(get_db)):
    """Every attack that SUCCEEDED or PARTIALLY succeeded (final verdict = human if reviewed)."""
    reviews = {r.evaluation_id: r for r in db.query(HumanReview).order_by(HumanReview.id).all()}
    q = (db.query(TestRun, Evaluation, Experiment)
         .join(Evaluation, Evaluation.test_run_id == TestRun.id)
         .join(Experiment, Experiment.id == TestRun.experiment_id)
         .filter(TestRun.kind == "attack"))
    if experiment_id:
        q = q.filter(TestRun.experiment_id == experiment_id)
    out = []
    for run, ev, exp in q.order_by(TestRun.experiment_id.desc(), TestRun.id).all():
        rev = reviews.get(ev.id)
        final = rev.final_verdict if rev else ev.verdict
        if final not in ("SUCCEEDED", "PARTIAL"):
            continue
        out.append({
            "experiment_id": exp.id, "experiment": exp.name, "test_id": run.test_id,
            "category": run.category, "predicted_category": ev.predicted_category,
            "input": run.attack_input, "response": run.target_response,
            "judge_verdict": ev.verdict, "human_verdict": rev.final_verdict if rev else None,
            "final_verdict": final, "risk": ev.risk, "evidence": ev.evidence,
            "human_notes": rev.notes if rev else None, "reviewed": rev is not None,
        })
    return out


@router.get("/defenses/all")
def all_defenses(db: Session = Depends(get_db)):
    return [{"id": d.id, "experiment_id": d.experiment_id, "observed_failure": d.observed_failure,
             "explanation": d.explanation, "patch": d.suggested_patch, "approved": d.approved}
            for d in db.query(Defense).order_by(Defense.id.desc()).all()]

import difflib


@router.get("/prompts/diff")
def prompt_diff(base: int, new: int, db: Session = Depends(get_db)):
    """Line-by-line diff between two stored prompt rows (by id)."""
    from app.models.db_models import PromptVersion
    a, b = db.get(PromptVersion, base), db.get(PromptVersion, new)
    if a is None or b is None:
        raise HTTPException(status_code=404, detail="Prompt id not found.")
    lines = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
            None, a.content.splitlines(), b.content.splitlines()).get_opcodes():
        if tag == "equal":
            lines += [{"type": "same", "text": t} for t in a.content.splitlines()[i1:i2]]
        else:
            lines += [{"type": "removed", "text": t} for t in a.content.splitlines()[i1:i2]]
            lines += [{"type": "added", "text": t} for t in b.content.splitlines()[j1:j2]]
    return {"base": {"id": a.id, "name": a.name, "technique": a.technique},
            "new": {"id": b.id, "name": b.name, "technique": b.technique}, "lines": lines}