import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function ValuePropositions() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const values = (entries.data ?? []).filter((entry) => entry.kind === "value");

  return (
    <div className="stack">
      <Panel
        title={<h1>Value propositions</h1>}
        actions={<Link to="/value/new">New value proposition</Link>}
      >
        <p className="muted small">
          A value proposition states what the work is worth. Its validated proof is what a
          K-Asset approval consumes; the proof is one-shot and internal to the approval.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open a value proposition by rho:id:…"
            className="mono"
            onKeyDown={(event) => {
              if (event.key === "Enter" && isRhoUri(uri.trim())) navigate(`/value/${uri.trim()}`);
            }}
          />
          <button onClick={() => isRhoUri(uri.trim()) && navigate(`/value/${uri.trim()}`)}>
            Open value proposition
          </button>
        </div>
        {values.length === 0 && (
          <Empty>No value propositions in this browser yet. Propose one, or paste a share link.</Empty>
        )}
        <div className="list">
          {values.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/value/${entry.uri}`}>{entry.summary}</Link>
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
