import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import {
  enqueueCapture,
  fetchTimeline,
  PHOTO_TYPES,
  photoImageUrl,
  syncQueue,
  uploadPhoto,
  type PhotoType,
  type TimelineEntry,
} from "./lib/api";

const DOMAIN: Record<string, { emoji: string; label: string }> = {
  sleep: { emoji: "😴", label: "Sleep" },
  nutrition: { emoji: "🍳", label: "Food" },
  hydration: { emoji: "💧", label: "Hydration" },
  care: { emoji: "🧴", label: "Care" },
  photo: { emoji: "📸", label: "Photo" },
  body_metric: { emoji: "⚖️", label: "Body" },
  work: { emoji: "💼", label: "Work" },
  book: { emoji: "📚", label: "Books" },
  wardrobe: { emoji: "👕", label: "Wardrobe" },
  egestion: { emoji: "🚽", label: "Egestion" },
  gym: { emoji: "🏋️", label: "Gym" },
  mood: { emoji: "🧠", label: "Mood" },
  symptom: { emoji: "🤒", label: "Symptom" },
  supplement: { emoji: "💊", label: "Supplement" },
  media: { emoji: "📎", label: "Note" },
  location: { emoji: "📍", label: "Location" },
};

// Defaults mirror the API: face/skin/body/nails are sensitive (AES-encrypted), hair is not.
const SENSITIVE_DEFAULT: Record<PhotoType, boolean> = {
  face: true,
  skin: true,
  body: true,
  nails: true,
  hair: false,
};

const sameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString();

function dayLabel(iso: string): string {
  const d = new Date(iso);
  const today = new Date();
  const yest = new Date(today);
  yest.setDate(today.getDate() - 1);
  if (sameDay(d, today)) return "Today";
  if (sameDay(d, yest)) return "Yesterday";
  return d.toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" });
}

const timeLabel = (iso: string) =>
  new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });

function observationsOf(e: TimelineEntry): string[] {
  const a = e.structured?.analysis as { observations?: unknown } | undefined;
  return Array.isArray(a?.observations) ? (a!.observations as string[]).slice(0, 3) : [];
}

