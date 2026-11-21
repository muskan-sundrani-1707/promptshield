import { useEffect, useState } from "react";
import { api } from "../api";

export default function RedTeam() {
  const [prompts, setPrompts] = useState([]);
  const [cases, setCases] = useState([]);
  const [prompt, setPrompt] = useState("V3");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.prompts().then((p) => {
      const names = [...new Set(p.map((x) => x.name))];
      setPrompts(names);
    }).catch((e) => setError(e.message));
    api.attackCases().then(setCases).catch(() => {});
  }, []);

  async function run() {
    setBusy(true); setError(""); setResult(null);
    try { setResult(await api.redteam({ prompt_name: prompt, user_message: message })); }
    catch (e) { setError(e.message); }
    setBusy(false);
  }

  return (
    <>
      <h1>Red-Team Testing</h1>
      <div className="card" style={{ maxWidth: 760 }}>
        <label>Prompt version under test</label>
        <select value={prompt} onChange={(e) => setPrompt(e.target.value)}>
          {prompts.map((p) => <option key={p}>{p}</option>)}
        </select>

        <label>Load a predefined attack (optional)</label>
        <select defaultValue="" onChange={(e) => setMessage(e.target.value)}>
          <option value="">-- choose --</option>
          {cases.map((c) => (
            <option key={c.test_id} value={c.attack_input}>
              {c.test_id} [{c.category}]
            </option>
          ))}
        </select>

        <label>Attack message (or write your own)</label>
        <textarea rows={4} value={message} onChange={(e) => setMessage(e.target.value)} />

        <button onClick={run} disabled={busy || !message.trim()}>
          {busy ? "Running..." : "Send attack"}
        </button>
      </div>

      {error && <div className="notice err">{error}</div>}

      {result && (
        <div className="card" style={{ marginTop: 16, maxWidth: 760 }}>
          <div className="label">Target AI response ({result.prompt})</div>
          <p style={{ whiteSpace: "pre-wrap" }}>{result.response}</p>
          <div className={`notice ${result.canary_leaked ? "err" : "ok"}`}>
            {result.canary_leaked
              ? "Secret canary found in the reply: proven leak."
              : "No canary found. This does NOT prove the attack failed. Read the reply yourself."}
          </div>
        </div>
      )}
    </>
  );
}