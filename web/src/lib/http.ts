// Shared HTTP base + bearer-token storage. Frontend and API are on different domains, so we use a
// signed bearer token (localStorage) rather than cross-site cookies (see docs grounding).
export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const TOKEN_KEY = "lifeos_token";
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export class AuthError extends Error {}

export function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  const t = getToken();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

// fetch wrapper that attaches the bearer token and converts a 401 into a re-auth signal.
export async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: authHeaders((init.headers as Record<string, string>) ?? {}),
  });
  if (res.status === 401) {
    clearToken();
    window.dispatchEvent(new Event("lifeos:unauthorized"));
    throw new AuthError("unauthorized");
  }
  return res;
}
