import { useEffect, useState } from "react";
import { api } from "../api";

export default function Dashboard() {
  const [s, setS] = useState(null);
  const [exps, setExps] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
        Promise.all([api.summary(), api.experiments(), api.historyStats()])
      .then(([summary, list, stats]) => { setS({ ...summary, ...stats }); setExps(list.slice(0, 8)); })
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="notice err">Cannot reach backend: {error}. Is uvicorn running?</div>;
  if (!s) return <p>Loading...</p>;

    const cards = [
    ["Final experiments", s.final_experiments, "blue"],
    ["Attack tests (final)", s.attack_tests, "blue"],
    ["Attacks succeeded (final)", s.attacks_succeeded, "red"],
    ["Attacks resisted (final)", s.attacks_resisted, "green"],
    ["Human reviews", s.human_reviews, "blue"],
    ["Prompt versions", s.prompt_versions, "blue"],
  ];

  return (
    <>
      <h1>Dashboard</h1>
      <div className="grid">
        {cards.map(([label, value, color]) => (
          <div className="card" key={label}>
            <div className="label">{label}</div>
            <div className={`value ${color}`}>{value}</div>
          </div>
        ))}
      </div>
      <h1 style={{ marginTop: 32 }}>Recent experiments</h1>
      <div className="card">
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Model</th><th>Created</th></tr></thead>
          <tbody>
            {exps.map((e) => (
              <tr key={e.id}><td>{e.id}</td><td>{e.name}</td><td>{e.model}</td>
                <td>{e.created_at.slice(0, 16).replace("T", " ")}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}