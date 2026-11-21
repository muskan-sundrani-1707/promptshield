import { useEffect, useState } from "react";
import { api } from "../api";

export default function Vulnerabilities() {
  const [rows, setRows] = useState([]);
  const [defenses, setDefenses] = useState([]);
  const [expId, setExpId] = useState("");
  const [onlyReviewed, setOnlyReviewed] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.vulnerabilities(expId).then(setRows).catch((e) => setError(e.message));
    api.allDefenses().then(setDefenses).catch(() => {});
  }, [expId]);

  const shown = rows.filter((r) => !onlyReviewed || r.reviewed);
  const byCat = {};
  shown.forEach((r) => { byCat[r.category] = (byCat[r.category] || 0) + 1; });

  return (
    <>
      <h1>Vulnerability Analysis</h1>
      <div className="card">
        <label>Experiment id (empty = all)</label>
        <input value={expId} onChange={(e) => setExpId(e.target.value.trim())} placeholder="e.g. 37" />
        <label style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <input type="checkbox" style={{ width: "auto" }} checked={onlyReviewed}
            onChange={(e) => setOnlyReviewed(e.target.checked)} />
          Only human-reviewed findings
        </label>
        <div className="notice">
          Judge-only findings may be wrong. Human-reviewed rows show both verdicts so
          you can see where the judge missed an attack.
        </div>
      </div>

      {error && <div className="notice err">{error}</div>}

      <div className="grid" style={{ marginTop: 16 }}>
        {Object.entries(byCat).map(([c, n]) => (
          <div className="card" key={c}>
            <div className="label">{c}</div>
            <div className="value red">{n}</div>
          </div>
        ))}
      </div>

      {shown.map((r, i) => (
        <div className="card" key={i} style={{ marginTop: 16 }}>
          <div>
            <b>{r.test_id}</b> ({r.category}) in experiment {r.experiment_id}{" "}
            <span className={r.final_verdict === "SUCCEEDED" ? "red" : ""}>[{r.final_verdict}]</span>
          </div>
          <div className="label" style={{ marginTop: 8 }}>
            Judge: {r.judge_verdict} | Human: {r.human_verdict ?? "not reviewed"} | Risk: {r.risk}
          </div>
          <div className="label" style={{ marginTop: 10 }}>Attack</div>
          <p style={{ whiteSpace: "pre-wrap", margin: "4px 0" }}>{r.input}</p>
          <div className="label">Target reply</div>
          <p style={{ whiteSpace: "pre-wrap", margin: "4px 0" }}>{r.response.slice(0, 500)}</p>
          {r.human_notes && <div className="notice">Reviewer note: {r.human_notes}</div>}
        </div>
      ))}
      {shown.length === 0 && <p>No findings.</p>}

      <h1 style={{ marginTop: 32 }}>Recommended defenses</h1>
      <div className="card" style={{ overflowX: "auto" }}>
        <table>
          <thead><tr><th>ID</th><th>Exp</th><th>Observed failure</th><th>Patch</th><th>Approved</th></tr></thead>
          <tbody>
            {defenses.map((d) => (
              <tr key={d.id}>
                <td>{d.id}</td><td>{d.experiment_id}</td>
                <td style={{ whiteSpace: "normal", minWidth: 220 }}>{d.observed_failure}</td>
                <td style={{ whiteSpace: "normal", minWidth: 260 }}>{d.patch}</td>
                <td className={d.approved ? "green" : "red"}>{d.approved ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}