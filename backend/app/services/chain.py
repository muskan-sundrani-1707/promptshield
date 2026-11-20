"""
Prompt chaining (V5): GUARD -> ANSWER -> OUTPUT CHECK, three separate LLM calls.
All three stage prompts live in ONE file (v5.txt), split by marker lines.
There is deliberately NO code-level canary filter here: that would be test-specific
and would make the results look better than a real defence is.
"""
from app.services.llm_providers import get_provider

GUARD, ANSWER, CHECK = "=== GUARD ===", "=== ANSWER ===", "=== OUTPUT CHECK ==="
REFUSAL = ("I'm sorry, I can't help with that request. I can help with questions about "
           "admissions, fees, exams, timetables and campus services.")


def is_chain(content: str) -> bool:
    return all(m in content for m in (GUARD, ANSWER, CHECK))


def split_stages(content: str) -> dict:
    parts, current = {}, None
    for line in content.splitlines():
        if line.strip() in (GUARD, ANSWER, CHECK):
            current = line.strip()
            parts[current] = []
        elif current:
            parts[current].append(line)
    return {k: "\n".join(v).strip() for k, v in parts.items()}


def ask_chain(content: str, user_message: str, provider: str, model: str,
              temperature: float = 0.0) -> str:
    stages = split_stages(content)
    llm = get_provider(provider, model)

    # Stage 1: guard looks at the student message only. Only an explicit UNSAFE blocks.
    verdict = llm.chat(stages[GUARD], user_message, temperature=0.0, max_tokens=20)
    if "UNSAFE" in verdict.upper():
        return REFUSAL

    # Stage 2: normal answer using the answer prompt (it holds the canary).
    reply = llm.chat(stages[ANSWER], user_message, temperature=temperature, max_tokens=500)

    # Stage 3: output checker reads message + draft reply. Only an explicit BLOCK blocks.
    check_input = f"STUDENT MESSAGE:\n{user_message}\n\nDRAFT REPLY:\n{reply}"
    check = llm.chat(stages[CHECK], check_input, temperature=0.0, max_tokens=20)
    if "BLOCK" in check.upper():
        return REFUSAL
    return reply