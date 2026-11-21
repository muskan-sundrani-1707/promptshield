import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api";

// Final, human-reviewed experiment ids from our runs
const PRESETS = {
  "Main dataset (V0, V3, V6, V7)": "23,24,29,36",
  "Held-out dataset (V0, V3, V6, V7)": "30,31,32,37",
};

export default function Evaluation() {
  const [ids, setIds] = useState(PRESETS["Main dataset (V0, V3, V6, V7)"]);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(value = ids) {
    setBusy(true); setError("");
    try { setData(await api.compare(value.replace(/\s/g, ""))); }
    catch (e) { setError(e.message); setData(null); }
    setBusy(false);
  }

  useEffect(() => { load(); }, []);

  const rows = data ? data.table.map((r) => ({
    name: r.prompt,
    "Attack success (lower is better)": r.asr,
    "Resistance": r.resistance,
    "Legit success": r.legit_success,
    "Robustness": r.robustness,
  })) : [];

  return (
    <>
      <h1>Evaluation Dashboard</h1>
      <div className="card">
        <label>Experiment ids (comma separated)</label>
        <input value={ids} onChange={(e) => setIds(e.target.value)} />
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={() => load()} disabled={busy}>{busy ? "Loading..." : "Compare"}</button>
          {Object.entries(PRESETS).map(([label, v]) => (
            <button key={label} onClick={() => { setIds(v); load(v); }} disabled={busy}>{label}</button>
          ))}
        </div>
      </div>

      {error && <div className="notice err">{error}</div>}

      {data && (
        <>
          <div className="card" style={{ marginTop: 16 }}>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={rows}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2940" />
                <XAxis dataKey="name" stroke="#8b97b3" />
                <YAxis domain={[0, 100]} stroke="#8b97b3" unit="%" />
                <Tooltip cursor={{ fill: "rgba(255,255,255,0.05)" }}
  contentStyle={{ background: "#121829", border: "1px solid #1f2940" }} />
                <Legend />
                <Bar dataKey="Attack success (lower is better)" fill="#ef4444" />
                <Bar dataKey="Resistance" fill="#22c55e" />
                <Bar dataKey="Legit success" fill="#3b82f6" />
                <Bar dataKey="Robustness" fill="#8b97b3" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="card" style={{ marginTop: 16, overflowX: "auto" }}>
            <table>
              <thead>
                <tr><th>Prompt</th><th>Exp</th><th>Attacks</th><th>ASR %</th><th>Resist %</th>
                  <th>Cls acc %</th><th>Legit %</th><th>FPR %</th><th>Legit leaks</th>
                  <th>Robust</th><th>Status</th></tr>
              </thead>
              <tbody>
                {data.table.map((r) => (
                  <tr key={r.experiment_id}>
                    <td>{r.prompt}</td><td>{r.experiment_id}</td><td>{r.attack_tests}</td>
                    <td className="red">{r.asr}</td><td className="green">{r.resistance}</td>
                    <td>{r.classification_accuracy}</td><td>{r.legit_success}</td>
                    <td>{r.false_positive_rate}</td><td>{r.canary_leaks_legit}</td>
                    <td>{r.robustness}</td>
                    <td className={r.status === "final" ? "green" : "red"}>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="notice">
            {data.warnings.map((w, i) => <div key={i}>Warning: {w}</div>)}
            <div>Status "final" means every flagged case was human-reviewed. "provisional" numbers are judge opinions only.</div>
          </div>
        </>
      )}
    </>
  );
}