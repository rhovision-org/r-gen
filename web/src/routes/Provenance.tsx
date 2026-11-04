import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function Provenance() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const records = (entries.data ?? []).filter((entry) => entry.kind === "provenance");

  return (
    <div className="stack">
      <Panel
        title={<h1>Provenance</h1>}
        actions={<Link to="/provenance/new">New provenance record</Link>}
      >
        <p className="muted small">
          Provenance is append-only. Only a declared writer can anchor or comment; the
          registry verifies membership in one direction.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open provenance by rho:id:…"
            className="mono"
            onKeyDown={(event) => {
              if (event.key === "Enter" && isRhoUri(uri.trim())) {
                navigate(`/provenance/${uri.trim()}`);
              }
            }}
          />
          <button
            onClick={() =>
              isRhoUri(uri.trim()) && navigate(`/provenance/${uri.trim()}`)
            }
          >
            Open provenance
          </button>
        </div>
        {records.length === 0 && (
          <Empty>No provenance records in this browser yet. Create one, or paste a share link.</Empty>
        )}
        <div className="list">
          {records.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/provenance/${entry.uri}`}>{entry.summary}</Link>
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
