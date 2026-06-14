import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { withingsAuthorizeUrl, withingsStatus, withingsSync } from "./lib/withings";

// Body-composition auto-sync control. Connect = OAuth redirect to Withings; once connected the
// button triggers a manual sync (the webhook handles new measurements automatically thereafter).
export default function WithingsButton() {
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["withings"], queryFn: withingsStatus });

  // Handle the OAuth redirect back from /withings/callback.
  useEffect(() => {
    const p = new URLSearchParams(window.location.search).get("withings");
    if (!p) return;
    history.replaceState(null, "", window.location.pathname);
    if (p === "connected") {
      void withingsSync()
        .then(() => qc.invalidateQueries({ queryKey: ["withings"] }))
        .finally(() => setTimeout(() => qc.invalidateQueries({ queryKey: ["timeline"] }), 3000));
    } else if (p === "error") {
      alert("Withings connection failed — please try again.");
    }
  }, [qc]);

  async function onClick() {
    if (data?.connected) {
      await withingsSync();
      setTimeout(() => qc.invalidateQueries({ queryKey: ["timeline"] }), 3000);
    } else {
      window.location.href = await withingsAuthorizeUrl();
    }
  }

  return (
    <button
      onClick={() => void onClick()}
      className="text-xs text-neutral-500 hover:text-neutral-300"
      title={data?.connected ? `Connected${data.last_sync_at ? ` · last sync ${new Date(data.last_sync_at).toLocaleString()}` : ""}` : "Connect your Withings scale"}
    >
      {data?.connected ? "⚖️ Sync Withings" : "⚖️ Connect Withings"}
    </button>
  );
}
