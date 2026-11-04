import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function Cases() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const cases = (entries.data ?? []).filter((entry) => entry.kind === "case");

  return (
    <div className="stack">
      <Panel title={<h1>Oracle cases</h1>}>
        <p className="muted small">
          Cases are opened by a K-Asset or value-proposition dispute, not from a standalone
          form. The subject passes its private decision capability to the case.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open a case by rho:id:…"
            className="mono"
            onKeyDown={(event) => {
              if (event.key === "Enter" && isRhoUri(uri.trim())) navigate(`/cases/${uri.trim()}`);
            }}
          />
          <button onClick={() => isRhoUri(uri.trim()) && navigate(`/cases/${uri.trim()}`)}>
            Open case
          </button>
        </div>
        {cases.length === 0 && (
          <Empty>No cases in this browser yet. Open a dispute, or paste a share link.</Empty>
        )}
        <div className="list">
          {cases.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/cases/${entry.uri}`}>{entry.summary}</Link>
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
