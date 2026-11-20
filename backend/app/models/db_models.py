from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from app.database.connection import Base


class PromptVersion(Base):
    """Every version of a system prompt (V0..V7) with the technique used."""
    __tablename__ = "prompt_versions"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)          # e.g. "V0", "V1"
    content = Column(Text, nullable=False)         # the full prompt text
    technique = Column(String)                     # e.g. "few-shot"
    parent_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Experiment(Base):
    """One full run of the fixed dataset against one prompt version."""
    __tablename__ = "experiments"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"))
    target_provider = Column(String)
    target_model = Column(String)
    temperature = Column(Float, default=0.0)
    evaluator_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class TestRun(Base):
    """One attack/legit input sent to the target AI and its ACTUAL response."""
    __tablename__ = "test_runs"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    test_id = Column(String, nullable=False)       # e.g. "ATK-001"
    kind = Column(String, nullable=False)          # "attack" or "legit"
    category = Column(String)                      # ground-truth category
    attack_input = Column(Text)
    expected_behavior = Column(Text)
    target_response = Column(Text)
    run_index = Column(Integer, default=0)         # repeat number (LLMs vary)
    created_at = Column(DateTime, default=datetime.utcnow)


class Evaluation(Base):
    """PromptShield Evaluator's judgement of one TestRun."""
    __tablename__ = "evaluations"
    id = Column(Integer, primary_key=True)
    test_run_id = Column(Integer, ForeignKey("test_runs.id"))
    predicted_category = Column(String)
    verdict = Column(String)                       # SUCCEEDED / PARTIAL / FAILED
    evidence = Column(Text)
    risk = Column(String)                          # LOW / MEDIUM / HIGH / CRITICAL
    confidence = Column(Float)
    rule_flag = Column(Boolean, default=False)     # canary leak found by rules
    needs_review = Column(Boolean, default=False)  # ask a human


class HumanReview(Base):
    """A human override of an evaluation (used to measure judge accuracy)."""
    __tablename__ = "human_reviews"
    id = Column(Integer, primary_key=True)
    evaluation_id = Column(Integer, ForeignKey("evaluations.id"))
    final_verdict = Column(String)
    notes = Column(Text)
    reviewed_at = Column(DateTime, default=datetime.utcnow)


class Defense(Base):
    """A suggested prompt patch generated from an observed failure."""
    __tablename__ = "defenses"
    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiments.id"))
    observed_failure = Column(Text)
    explanation = Column(Text)
    suggested_patch = Column(Text)
    new_prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id"), nullable=True)
    approved = Column(Boolean, default=False)