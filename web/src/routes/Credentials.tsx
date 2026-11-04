import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import * as journal from "../lib/journal";
import { isRhoUri } from "../lib/network";
import { relative } from "../lib/format";
import { Empty, Panel, StatusPill } from "../components/ui";

export default function Credentials() {
  const navigate = useNavigate();
  const [uri, setUri] = useState("");
  const entries = useQuery({ queryKey: ["journal"], queryFn: journal.list, staleTime: 0 });
  const credentials = (entries.data ?? []).filter((entry) => entry.kind === "credential");

  return (
    <div className="stack">
      <Panel
        title={<h1>Credentials</h1>}
        actions={<Link to="/credentials/issue">Issue a credential</Link>}
      >
        <p className="muted small">
          Only the genesis issuer can issue. A credential is proven by its subject at the
          moment of use; revocation is not retroactive for a proof already taken.
        </p>
        <div className="paste-row">
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="open a credential by rho:id:…"
            className="mono"
            onKeyDown={(event) => {
              if (event.key === "Enter" && isRhoUri(uri.trim())) {
                navigate(`/credentials/${uri.trim()}`);
              }
            }}
          />
          <button
            onClick={() =>
              isRhoUri(uri.trim()) && navigate(`/credentials/${uri.trim()}`)
            }
          >
            Open credential
          </button>
        </div>
        {credentials.length === 0 && (
          <Empty>No credentials in this browser yet. Issue one, or paste a share link.</Empty>
        )}
        <div className="list">
          {credentials.map((entry) => (
            <div className="list-row" key={entry.id}>
              <div>
                {entry.uri ? (
                  <Link to={`/credentials/${entry.uri}`}>{entry.summary}</Link>
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
