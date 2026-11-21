import { useEffect, useState } from "react";
import { api } from "../api";

const BASE = "http://127.0.0.1:8000";

export default function History() {
  const [rows, setRows] = useState([]);
  const [onlyFinal, setOnlyFinal] = useState(true);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [manual, setManual] = useState([]);

  useEffect(() => {
    setLoading(true);
    api.history(onlyFinal)
      .then((r) => { setRows(r); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [onlyFinal]);

  useEffect(() => {
    api.manualTests().then(setManual).catch(() => {});
  }, []);

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

      <h2 style={{ marginTop: 28 }}>Manual tests (Red-Team playground)</h2>
      <div className="notice">
        Single attacks typed by hand. These are NOT scored and are not part of any
        experiment, so they never affect ASR or the other metrics above.
      </div>
      <div className="card" style={{ marginTop: 12, overflowX: "auto" }}>
        <table>
          <thead>
            <tr><th>ID</th><th>Time</th><th>Prompt</th><th>Attack</th>
              <th>Reply</th><th>Canary</th></tr>
          </thead>
          <tbody>
            {manual.map((m) => (
              <tr key={m.id}>
                <td>{m.id}</td>
                <td>{new Date(m.created_at + "Z").toLocaleString()}</td>
                <td>{m.prompt}</td>
                <td>{m.message.slice(0, 120)}</td>
                <td>{m.response.slice(0, 160)}</td>
                <td className={m.canary_leaked ? "red" : "green"}>
                  {m.canary_leaked ? "LEAKED" : "none"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {manual.length === 0 && <p>No manual tests yet.</p>}
      </div>
    </>
  );
}