import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import Auth from "./Auth";
import PhotoComposer from "./PhotoComposer";
import WithingsButton from "./Withings";
import { enqueueCapture, fetchTimeline, photoImageUrl, syncQueue, type TimelineEntry } from "./lib/api";
import { logout } from "./lib/auth";
import { getToken } from "./lib/http";

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

// Structured fields to reveal on expand (the parse the API filed into a domain table).
function structuredPairs(e: TimelineEntry): [string, string][] {
  const s = e.structured ?? {};
  return Object.entries(s)
    .filter(([k]) => k !== "analysis" && k !== "prompt_version")
    .map(([k, v]) => [k, typeof v === "object" && v !== null ? JSON.stringify(v) : String(v)] as [string, string])
    .filter(([, v]) => v && v !== "null" && v !== "{}" && v !== "[]");
}

export default function App() {
  const qc = useQueryClient();
  const [authed, setAuthed] = useState(() => !!getToken());
  useEffect(() => {
    const onUnauth = () => setAuthed(false); // a 401 from any request drops us to the gate
    window.addEventListener("lifeos:unauthorized", onUnauth);
    return () => window.removeEventListener("lifeos:unauthorized", onUnauth);
  }, []);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [composing, setComposing] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const { data: entries = [], isLoading } = useQuery({
    queryKey: ["timeline"],
    queryFn: fetchTimeline,
    enabled: authed,
  });

  if (!authed)
    return (
      <Auth
        onAuthed={() => {
          setAuthed(true);
          void qc.invalidateQueries({ queryKey: ["timeline"] });
          void syncQueue();
        }}
      />
    );

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

  const groups: Record<string, TimelineEntry[]> = {};
  for (const e of entries) (groups[dayLabel(e.occurred_at)] ??= []).push(e);

  return (
    <div className="min-h-screen bg-neutral-950 text-neutral-100">
      <main className="mx-auto max-w-xl px-4 py-8">
        <header className="mb-6 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">LifeOS</h1>
            <p className="text-sm text-neutral-400">Log anything — AI files it onto your timeline.</p>
          </div>
          <div className="flex items-center gap-3">
            <WithingsButton />
            <button
              onClick={() => {
                logout();
                setAuthed(false);
              }}
              className="text-xs text-neutral-500 hover:text-neutral-300"
            >
              Lock
            </button>
          </div>
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
                onClick={() => setComposing(true)}
                className="rounded-full border border-neutral-700 px-3 py-1.5 text-sm text-neutral-300 transition hover:border-neutral-500"
              >
                📷 Photo
              </button>
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
                  const pairs = structuredPairs(e);
                  const isOpen = open === e.id;
                  return (
                    <li
                      key={e.id}
                      className="overflow-hidden rounded-xl border border-neutral-800/70 bg-neutral-900/40"
                    >
                      <div
                        className={`flex gap-3 p-3 ${pairs.length ? "cursor-pointer" : ""}`}
                        onClick={() => pairs.length && setOpen(isOpen ? null : e.id)}
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
                                src={photoImageUrl(e.ref_id!, e.media_token)}
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
                        {pairs.length > 0 && (
                          <span className="select-none text-xs text-neutral-600">{isOpen ? "▲" : "▼"}</span>
                        )}
                      </div>
                      {isOpen && pairs.length > 0 && (
                        <dl className="border-t border-neutral-800/70 px-3 py-2 text-xs">
                          {pairs.map(([k, v]) => (
                            <div key={k} className="flex gap-2 py-0.5">
                              <dt className="min-w-24 shrink-0 capitalize text-neutral-500">
                                {k.replace(/_/g, " ")}
                              </dt>
                              <dd className="break-all text-neutral-300">{v}</dd>
                            </div>
                          ))}
                        </dl>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </section>
      </main>

      {composing && (
        <PhotoComposer
          onClose={() => setComposing(false)}
          onSaved={() => {
            setComposing(false);
            void qc.invalidateQueries({ queryKey: ["timeline"] });
          }}
        />
      )}
    </div>
  );
}
