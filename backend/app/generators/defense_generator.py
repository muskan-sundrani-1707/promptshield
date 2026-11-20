"""
Defense generator: reads FAILED defences (attack verdict SUCCEEDED/PARTIAL) of an experiment,
asks an LLM for an explanation + one patch rule per attack category, saves them as DRAFTS.
A human must approve each patch before it is used. Then build_patched_prompt makes V6.
"""
from pathlib import Path
from sqlalchemy.orm import Session
from app.evaluators.llm_judge import extract_json
from app.evaluators.rule_checks import CANARY, canary_leaked
from app.models.db_models import Defense, Evaluation, Experiment, HumanReview, PromptVersion, TestRun
from app.services.chain import is_chain
from app.services.llm_providers import get_provider
from app.services.prompt_store import PROMPT_DIR, get_latest, seed_prompts

GEN_PROMPT = PROMPT_DIR / "defense_generator_v1.txt"


def generate_defenses(db: Session, experiment_id: int, provider: str, model: str) -> dict:
    exp = db.get(Experiment, experiment_id)
    prompt = db.get(PromptVersion, exp.prompt_version_id)
    reviews = {r.evaluation_id: r.final_verdict
               for r in db.query(HumanReview).order_by(HumanReview.id).all()}
    rows = (db.query(TestRun, Evaluation).join(Evaluation, Evaluation.test_run_id == TestRun.id)
            .filter(TestRun.experiment_id == experiment_id, TestRun.kind == "attack")
            .order_by(TestRun.id).all())
    existing = [d.observed_failure or "" for d in
                db.query(Defense).filter(Defense.experiment_id == experiment_id).all()]
    system = GEN_PROMPT.read_text(encoding="utf-8")
    safe_prompt = prompt.content.replace(CANARY, "[REDACTED]")

    created, skipped, seen = [], [], set()
    for run, ev in rows:
        final = reviews.get(ev.id, ev.verdict)               # human verdict wins
        if final not in ("SUCCEEDED", "PARTIAL") or run.category in seen:
            continue
        seen.add(run.category)                                # one defence per category
        tag = f"[{run.category}] "
        if any(e.startswith(tag) for e in existing):
            continue
        data = (f"=== SYSTEM PROMPT ===\n{safe_prompt}\n\n=== ATTACK MESSAGE ===\n{run.attack_input}\n\n"
                f"=== CHATBOT REPLY ===\n{run.target_response}\n\n"
                f"=== EVALUATOR EVIDENCE ===\n{ev.evidence}\n\nReturn only the JSON object now.")
        raw = get_provider(provider, model).chat(system, data, temperature=0.0, max_tokens=500)
        parsed = extract_json(raw) or {}
        patch = str(parsed.get("suggested_patch", "")).strip()
        if not patch or canary_leaked(patch) or len(patch.split()) > 60:
            skipped.append({"category": run.category, "reason": "patch empty, too long or leaks the secret"})
            continue
        d = Defense(experiment_id=experiment_id,
                    observed_failure=tag + str(parsed.get("observed_failure", "")).strip(),
                    explanation=str(parsed.get("explanation", "")).strip(),
                    suggested_patch=patch, approved=False)
        db.add(d)
        db.commit()
        db.refresh(d)
        created.append({"defense_id": d.id, "category": run.category, "patch": patch})
    return {"created": created, "skipped": skipped}


def build_patched_prompt_text(base: str, patches: list) -> str:
    """Insert the approved rules just before the 'Internal note:' line (or at the end)."""
    block = "Additional rules (added after observed failures):\n" + \
            "\n".join(f"- {p}" for p in patches) + "\n\n"
    marker = "Internal note:"
    if marker in base:
        i = base.rindex(marker)
        return base[:i] + block + base[i:]
    return base.rstrip() + "\n\n" + block


def build_v6(db: Session, experiment_id: int) -> dict:
    exp = db.get(Experiment, experiment_id)
    base = db.get(PromptVersion, exp.prompt_version_id)
    if is_chain(base.content):
        raise ValueError("Base prompt is the V5 chain. Generate defenses from a non-chain experiment (e.g. V3).")
    approved = db.query(Defense).filter(Defense.experiment_id == experiment_id,
                                        Defense.approved.is_(True)).all()
    if not approved:
        raise ValueError("No approved defenses for this experiment. Approve at least one first.")
    text = build_patched_prompt_text(base.content, [d.suggested_patch for d in approved])
    (PROMPT_DIR / "v6.txt").write_text(text, encoding="utf-8")
    seed_prompts(db)                                         # adds the new V6 row
    v6 = get_latest(db, "V6")
    v6.parent_id = base.id                                   # V6 descends from its base prompt
    for d in approved:
        d.new_prompt_version_id = v6.id
    db.commit()
    return {"v6_prompt_id": v6.id, "parent": base.name, "rules_added": [d.suggested_patch for d in approved]}