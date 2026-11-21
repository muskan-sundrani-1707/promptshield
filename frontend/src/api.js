
const BASE = "http://127.0.0.1:8000";

async function request(path, options) {
  const res = await fetch(BASE + path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
  return data;
}

export const api = {
  health: () => request("/api/health"),
  summary: () => request("/api/dashboard/summary"),
  experiments: () => request("/api/experiments"),
  compare: (ids) => request(`/api/metrics/compare?ids=${ids}`),
  testConnection: (cfg) =>
    request("/api/target/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    }),
  history: (onlyFinal) => request(`/api/history?only_final=${onlyFinal}`),
  historyStats: () => request("/api/history/stats"),
  prompts: () => request("/api/prompts"),
  attackCases: () => request("/api/datasets/attacks"),
  manualTests: () => request("/api/target/manual-tests"),
  redteam: (body) =>
    request("/api/target/redteam", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  vulnerabilities: (expId) => request(`/api/vulnerabilities${expId ? `?experiment_id=${expId}` : ""}`),
  allDefenses: () => request("/api/defenses/all"),
  promptDiff: (base, nw) => request(`/api/prompts/diff?base=${base}&new=${nw}`),
  approveDefense: (id, approved) =>
    request(`/api/defenses/${id}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ approved }),
    }),
};
