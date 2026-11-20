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
  testConnection: (cfg) =>
    request("/api/target/test-connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(cfg),
    }),
};