export default function App() {
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const [pending, setPending] = useState<{ file: File; url: string } | null>(null);
  const [ptype, setPtype] = useState<PhotoType>("skin");
  const [pnotes, setPnotes] = useState("");
  const [sensitive, setSensitive] = useState(true);
  const [excludeAi, setExcludeAi] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { data: entries = [], isLoading } = useQuery({ queryKey: ["timeline"], queryFn: fetchTimeline });

  async function log() {
    const t = text.trim();
    if (!t || busy) return;
    setBusy(true);
    try {
      await enqueueCapture(t);
      await syncQueue();
      setText("");
      await qc.invalidateQueries({ queryKey: ["timeline"] });
    } finally {
      setBusy(false);
    }
  }

  function pickPhoto(file: File) {
    setPtype("skin");
    setPnotes("");
    setSensitive(SENSITIVE_DEFAULT.skin);
    setExcludeAi(false);
    setPending({ file, url: URL.createObjectURL(file) });
  }

  function chooseType(t: PhotoType) {
    setPtype(t);
    setSensitive(SENSITIVE_DEFAULT[t]);
  }

  function closeComposer() {
    if (pending) URL.revokeObjectURL(pending.url);
    setPending(null);
  }

  async function submitPhoto() {
    if (!pending || uploading) return;
    setUploading(true);
    try {
      await uploadPhoto(pending.file, ptype, {
        notes: pnotes.trim() || undefined,
        sensitive,
        excludeFromCloudAi: excludeAi,
      });
      closeComposer();
      await qc.invalidateQueries({ queryKey: ["timeline"] });
    } catch (err) {
      alert(`Upload failed: ${(err as Error).message}`);
    } finally {
      setUploading(false);
    }
  }

  const groups: Record<string, TimelineEntry[]> = {};
  for (const e of entries) (groups[dayLabel(e.occurred_at)] ??= []).push(e);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <main className="mx-auto max-w-xl px-4 py-8">
        <header className="mb-6">
          <h1 className="text-2xl font-semibold tracking-tight">LifeOS</h1>
          <p className="text-sm text-neutral-400">Log anything — AI files it onto your timeline.</p>
        </header>

        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 p-3 focus-within:border-neutral-700">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") void log();
            }}
            placeholder="slept 11–7, eggs + coffee, did my PM skincare, skin felt oily…"
            rows={3}
            className="w-full resize-none bg-transparent text-base text-neutral-100 outline-none placeholder:text-neutral-600"
          />
          <div className="mt-2 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-xs text-neutral-500">⌘/Ctrl + Enter</span>
              <button
                onClick={() => fileInput.current?.click()}
                className="rounded-full border border-neutral-700 px-3 py-1.5 text-sm text-neutral-300 transition hover:border-neutral-500"
              >
                📷 Photo
              </button>
              <input
                ref={fileInput}
                type="file"
                accept="image/*"
                capture="environment"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) pickPhoto(f);
                  e.target.value = "";
                }}
              />
            </div>
            <button
              onClick={() => void log()}
              disabled={busy || !text.trim()}
              className="rounded-full bg-orange-500 px-4 py-1.5 text-sm font-medium text-black transition hover:bg-orange-400 disabled:opacity-40"
            >
              {busy ? "Logging…" : "Log"}
            </button>
          </div>
        </div>

        <section className="mt-8 space-y-6">
          {isLoading && <p className="text-sm text-neutral-500">Loading…</p>}
          {!isLoading && entries.length === 0 && (
            <p className="text-sm text-neutral-500">No entries yet — log your first above.</p>
          )}
          {Object.entries(groups).map(([day, items]) => (
            <div key={day}>
              <h2 className="mb-2 text-xs font-medium uppercase tracking-wider text-neutral-500">{day}</h2>
              <ul className="space-y-2">
                {items.map((e) => {
                  const d = DOMAIN[e.domain] ?? { emoji: "•", label: e.domain };
                  const low = e.confidence != null && e.confidence < 0.6;
                  const isPhoto = e.domain === "photo" && e.ref_id;
                  const obs = isPhoto ? observationsOf(e) : [];
                  return (
                    <li
                      key={e.id}
                      className="flex gap-3 rounded-xl border border-neutral-800/70 bg-neutral-900/40 p-3"
                    >
                      <div className="text-xl leading-none">{d.emoji}</div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="rounded-full bg-neutral-800 px-2 py-0.5 text-[11px] text-neutral-300">
                            {d.label}
                          </span>
                          <span className="text-[11px] text-neutral-500">{timeLabel(e.occurred_at)}</span>
                          {low && <span className="text-[11px] text-amber-400">needs confirm</span>}
                        </div>
                        <p className="mt-1 text-sm text-neutral-200">{e.summary}</p>
                        {isPhoto && (
                          <div className="mt-2 flex gap-3">
                            <img
                              src={photoImageUrl(e.ref_id!)}
                              alt={`${e.domain} photo`}
                              loading="lazy"
                              className="h-24 w-24 shrink-0 rounded-lg border border-neutral-800 object-cover"
                            />
                            {obs.length > 0 && (
                              <ul className="min-w-0 list-disc space-y-0.5 pl-4 text-xs text-neutral-400">
                                {obs.map((o, i) => (
                                  <li key={i}>{o}</li>
                                ))}
                              </ul>
                            )}
                          </div>
                        )}
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </section>
      </main>

      {pending && (
        <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/70 p-4 sm:items-center">
          <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-4">
            <div className="flex gap-3">
              <img
                src={pending.url}
                alt="preview"
                className="h-28 w-28 shrink-0 rounded-lg border border-neutral-800 object-cover"
              />
              <div className="flex-1">
                <h3 className="text-sm font-medium">Add photo</h3>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {PHOTO_TYPES.map((t) => (
                    <button
                      key={t}
                      onClick={() => chooseType(t)}
                      className={`rounded-full px-2.5 py-1 text-xs capitalize transition ${
                        ptype === t
                          ? "bg-orange-500 text-black"
                          : "border border-neutral-700 text-neutral-300 hover:border-neutral-500"
                      }`}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <input
              value={pnotes}
              onChange={(e) => setPnotes(e.target.value)}
              placeholder="notes (optional) — e.g. left cheek, after AM routine"
              className="mt-3 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm outline-none placeholder:text-neutral-600 focus:border-neutral-600"
            />

            <label className="mt-3 flex items-center justify-between text-sm">
              <span>
                🔒 Sensitive <span className="text-neutral-500">(encrypt at rest)</span>
              </span>
              <input type="checkbox" checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} />
            </label>
            <label className="mt-2 flex items-center justify-between text-sm">
              <span>
                🚫 Skip cloud AI <span className="text-neutral-500">(no vision analysis)</span>
              </span>
              <input type="checkbox" checked={excludeAi} onChange={(e) => setExcludeAi(e.target.checked)} />
            </label>

            <div className="mt-4 flex justify-end gap-2">
              <button
                onClick={closeComposer}
                className="rounded-full px-4 py-1.5 text-sm text-neutral-400 hover:text-neutral-200"
              >
                Cancel
              </button>
              <button
                onClick={() => void submitPhoto()}
                disabled={uploading}
                className="rounded-full bg-orange-500 px-4 py-1.5 text-sm font-medium text-black transition hover:bg-orange-400 disabled:opacity-40"
              >
                {uploading ? "Uploading…" : "Save photo"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
