import { useState } from "react";
import { api } from "../api";

export default function TargetConfig() {
  const [provider, setProvider] = useState("ollama");
  const [model, setModel] = useState("llama3.2");
  const [temperature, setTemperature] = useState(0);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);

  async function test() {
    setBusy(true); setResult(null);
    try {
      const r = await api.testConnection({ provider, model, temperature: Number(temperature) });
      setResult({ ok: true, text: `Connected. Reply: "${r.reply}" (${r.latency_ms} ms)` });
    } catch (e) {
      setResult({ ok: false, text: e.message });
    }
    setBusy(false);
  }

  return (
    <>
      <h1>Target AI Configuration</h1>
      <div className="card" style={{ maxWidth: 520 }}>
        <label>LLM provider</label>
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="ollama">Ollama (local, free)</option>
          <option value="anthropic">Anthropic</option>
          <option value="openai">OpenAI</option>
        </select>
        <label>Model</label>
        <input value={model} onChange={(e) => setModel(e.target.value)} />
        <label>Temperature</label>
        <input type="number" step="0.1" min="0" max="2" value={temperature}
          onChange={(e) => setTemperature(e.target.value)} />
        <div className="notice">
          API keys are never entered here. They are read by the backend from the
          <code> .env</code> file only, so they cannot leak through the browser.
        </div>
        <button onClick={test} disabled={busy || !model}>
          {busy ? "Testing..." : "Test connection"}
        </button>
        {result && <div className={`notice ${result.ok ? "ok" : "err"}`}>{result.text}</div>}
      </div>
    </>
  );
}