import { useEffect, useRef, useState } from "react";
import {
  fetchLatestPhoto,
  PHOTO_TYPES,
  photoImageUrl,
  uploadPhoto,
  type PhotoType,
} from "./lib/api";

// Mirrors the API defaults: face/skin/body/nails are sensitive (AES-encrypted), hair is not.
const SENSITIVE_DEFAULT: Record<PhotoType, boolean> = {
  face: true,
  skin: true,
  body: true,
  nails: true,
  hair: false,
};
// Front camera for face/skin selfies; rear for body/nails/hair.
const FACING_DEFAULT: Record<PhotoType, "user" | "environment"> = {
  face: "user",
  skin: "user",
  body: "environment",
  nails: "environment",
  hair: "environment",
};

const primaryBtn =
  "rounded-full bg-orange-500 px-4 py-1.5 text-sm font-medium text-black transition hover:bg-orange-400 disabled:opacity-40";

/**
 * Live camera with a translucent "ghost" of the previous same-type photo overlaid, so the user
 * can match their framing/pose. Captures a still via canvas (no mirroring — preview, ghost, and
 * saved file all share one orientation so alignment is consistent). Falls back to a file input
 * when getUserMedia is unavailable or denied.
 */
function CameraCapture({
  ghostUrl,
  facing: facingDefault,
  onCapture,
}: {
  ghostUrl: string | null;
  facing: "user" | "environment";
  onCapture: (file: File) => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [facing, setFacing] = useState(facingDefault);
  const [opacity, setOpacity] = useState(0.45);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function start() {
      // getUserMedia needs a secure context; absent it (or on older browsers) use the file fallback.
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("Live camera isn't available here — upload a photo instead.");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facing }, // bare string = {ideal}; never {exact} (OverconstrainedError)
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch(() => {});
        }
        setError(null);
      } catch (e) {
        const name = (e as Error).name;
        setError(
          name === "NotAllowedError"
            ? "Camera permission denied — upload a photo instead."
            : "Camera unavailable — upload a photo instead.",
        );
      }
    }
    void start();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop()); // release the camera light
      streamRef.current = null;
      if (videoRef.current) videoRef.current.srcObject = null;
    };
  }, [facing]);

  function capture() {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return;
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    canvas.getContext("2d")?.drawImage(v, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (b) => b && onCapture(new File([b], "capture.jpg", { type: "image/jpeg" })),
      "image/jpeg",
      0.92,
    );
  }

  return (
    <div>
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl bg-black">
        <video ref={videoRef} playsInline muted autoPlay className="h-full w-full object-cover" />
        {ghostUrl && (
          <img
            src={ghostUrl}
            alt=""
            className="pointer-events-none absolute inset-0 h-full w-full object-cover"
            style={{ opacity }}
          />
        )}
        {error && (
          <div className="absolute inset-0 grid place-items-center p-4 text-center text-sm text-neutral-300">
            {error}
          </div>
        )}
        <button
          onClick={() => setFacing((f) => (f === "user" ? "environment" : "user"))}
          className="absolute right-2 top-2 rounded-full bg-black/50 px-2 py-1 text-xs text-white"
        >
          ⟲ flip
        </button>
      </div>

      {ghostUrl && (
        <label className="mt-3 flex items-center gap-2 text-xs text-neutral-400">
          ghost
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
            className="flex-1 accent-orange-500"
          />
        </label>
      )}

      <div className="mt-3 flex items-center justify-between">
        <button
          onClick={() => fileRef.current?.click()}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          Upload a file instead
        </button>
        <button onClick={capture} disabled={!!error} className={primaryBtn}>
          📸 Capture
        </button>
      </div>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        capture={facing}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onCapture(f);
          e.target.value = "";
        }}
      />
    </div>
  );
}

