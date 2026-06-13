import { useEffect, useState } from "react";
import { enqueueCapture, syncQueue } from "./lib/api";
import { db } from "./lib/db";

// Phase-2 skeleton: the universal freeform capture surface.
// Structured-default-else-freeform parsing happens server-side (Phase 4).
export default function App() {
  const [text, setText] = useState("");
  const [pending, setPending] = useState(0);

  async function refresh() {
    setPending(await db.captures.where("synced").equals(0).count());
  }

  useEffect(() => {
    void syncQueue().then(refresh);
  }, []);

  async function log() {
    if (!text.trim()) return;
    await enqueueCapture(text.trim());
    setText("");
    await refresh();
  }

  return (
    <main style={{ maxWidth: 560, margin: "0 auto", padding: 16, fontFamily: "system-ui" }}>
      <h1>LifeOS</h1>
      <p style={{ color: "#666" }}>
        Log anything — sleep, food, skincare, mood, gym. AI structures it later
        (structured-default, freeform fallback).
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. slept 11–7, eggs + coffee, showered, skin felt oily"
        rows={3}
        style={{ width: "100%", padding: 8, fontSize: 16, boxSizing: "border-box" }}
      />
      <button onClick={log} style={{ marginTop: 8, padding: "8px 16px", fontSize: 16 }}>
        Log
      </button>
      <p style={{ color: "#999", marginTop: 12 }}>
        {pending > 0 ? `${pending} pending sync` : "all synced"}
      </p>
    </main>
  );
}
