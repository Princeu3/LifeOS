import { useEffect, useState } from "react";
import { fetchStatus, login, recover, register, type AuthStatus } from "./lib/auth";

const card =
  "w-full max-w-sm rounded-2xl border border-neutral-800 bg-neutral-900/70 p-6 text-neutral-100";
const primaryBtn =
  "w-full rounded-full bg-orange-500 px-4 py-2 text-sm font-medium text-black transition hover:bg-orange-400 disabled:opacity-40";
const input =
  "w-full rounded-lg border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm outline-none placeholder:text-neutral-600 focus:border-neutral-600";

export default function Auth({ onAuthed }: { onAuthed: () => void }) {
  const [status, setStatus] = useState<AuthStatus | null | "error">(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [mode, setMode] = useState<"login" | "recovery">("login");
  const [bootstrapToken, setBootstrapToken] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState<string | null>(null);

  useEffect(() => {
    fetchStatus().then(setStatus).catch(() => setStatus("error"));
  }, []);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setErr(null);
    try {
      await fn();
    } catch (e) {
      setErr((e as Error).message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const wrap = (children: React.ReactNode) => (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 px-4">
      <div className={card}>
        <h1 className="text-xl font-semibold tracking-tight">LifeOS</h1>
        {children}
        {err && <p className="mt-3 text-sm text-red-400">{err}</p>}
      </div>
    </div>
  );

  // One-time recovery-code display (after first registration or after a recovery).
  if (recoveryCode) {
    return wrap(
      <>
        <p className="mt-2 text-sm text-neutral-400">
          Save this recovery code somewhere safe. It's the only way back in if you lose your passkey.
        </p>
        <code className="mt-3 block break-all rounded-lg border border-orange-500/40 bg-neutral-950 px-3 py-2 text-center text-sm text-orange-300">
          {recoveryCode}
        </code>
        <button className={`${primaryBtn} mt-4`} onClick={onAuthed}>
          I've saved it — continue
        </button>
      </>,
    );
  }

  if (status === null) return wrap(<p className="mt-2 text-sm text-neutral-500">Loading…</p>);
  if (status === "error")
    return wrap(
      <>
        <p className="mt-2 text-sm text-neutral-400">Couldn't reach the server.</p>
        <button className={`${primaryBtn} mt-4`} onClick={() => location.reload()}>
          Retry
        </button>
      </>,
    );

  // First-run setup — create the first passkey (gated by a setup token if the server requires one).
  if (!status.registered) {
    return wrap(
      <>
        <p className="mt-2 text-sm text-neutral-400">Set up your passkey to secure your data.</p>
        <div className="mt-4 space-y-2">
          <input
            className={input}
            placeholder="passkey name (e.g. MacBook)"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          {status.needs_bootstrap_token && (
            <input
              className={input}
              placeholder="setup token"
              value={bootstrapToken}
              onChange={(e) => setBootstrapToken(e.target.value)}
            />
          )}
        </div>
        <button
          className={`${primaryBtn} mt-4`}
          disabled={busy || (status.needs_bootstrap_token && !bootstrapToken)}
          onClick={() =>
            run(async () => {
              const { recoveryCode } = await register({
                name: name.trim() || undefined,
                bootstrapToken: bootstrapToken.trim() || undefined,
              });
              if (recoveryCode) setRecoveryCode(recoveryCode);
              else onAuthed();
            })
          }
        >
          {busy ? "Creating…" : "Create passkey"}
        </button>
      </>,
    );
  }

  // Returning user — unlock with a passkey, or fall back to the recovery code.
  return wrap(
    <>
      {mode === "login" ? (
        <>
          <p className="mt-2 text-sm text-neutral-400">Unlock with your passkey.</p>
          <button
            className={`${primaryBtn} mt-4`}
            disabled={busy}
            onClick={() => run(async () => { await login(); onAuthed(); })}
          >
            {busy ? "Unlocking…" : "🔑 Unlock with passkey"}
          </button>
          <button
            className="mt-3 w-full text-center text-xs text-neutral-500 hover:text-neutral-300"
            onClick={() => { setErr(null); setMode("recovery"); }}
          >
            Lost your passkey? Use a recovery code
          </button>
        </>
      ) : (
        <>
          <p className="mt-2 text-sm text-neutral-400">Enter your recovery code.</p>
          <input
            className={`${input} mt-3`}
            placeholder="recovery code"
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <button
            className={`${primaryBtn} mt-3`}
            disabled={busy || !code.trim()}
            onClick={() =>
              run(async () => {
                const { recoveryCode } = await recover(code.trim());
                setRecoveryCode(recoveryCode); // show the rotated code, then continue
              })
            }
          >
            {busy ? "Recovering…" : "Recover access"}
          </button>
          <button
            className="mt-3 w-full text-center text-xs text-neutral-500 hover:text-neutral-300"
            onClick={() => { setErr(null); setMode("login"); }}
          >
            Back to passkey
          </button>
        </>
      )}
    </>,
  );
}
