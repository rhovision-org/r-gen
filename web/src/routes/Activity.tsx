import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import * as journal from "../lib/journal";
import { useWallet } from "../lib/store";
import { relative, when } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

const ROUTE: Record<string, string> = {
  claim: "claims",
  kasset: "kassets",
  credential: "credentials",
  value: "value",
  case: "cases",
  provenance: "provenance",
};

export default function Activity() {
  const client = useWallet((state) => state.client);
  const queryClient = useQueryClient();
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reconcile = async (id: string, deployId: string) => {
    if (!client) return;
    setBusy(id);
    setError(null);
    try {
      const status = JSON.parse(await client.deploy_status(deployId)) as {
        processed?: boolean;
        success?: boolean;
        status?: string;
        blockNumber?: number;
      };
      await journal.mark(id, {
        status: status.success
          ? "finalized"
          : status.processed
            ? "failed"
            : "unknown",
        blockNumber: status.blockNumber,
      });
      await queryClient.invalidateQueries({ queryKey: ["journal"] });
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="stack">
      <Panel title={<h1>Activity</h1>}>
        <p className="muted small">
          This is the browser's journal, not a chain index. Each row is one signed deploy
          this browser submitted; reconcile asks the node for its status.
        </p>
        {error && <p className="error">{error}</p>}
        {entries.isLoading && <p className="muted">loading…</p>}
        {entries.data && entries.data.length === 0 && (
          <Empty>No activity yet. Every write you sign will appear here.</Empty>
        )}
        <div className="list">
          {(entries.data ?? []).map((entry) => {
            const route = ROUTE[entry.kind];
            return (
              <div className="list-row" key={entry.id}>
                <div>
                  {entry.uri && route ? (
                    <Link to={`/${route}/${entry.uri}`}>{entry.summary}</Link>
                  ) : (
                    <strong>{entry.summary}</strong>
                  )}
                  <div className="muted small">
                    {entry.kind} · {relative(entry.createdAt)} · {when(entry.createdAt)}
                    {entry.blockNumber !== undefined && ` · block ${entry.blockNumber}`}
                  </div>
                  {entry.deployId && (
                    <div className="mono small" title={entry.deployId}>
                      {entry.deployId}
                    </div>
                  )}
                  {entry.refusal && <div className="small error">{entry.refusal}</div>}
                </div>
                <div className="row gap">
                  <StatusPill status={entry.status} />
                  {entry.deployId && (
                    <button
                      className="ghost small-button"
                      disabled={busy === entry.id}
                      onClick={() => void reconcile(entry.id, entry.deployId!)}
                    >
                      {busy === entry.id ? "checking…" : "reconcile"}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </Panel>
    </div>
  );
}
