"""
Test runner: sends every dataset case to the TARGET AI using one prompt version
and saves the ACTUAL responses. It does NOT judge anything (that is the Evaluator, Step 5).
"""
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.db_models import Experiment, TestRun
from app.services.dataset_loader import load_attack_cases, load_legit_cases
from app.services.llm_providers import LLMError
from app.services.prompt_store import get_latest
from app.services.target_ai import ask_target

MAX_CONSECUTIVE_ERRORS = 3   # stop early if the model keeps failing (e.g. Ollama is off)


def run_experiment(db: Session, prompt_name: str, provider: str, model: str,
                   temperature: float = 0.0, repeats: int = 1, categories=None,
                   include_attacks: bool = True, include_legit: bool = True,
                   limit=None) -> dict:
    prompt = get_latest(db, prompt_name)
    if prompt is None:
        raise ValueError(f"Prompt version '{prompt_name}' not found. Call /api/prompts/seed first.")

    # Build the list of cases to run: (kind, test_id, category, input, expected)
    cases = []
    if include_attacks:
        attacks = load_attack_cases(categories)
        if limit:
            attacks = attacks[:limit]
        cases += [("attack", c["test_id"], c["category"], c["attack_input"],
                   c["expected_secure_behavior"]) for c in attacks]
    if include_legit:
        legit = load_legit_cases()
        if limit:
            legit = legit[:limit]
        cases += [("legit", c["test_id"], c["category"], c["user_input"],
                   c["expected_behavior"]) for c in legit]
    if not cases:
        raise ValueError("No test cases selected.")

    experiment = Experiment(
        name=f"{prompt_name}-{model}-{datetime.now():%Y%m%d-%H%M%S}",
        prompt_version_id=prompt.id, target_provider=provider,
        target_model=model, temperature=temperature,
    )
    db.add(experiment)
    db.commit()
    db.refresh(experiment)

    saved, errors, consecutive = 0, [], 0
    stopped_early = False
    for run_index in range(repeats):
        for kind, test_id, category, user_input, expected in cases:
            try:
                reply = ask_target(prompt.content, user_input, provider, model, temperature)
                consecutive = 0
            except LLMError as e:
                errors.append({"test_id": test_id, "run_index": run_index, "error": str(e)})
                consecutive += 1
                if consecutive >= MAX_CONSECUTIVE_ERRORS:
                    stopped_early = True
                    break
                continue   # failed calls are NOT saved, so no fake data
            db.add(TestRun(experiment_id=experiment.id, test_id=test_id, kind=kind,
                           category=category, attack_input=user_input,
                           expected_behavior=expected, target_response=reply,
                           run_index=run_index))
            db.commit()
            saved += 1
        if stopped_early:
            break

    return {"experiment_id": experiment.id, "experiment_name": experiment.name,
            "prompt_version": prompt_name, "planned": len(cases) * repeats,
            "saved": saved, "errors": errors, "stopped_early": stopped_early}