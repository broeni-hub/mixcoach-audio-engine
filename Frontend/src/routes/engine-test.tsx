import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";

export const Route = createFileRoute("/engine-test")({
  component: EngineTestPage,
});

function EngineTestPage() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function analyze() {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const form = new FormData();
      form.append("file", file, file.name);

      const baseUrl =
        import.meta.env.VITE_AUDIO_ENGINE_URL || "http://127.0.0.1:8000";

      const response = await fetch(`${baseUrl}/analyze/set`, {
        method: "POST",
        body: form,
      });

      if (!response.ok) {
        throw new Error(await response.text());
      }

      setResult(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: 32, fontFamily: "sans-serif" }}>
      <h1>MixCoach Engine Test</h1>

      <input
        type="file"
        accept=".mp3,.wav,.aiff,.aif,.flac,.m4a"
        onChange={(event) => setFile(event.target.files?.[0] ?? null)}
      />

      <div style={{ marginTop: 16 }}>
        <button disabled={!file || loading} onClick={analyze}>
          {loading ? "Analyzing..." : "Analyze with Python Engine"}
        </button>
      </div>

      {error && (
        <pre style={{ color: "red", marginTop: 24, whiteSpace: "pre-wrap" }}>
          {error}
        </pre>
      )}

      {result && (
        <pre style={{ marginTop: 24, whiteSpace: "pre-wrap" }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}