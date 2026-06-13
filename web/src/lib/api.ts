import { db } from "./db";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

// Write to the local queue first (works offline), then attempt sync.
export async function enqueueCapture(text: string, domainHint?: string): Promise<void> {
  const now = new Date().toISOString();
  await db.captures.add({
    text,
    occurred_at: now,
    domain_hint: domainHint,
    source: "manual",
    media_keys: [],
    created_at: now,
    synced: 0,
  });
  void syncQueue();
}

export async function syncQueue(): Promise<void> {
  if (!navigator.onLine) return;
  const pending = await db.captures.where("synced").equals(0).toArray();
  for (const c of pending) {
    try {
      const res = await fetch(`${API}/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: c.text,
          occurred_at: c.occurred_at,
          domain_hint: c.domain_hint,
          source: c.source,
          media_keys: c.media_keys,
        }),
      });
      if (res.ok && c.id != null) await db.captures.update(c.id, { synced: 1 });
    } catch {
      // offline / transient — will retry on next sync
    }
  }
}

window.addEventListener("online", () => void syncQueue());