export default function PhotoComposer({
  onClose,
  onSaved,
}: {
  onClose: () => void;
  onSaved: () => void;
}) {
  const [step, setStep] = useState<"type" | "capture" | "details">("type");
  const [ptype, setPtype] = useState<PhotoType>("skin");
  const [ghostUrl, setGhostUrl] = useState<string | null>(null);
  const [captured, setCaptured] = useState<{ file: File; url: string } | null>(null);
  const [notes, setNotes] = useState("");
  const [sensitive, setSensitive] = useState(true);
  const [excludeAi, setExcludeAi] = useState(false);
  const [busy, setBusy] = useState(false);

  // revoke any object URLs we created
  useEffect(() => {
    return () => {
      if (captured) URL.revokeObjectURL(captured.url);
    };
  }, [captured]);

  async function chooseType(t: PhotoType) {
    setPtype(t);
    setSensitive(SENSITIVE_DEFAULT[t]);
    setGhostUrl(null);
    try {
      const ref = await fetchLatestPhoto(t);
      if (ref) setGhostUrl(photoImageUrl(ref.id, ref.media_token));
    } catch {
      /* no ghost is fine */
    }
    setStep("capture");
  }

  function onCapture(file: File) {
    setCaptured({ file, url: URL.createObjectURL(file) });
    setStep("details");
  }

  async function save() {
    if (!captured || busy) return;
    setBusy(true);
    try {
      await uploadPhoto(captured.file, ptype, {
        notes: notes.trim() || undefined,
        sensitive,
        excludeFromCloudAi: excludeAi,
      });
      onSaved();
    } catch (e) {
      alert(`Upload failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-10 flex items-end justify-center bg-black/70 p-4 sm:items-center">
      <div className="w-full max-w-md rounded-2xl border border-neutral-800 bg-neutral-900 p-4 text-neutral-100">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">
            {step === "type" ? "What are you capturing?" : `${ptype[0].toUpperCase()}${ptype.slice(1)} photo`}
          </h3>
          <button onClick={onClose} className="text-xs text-neutral-500 hover:text-neutral-300">
            Cancel
          </button>
        </div>

        {step === "type" && (
          <div className="mt-3 flex flex-wrap gap-2">
            {PHOTO_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => void chooseType(t)}
                className="rounded-full border border-neutral-700 px-3 py-1.5 text-sm capitalize text-neutral-200 transition hover:border-orange-500 hover:text-orange-300"
              >
                {t}
              </button>
            ))}
          </div>
        )}

        {step === "capture" && (
          <div className="mt-3">
            {ghostUrl && (
              <p className="mb-2 text-xs text-neutral-500">
                Aligning to your last {ptype} photo — match the ghost, then capture.
              </p>
            )}
            <CameraCapture ghostUrl={ghostUrl} facing={FACING_DEFAULT[ptype]} onCapture={onCapture} />
          </div>
        )}

        {step === "details" && captured && (
          <div className="mt-3">
            <div className="relative aspect-[3/4] w-full overflow-hidden rounded-xl bg-black">
              <img src={captured.url} alt="captured" className="h-full w-full object-cover" />
              {ghostUrl && (
                <img
                  src={ghostUrl}
                  alt=""
                  className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-30"
                />
              )}
            </div>
            <input
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="notes (optional) — e.g. left cheek, after AM routine"
              className="mt-3 w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm outline-none placeholder:text-neutral-600 focus:border-neutral-600"
            />
            <label className="mt-3 flex items-center justify-between text-sm">
              <span>🔒 Sensitive <span className="text-neutral-500">(encrypt at rest)</span></span>
              <input type="checkbox" checked={sensitive} onChange={(e) => setSensitive(e.target.checked)} />
            </label>
            <label className="mt-2 flex items-center justify-between text-sm">
              <span>🚫 Skip cloud AI <span className="text-neutral-500">(no vision analysis)</span></span>
              <input type="checkbox" checked={excludeAi} onChange={(e) => setExcludeAi(e.target.checked)} />
            </label>
            <div className="mt-4 flex justify-between">
              <button
                onClick={() => {
                  setCaptured(null);
                  setStep("capture");
                }}
                className="rounded-full px-4 py-1.5 text-sm text-neutral-400 hover:text-neutral-200"
              >
                ↺ Retake
              </button>
              <button onClick={() => void save()} disabled={busy} className={primaryBtn}>
                {busy ? "Uploading…" : "Save photo"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
