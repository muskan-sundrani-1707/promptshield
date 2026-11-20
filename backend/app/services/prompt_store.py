"""Syncs prompt .txt files into the prompt_versions table."""
from pathlib import Path
from sqlalchemy.orm import Session
from app.models.db_models import PromptVersion

PROMPT_DIR = Path(__file__).resolve().parents[2] / "prompts"

# version name -> (file name, technique used)
PROMPT_FILES = {
    "V0": ("baseline.txt", "baseline"),
    "V1": ("v1.txt", "role-based + explicit rules"),
    "V2": ("v2.txt", "attack taxonomy + constraints"),
    "V3": ("v3.txt", "few-shot examples"),
    "V4": ("v4.txt", "structured JSON output"),
    "V5": ("v5.txt", "prompt chaining"),
    "V6": ("v6.txt", "defense generation"),
    "V7": ("final.txt", "final hardened prompt"),
}


def get_latest(db: Session, name: str):
    """Newest row for a version name (or None)."""
    return (db.query(PromptVersion).filter(PromptVersion.name == name)
            .order_by(PromptVersion.id.desc()).first())


def seed_prompts(db: Session) -> list:
    """Add any prompt file that is new or changed. Files that don't exist yet are skipped."""
    report = []
    for name, (filename, technique) in PROMPT_FILES.items():
        path = PROMPT_DIR / filename
        if not path.exists():
            continue
        content = path.read_text(encoding="utf-8").strip()
        latest = get_latest(db, name)
        if latest and latest.content == content:
            report.append({"name": name, "id": latest.id, "status": "unchanged"})
            continue
        row = PromptVersion(name=name, content=content, technique=technique,
                            parent_id=latest.id if latest else None)
        db.add(row)
        db.commit()
        db.refresh(row)
        report.append({"name": name, "id": row.id, "status": "added"})
    return report