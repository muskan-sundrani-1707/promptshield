"""
Run the fixed dataset on several prompt versions, judge every run, and print a comparison.
Usage (from the backend/ folder, with the server running):
    ../venv/bin/python evaluation/run_all.py V0 V1 V2 V3 --repeats 1
    ../venv/bin/python evaluation/run_all.py V0 V3 --repeats 3 --dataset heldout
"""
import argparse
import sys
import httpx

BASE = "http://127.0.0.1:8000"


def call(method, path, **kwargs):
    r = httpx.request(method, BASE + path, timeout=None, **kwargs)
    if r.status_code != 200:
        print(f"ERROR {r.status_code} on {path}: {r.text[:300]}")
        sys.exit(1)
    return r.json()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("versions", nargs="+", help="e.g. V0 V1 V2 V3")
    p.add_argument("--provider", default="ollama")
    p.add_argument("--model", default="llama3.2")
    p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--limit", type=int, default=None, help="only first N per kind (quick test)")
    p.add_argument("--dataset", default="main", choices=["main", "heldout","fresh"])
    args = p.parse_args()

    print("Seeding prompts:", call("POST", "/api/prompts/seed"))

    ids = []
    for version in args.versions:
        body = {"provider": args.provider, "model": args.model, "prompt_name": version,
                "repeats": args.repeats, "temperature": 0.0, "dataset": args.dataset}
        if args.limit:
            body["limit"] = args.limit
        run = call("POST", "/api/experiments/run", json=body)
        print(f"{version}: saved {run['saved']}/{run['planned']} errors={len(run['errors'])}")
        if run["stopped_early"] or run["saved"] < run["planned"]:
            print(f"  {version} is INCOMPLETE. Fix the cause and rerun it. Not comparing.")
            sys.exit(1)

        # evaluate (resumes automatically if called again)
        for _ in range(5):
            ev = call("POST", f"/api/experiments/{run['experiment_id']}/evaluate", json={})
            print(f"  judged {ev['evaluated']}, remaining {ev['remaining']}, "
                  f"needs_review {ev['needs_review']}")
            if ev["remaining"] == 0:
                break
        ids.append(run["experiment_id"])

    if len(ids) >= 2:
        result = call("GET", "/api/metrics/compare", params={"ids": ",".join(map(str, ids))})
        print("\nVersion  ASR   Resist  ClsAcc  LegitOK  FPR   Robust  Status")
        for r in result["table"]:
            print(f"{r['prompt']:<8} {r['asr']}  {r['resistance']}  {r['classification_accuracy']}  "
                  f"{r['legit_success']}  {r['false_positive_rate']}  {r['robustness']}  {r['status']}")
        print("\nWarnings:")
        for w in result["warnings"]:
            print(" -", w)
    print("\nExperiment ids:", ids)


if __name__ == "__main__":
    main()