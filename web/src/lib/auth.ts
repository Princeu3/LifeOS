import { startAuthentication, startRegistration } from "@simplewebauthn/browser";
import { API, authHeaders, clearToken, setToken } from "./http";

export interface AuthStatus {
  registered: boolean;
  credentials: number;
  max: number;
  recovery_set: boolean;
  needs_bootstrap_token: boolean;
}

async function detail(res: Response, fallback: string): Promise<string> {
  return ((await res.json().catch(() => ({}))) as { detail?: string }).detail ?? fallback;
}

export async function fetchStatus(): Promise<AuthStatus> {
  const r = await fetch(`${API}/auth/status`);
  if (!r.ok) throw new Error(`status ${r.status}`);
  return r.json();
}

// Register a passkey. First one is the bootstrap (may need a setup token); a 2nd needs a session.
export async function register(
  opts: { name?: string; bootstrapToken?: string } = {},
): Promise<{ recoveryCode: string | null }> {
  const headers: Record<string, string> = authHeaders({ "Content-Type": "application/json" });
  if (opts.bootstrapToken) headers["X-Bootstrap-Token"] = opts.bootstrapToken;

  const optRes = await fetch(`${API}/auth/register/options`, {
    method: "POST",
    headers,
    body: JSON.stringify({ name: opts.name }),
  });
  if (!optRes.ok) throw new Error(await detail(optRes, `register options ${optRes.status}`));
  const { options, state } = await optRes.json();

  const response = await startRegistration({ optionsJSON: options });

  const verRes = await fetch(`${API}/auth/register/verify`, {
    method: "POST",
    headers,
    body: JSON.stringify({ response, state, name: opts.name }),
  });
  if (!verRes.ok) throw new Error(await detail(verRes, `register verify ${verRes.status}`));
  const data = await verRes.json();
  setToken(data.token);
  return { recoveryCode: data.recovery_code ?? null };
}

export async function login(): Promise<void> {
  const optRes = await fetch(`${API}/auth/login/options`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!optRes.ok) throw new Error(await detail(optRes, `login options ${optRes.status}`));
  const { options, state } = await optRes.json();

  const response = await startAuthentication({ optionsJSON: options });

  const verRes = await fetch(`${API}/auth/login/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ response, state }),
  });
  if (!verRes.ok) throw new Error(await detail(verRes, `login verify ${verRes.status}`));
  setToken((await verRes.json()).token);
}

// Recovery is single-use: the server rotates it and returns a fresh code to save.
export async function recover(code: string): Promise<{ recoveryCode: string }> {
  const r = await fetch(`${API}/auth/recovery`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code }),
  });
  if (!r.ok) throw new Error(await detail(r, "invalid recovery code"));
  const data = await r.json();
  setToken(data.token);
  return { recoveryCode: data.recovery_code };
}

export const logout = () => clearToken();
