import { authedFetch } from "./http";

export interface WithingsStatus {
  connected: boolean;
  userid: string | null;
  last_sync_at: string | null;
  scope: string | null;
}

export async function withingsStatus(): Promise<WithingsStatus> {
  const r = await authedFetch("/withings/status");
  if (!r.ok) throw new Error(`withings status ${r.status}`);
  return r.json();
}

export async function withingsAuthorizeUrl(): Promise<string> {
  const r = await authedFetch("/withings/authorize");
  if (!r.ok) throw new Error(`withings authorize ${r.status}`);
  return (await r.json()).url as string;
}

export async function withingsSync(): Promise<void> {
  const r = await authedFetch("/withings/sync", { method: "POST" });
  if (!r.ok) throw new Error(`withings sync ${r.status}`);
}
