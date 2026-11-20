"""Loads the fixed test datasets from backend/datasets/ and validates them."""
import json
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[2] / "datasets"

ATTACK_FIELDS = {"test_id", "category", "attack_input", "expected_secure_behavior"}
LEGIT_FIELDS = {"test_id", "category", "user_input", "expected_behavior"}

ATTACK_CATEGORIES = [
    "Instruction Override", "Prompt Injection", "Role Manipulation",
    "Information Extraction", "Policy Bypass", "Context Manipulation",
]


def _load(filename: str, required: set) -> list:
    path = DATASET_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    for case in cases:
        missing = required - set(case)
        if missing:
            raise ValueError(f"{filename}: case {case.get('test_id')} is missing {missing}")
    return cases


def load_attack_cases(categories=None) -> list:
    cases = _load("attack_cases.json", ATTACK_FIELDS)
    if categories:
        cases = [c for c in cases if c["category"] in categories]
    return cases


def load_legit_cases() -> list:
    return _load("legitimate_cases.json", LEGIT_FIELDS)