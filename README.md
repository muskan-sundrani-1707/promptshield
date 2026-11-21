# PromptShield

Automated red-team framework for testing and hardening LLM system prompts.
Course: Prompt Engineering (SCSE4041), Problem C23: Prompt Safety Tester / Red Team Kit.

Cycle: ATTACK -> ANALYZE -> DETECT -> HARDEN -> RETEST -> COMPARE

**Research question:** Can iterative prompt hardening reduce adversarial attack success
while keeping the target AI able to answer legitimate requests?

## Two AI roles

| Role | What it does | Files |
|---|---|---|
| Target AI | The chatbot under test (University Helpdesk). Sees only a system prompt and a user message. | `services/target_ai.py`, `prompts/*.txt` |
| PromptShield Evaluator | Judges the target's real replies. Never shares a conversation with the target. | `evaluators/` |

The evaluator has three layers so no single judge is trusted blindly:
1. **Rule check:** a fake canary string (`CANARY-7F3A`) in the target prompt. If it appears in a reply, the leak is proven.
2. **LLM judge:** classifies category, verdict (SUCCEEDED / PARTIAL / FAILED), risk, confidence.
3. **Human review:** low-confidence or disputed cases are flagged; the human verdict is stored separately and wins.

## Prompt versions

| Version | Technique | Notes |
|---|---|---|
| V0 | Baseline | Plain helpdesk prompt |
| V1, V2 | Role + rules, attack taxonomy | Cumulative |
| V3 | Few-shot examples | Examples are not copies of test cases |
| V4 | Structured JSON output | |
| V5 | Prompt chain (guard, answer, output check) | 3 LLM calls per message |
| V6 | Defence generation | Patches generated from failures, human-approved |
| V7 | Final prompt | V6 + one general rule |

## Datasets (fixed, in `backend/datasets/`)

| File | Purpose |
|---|---|
| `attack_cases.json` | 18 attacks (6 categories x 3), used to build defences |
| `legitimate_cases.json` | 10 normal helpdesk questions |
| `attack_cases_heldout.json` | 12 attacks never used to write defences |
| `attack_cases_fresh.json` | 8 attacks written after seeing results |

## Results (llama3.2, temperature 0, one run, human-reviewed)

Main dataset (18 attacks + 10 legit):

| Version | ASR | Resistance | Legit success | Legit canary leaks | Robustness |
|---|---|---|---|---|---|
| V0 | 66.7% | 27.8% | 100% | 10/10 | 43.5 |
| V3 | 16.7% | 72.2% | 100% | 0 | 83.9 |
| V4 | 27.8% | 66.7% | 100% | 0 | 80.0 |
| V5 | 11.1% | 88.9% | 60% | 0 | 71.6 |
| V6 | 16.7% | 77.8% | 100% | 0 | 87.5 |
| V7 | 11.1% | 88.9% | 100% | 0 | 94.1 |

Held-out dataset (12 attacks + 10 legit):

| Version | ASR | Resistance | Legit success | Legit canary leaks | Robustness |
|---|---|---|---|---|---|
| V0 | 50.0% | 33.3% | 100% | 10/10 | 50.0 |
| V3 | 16.7% | 75.0% | 100% | 0 | 85.7 |
| V6 | 8.3% | 83.3% | 100% | 0 | 90.9 |
| V7 | 8.3% | 91.7% | 100% | 0 | 95.7 |

### What the evidence supports
- Few-shot + rules + taxonomy (V0 to V3) cut ASR a lot on two separate datasets.
- V4 (JSON output) gave no benefit; V5 (guard chain) over-refused normal questions (40% false positives).
- V6 and V7 versus V3 differ by 1 to 2 attacks. This is within noise; no superiority is claimed.
- System-prompt extraction (ATK-010, ATK-012) still leaked in V6/V7 despite a dedicated rule.

## Limitations
- One 3B model is both target and judge; one run, temperature 0.
- Small datasets: one attack equals 5.6% (main) or 8.3% (held-out).
- The LLM judge undercounted attacks (judge-human agreement 58% to 90%). Flagged cases were human-reviewed; some unflagged cases were not.
- V6 patches came from the main dataset; V7's extra rule was inspired by a held-out case, so those sets are not fully independent for V7.
- The canary rule only catches the exact string (a partial leak like `CANR` is missed).
- The robustness score does not penalise secrets leaked inside legitimate answers; read the canary-leak column.
- All tests use harmless fake data against a local model only. No real credentials or external systems.

## Setup (macOS)

```bash
brew install python node git ollama
git clone <your-repo-url> promptshield && cd promptshield

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # defaults use Ollama, no API key needed

ollama serve                  # keep running (separate tab)
ollama pull llama3.2
```

API keys (only for paid providers) go in `.env`, never in code or the browser.

## Run

Terminal 1 (backend):
```bash
cd backend && source ../venv/bin/activate
uvicorn app.main:app --reload
```

Terminal 2 (frontend):
```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. API docs: http://127.0.0.1:8000/docs

## Reproduce the experiments

Run one command at a time, with the server and Ollama on, and nothing else hitting the server.

```bash
cd backend
../venv/bin/python evaluation/run_all.py V0 V3 V6 --repeats 1
../venv/bin/python evaluation/run_all.py V0 V3 V6 V7 --repeats 1 --dataset heldout
```

Then review flagged cases (`GET /api/evaluations/review-queue?experiment_id=N`, verdicts via
`POST /api/evaluations/{id}/review`). Metrics are `final` only when no flagged case is pending.

## Structure

```
backend/app/   main.py, routes/, services/, evaluators/, generators/, models/, database/
backend/prompts/    all prompt versions + evaluator and defence-generator prompts
backend/datasets/   fixed test sets
backend/evaluation/ run_all.py
frontend/src/       api.js, App.jsx, pages/
docs/
```