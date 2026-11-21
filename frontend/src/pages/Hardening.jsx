import { useEffect, useState } from "react";
import { api } from "../api";

export default function Hardening() {
  const [prompts, setPrompts] = useState([]);
  const [defenses, setDefenses] = useState([]);
  const [base, setBase] = useState("");
  const [nw, setNw] = useState("");
  const [diff, setDiff] = useState(null);
  const [error, setError] = useState("");

  function loadDefenses() { api.allDefenses().then(setDefenses).catch(() => {}); }

  useEffect(() => {
    api.prompts().then((p) => {
      setPrompts(p);
      const last = (name) => [...p].reverse().find((x) => x.name === name);
      if (last("V3")) setBase(String(last("V3").id));
      if (last("V7")) setNw(String(last("V7").id));
    }).catch((e) => setError(e.message));
    loadDefenses();
  }, []);

  async function compare() {
    setError(""); setDiff(null);
    try { setDiff(await api.promptDiff(base, nw)); } catch (e) { setError(e.message); }
  }

  async function decide(id, approved) {
    try { await api.approveDefense(id, approved); loadDefenses(); }
    catch (e) { setError(e.message); }
  }

  const opt = (p) => <option key={p.id} value={p.id}>{p.name} (id {p.id}, {p.technique})</option>;

  return (
    <>
      <h1>Prompt Hardening</h1>
      <div className="card">
        <label>Original prompt</label>
        <select value={base} onChange={(e) => setBase(e.target.value)}>{prompts.map(opt)}</select>
        <label>Hardened prompt</label>
        <select value={nw} onChange={(e) => setNw(e.target.value)}>{prompts.map(opt)}</select>
        <button onClick={compare} disabled={!base || !nw}>Show changes</button>
        <div className="notice">
          Green lines were added, red lines were removed. A longer prompt is not automatically
          a better prompt: check the Evaluation page for measured results.
        </div>
      </div>

      {error && <div className="notice err">{error}</div>}

      {diff && (
        <div className="card" style={{ marginTop: 16 }}>
          <div className="label">{diff.base.name} to {diff.new.name}</div>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13, lineHeight: 1.6, margin: "10px 0 0" }}>
            {diff.lines.map((l, i) => (
              <div key={i} style={{
                background: l.type === "added" ? "rgba(34,197,94,.15)" :
                  l.type === "removed" ? "rgba(239,68,68,.15)" : "transparent",
                color: l.type === "added" ? "#86efac" : l.type === "removed" ? "#fca5a5" : "#b4c0da",
              }}>
                {l.type === "added" ? "+ " : l.type === "removed" ? "- " : "  "}{l.text}
              </div>
            ))}
          </pre>
        </div>
      )}

      <h1 style={{ marginTop: 32 }}>Proposed defenses</h1>
      <div className="card" style={{ overflowX: "auto" }}>
        <table>
          <thead><tr><th>ID</th><th>Exp</th><th>Observed failure</th><th>Patch</th><th>Approved</th><th>Action</th></tr></thead>
          <tbody>
            {defenses.map((d) => (
              <tr key={d.id}>
                <td>{d.id}</td><td>{d.experiment_id}</td>
                <td style={{ whiteSpace: "normal", minWidth: 200 }}>{d.observed_failure}</td>
                <td style={{ whiteSpace: "normal", minWidth: 260 }}>{d.patch}</td>
                <td className={d.approved ? "green" : "red"}>{d.approved ? "yes" : "no"}</td>
                <td>
                  <button style={{ margin: "0 6px 0 0", padding: "6px 12px" }} onClick={() => decide(d.id, true)}>Approve</button>
                  <button style={{ margin: 0, padding: "6px 12px", background: "#7f1d1d" }} onClick={() => decide(d.id, false)}>Reject</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}