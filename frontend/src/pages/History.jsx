import { useEffect, useState } from "react";
import { api } from "../api";

const BASE = "http://127.0.0.1:8000";

export default function History() {
  const [rows, setRows] = useState([]);
  const [onlyFinal, setOnlyFinal] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.history(onlyFinal)
      .then((r) => { setRows(r); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [onlyFinal]);

  return (
    <>
      <h1>Experiment History</h1>
      <div className="card">
        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="checkbox" style={{ width: "auto" }} checked={onlyFinal}
            onChange={(e) => setOnlyFinal(e.target.checked)} />
          Show only final (human-reviewed) experiments
        </label>
        <div className="notice">
          Provisional experiments contain judge opinions that were not human-verified.
          Do not quote their numbers as results.
        </div>
      </div>

      {error && <div className="notice err">{error}</div>}
      {loading && <p>Loading...</p>}

      {!loading && (
        <div className="card" style={{ marginTop: 16, overflowX: "auto" }}>
          <table>
            <thead>
              <tr><th>ID</th><th>Prompt</th><th>Dataset</th><th>Model</th><th>Attacks</th>
                <th>ASR %</th><th>Resist %</th><th>Legit %</th><th>Legit leaks</th>
                <th>Robust</th><th>Status</th><th>Export</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.experiment_id}>
                  <td>{r.experiment_id}</td><td>{r.prompt}</td><td>{r.dataset}</td>
                  <td>{r.model}</td><td>{r.attack_tests}</td>
                  <td className="red">{r.asr ?? "-"}</td>
                  <td className="green">{r.resistance ?? "-"}</td>
                  <td>{r.legit_success ?? "-"}</td><td>{r.legit_canary_leaks}</td>
                  <td>{r.robustness ?? "-"}</td>
                  <td className={r.status === "final" ? "green" : "red"}>
                    {r.status}{r.pending_review ? ` (${r.pending_review} to review)` : ""}
                  </td>
                  <td>
                    <a href={`${BASE}/api/experiments/${r.experiment_id}/export?format=csv`}>CSV</a>{" "}
                    <a href={`${BASE}/api/experiments/${r.experiment_id}/export?format=json`}>JSON</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {rows.length === 0 && <p>No experiments to show.</p>}
        </div>
      )}
    </>
  );
}