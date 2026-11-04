import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function Claims() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({
    queryKey: ["journal"],
    queryFn: journal.list,
    staleTime: 0,
  });
  const claims = (entries.data ?? []).filter((entry) => entry.kind === "claim");

  const open = () => {
    if (isRhoUri(uri.trim())) navigate(`/claims/${uri.trim()}`);
  };

  return (
    <div className="stack">
      <Panel
        title={<h1>Claims</h1>}
        actions={<Link to="/claims/new">New claim</Link>}
      >
        <p className="muted small">
          The chain has no index. This list is the claims this browser has seen or created;
          any claim with its share link opens here.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open a claim by rho:id:…"
            className="mono"
            onKeyDown={(event) => event.key === "Enter" && open()}
          />
          <button onClick={open}>Open claim</button>
        </div>
        {entries.isLoading && <p className="muted">loading local journal…</p>}
        {claims.length === 0 && (
          <Empty>
            No claims in this browser yet. Create one, or paste a share link above.
          </Empty>
        )}
        <div className="list">
          {claims.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/claims/${entry.uri}`}>{entry.summary}</Link>
                ) : (
                  <span>{entry.summary}</span>
                )}
                <div className="muted small">
                  {entry.uri ? `${entry.uri.slice(0, 24)}…` : entry.kind} ·{" "}
                  {relative(entry.createdAt)}
                </div>
              </div>
              <StatusPill status={entry.status} />
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
