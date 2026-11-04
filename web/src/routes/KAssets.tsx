import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function KAssets() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const kassets = (entries.data ?? []).filter((entry) => entry.kind === "kasset");

  return (
    <div className="stack">
      <Panel title={<h1>K-Assets</h1>}>
        <p className="muted small">
          A K-Asset is created by a real claim validation. There is no factory for it and no
          index; the K-Asset URI comes back from <code>Claim.validate</code>.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open a K-Asset by rho:id:…"
            className="mono"
            onKeyDown={(event) => {
              if (event.key === "Enter" && isRhoUri(uri.trim())) navigate(`/kassets/${uri.trim()}`);
            }}
          />
          <button
            onClick={() => isRhoUri(uri.trim()) && navigate(`/kassets/${uri.trim()}`)}
          >
            Open K-Asset
          </button>
        </div>
        {kassets.length === 0 && (
          <Empty>No K-Assets in this browser yet. Validate a claim, or paste a share link.</Empty>
        )}
        <div className="list">
          {kassets.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/kassets/${entry.uri}`}>{entry.summary}</Link>
                ) : (
                  <span>{entry.summary}</span>
                )}
                <div className="muted small">{relative(entry.createdAt)}</div>
              </div>
              <StatusPill status={entry.status} />
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
