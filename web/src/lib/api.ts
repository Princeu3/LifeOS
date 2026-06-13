import { db } from "./db";
import { downscaleImage } from "./image";

export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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

export interface TimelineEntry {
  id: string;
  occurred_at: string;
  domain: string;
  source: string;
  summary: string | null;
  confidence: number | null;
  structured?: Record<string, unknown> | null;
  ref_table?: string | null;
  ref_id?: string | null;
  media?: { bucket_key: string; photo_id?: string }[];
}

export async function fetchTimeline(): Promise<TimelineEntry[]> {
  const r = await fetch(`${API}/timeline`);
  if (!r.ok) throw new Error(`timeline ${r.status}`);
  return r.json();
}

export const PHOTO_TYPES = ["face", "skin", "body", "nails", "hair"] as const;
export type PhotoType = (typeof PHOTO_TYPES)[number];

export interface PhotoOut {
  id: string;
  photo_type: string;
  sensitive: boolean;
  exclude_from_cloud_ai: boolean;
  analysis: Record<string, unknown> | null;
  ai_model: string | null;
  ai_confidence: number | null;
  event_id: string | null;
}

// Built so the client can fetch (and, for sensitive media, decrypt-on-read via) the API proxy.
export const photoImageUrl = (refId: string) => `${API}/photos/${refId}/image`;

export async function uploadPhoto(
  file: File,
  photoType: PhotoType,
  opts: { notes?: string; sensitive?: boolean; excludeFromCloudAi?: boolean } = {},
): Promise<PhotoOut> {
  const scaled = await downscaleImage(file); // keep payload < OpenRouter's 32MB cap, cut cost/storage
  const form = new FormData();
  form.append("file", scaled);
  form.append("photo_type", photoType);
  form.append("occurred_at", new Date().toISOString());
  if (opts.notes) form.append("notes", opts.notes);
  if (opts.sensitive != null) form.append("sensitive", String(opts.sensitive));
  if (opts.excludeFromCloudAi != null)
    form.append("exclude_from_cloud_ai", String(opts.excludeFromCloudAi));
  const r = await fetch(`${API}/photos`, { method: "POST", body: form });
  if (!r.ok) throw new Error(`photo upload ${r.status}`);
  return r.json();
}
