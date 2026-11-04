import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { parseRead } from "../lib/api";
import { loadCatalogue } from "../lib/catalogue";
import { str, useHeight, useRead } from "../lib/entity";
import { isRhoUri } from "../lib/network";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import type { CatalogueEntry, IdentityState, State } from "../lib/types";
import type { Rgen } from "../wasm";
import { Empty, Panel, StatusPill, Uri } from "../components/ui";

const KIND_ROUTE: Record<string, string> = {
  claim: "claims",
  kasset: "kassets",
  credential: "credentials",
  value: "value",
  case: "cases",
  provenance: "provenance",
};

const KIND_READ: Record<string, string> = {
  claim: "claim_get",
  kasset: "kasset_get",
  credential: "credential_get",
  value: "vp_get",
  case: "case_get",
  provenance: "provenance_get",
  identity: "identity_get",
};

async function readEntity(client: Rgen, kind: string, uri: string) {
  const method = KIND_READ[kind];
  if (!method) throw new Error(`unknown entity kind ${kind}`);
  const fn = (client as unknown as Record<string, (value: string) => Promise<string>>)[method];
  if (!fn) throw new Error(`the client has no ${method}`);
  return parseRead<State>(await fn.call(client, uri));
}

function CatalogueCard({ entry }: { entry: CatalogueEntry }) {
  const client = useWallet((state) => state.client);
  const query = useQuery({
    queryKey: ["catalogue", entry.kind, entry.uri],
    enabled: !!client,
    queryFn: async () => readEntity(client!, entry.kind, entry.uri),
  });
  const path = KIND_ROUTE[entry.kind];
  const status =
    str(query.data?.data, "status") ??
    (entry.kind === "provenance" ? "append-only" : query.isError ? "missing" : undefined);
  return (
    <article className="card">
      <div className="card-head">
        <strong>{entry.label}</strong>
        <StatusPill status={status} />
      </div>
      <span className="muted small">{entry.kind}</span>
      <span className="mono small" title={entry.uri}>
        {shortId(entry.uri, 10)}
      </span>
      {entry.detail && <span className="muted small">{entry.detail}</span>}
      {query.isError && <span className="small error">{String(query.error)}</span>}
      {path && (
        <Link className="small" to={`/${path}/${entry.uri}`}>
          open
        </Link>
      )}
      {!path && str(query.data?.data, "subject") && (
        <Link className="small" to={`/identity/${str(query.data?.data, "subject")}`}>
          open identity
        </Link>
      )}
    </article>
  );
}

export default function Overview() {
  const navigate = useNavigate();
  const { client, address, readiness, profile } = useWallet();
  const [kind, setKind] = useState("claim");
  const [uri, setUri] = useState("");
  const [error, setError] = useState<string | null>(null);
  const height = useHeight();
  const identity = useRead<IdentityState>(
    ["identity", address],
    client && address ? () => client.identity_lookup(address) : null,
  );
  const catalogue = useQuery({
    queryKey: ["catalogue", readiness.networkId, readiness.root],
    enabled: readiness.state === "ready",
    queryFn: () => loadCatalogue(readiness.networkId, readiness.root),
  });

  const open = () => {
    setError(null);
    if (!isRhoUri(uri.trim())) {
      setError("paste a rho:id: registry URI");
      return;
    }
    const path = KIND_ROUTE[kind];
    if (!path) {
      setError(`unknown kind ${kind}`);
      return;
    }
    navigate(`/${path}/${uri.trim()}`);
  };

  return (
    <div className="stack">
      <Panel title={<h1>r-gen</h1>}>
        <p className="muted">
          Claims are the quantity of engineering work; validations are its quality. A validated
          claim creates exactly one K-Asset. Credentials, adjudication and provenance stay with
          the asset. Everything here is read from, and written to, the deployed contracts.
        </p>
        <div className="grid three">
          <div className="stat">
            <span>Network</span>
            <strong>{profile.name}</strong>
            {profile.name === "testnet" && readiness.networkId && (
              <span className="muted small">{readiness.networkId}</span>
            )}
          </div>
          <div className="stat">
            <span>Finalized height</span>
            <strong>{height.data?.toLocaleString() ?? "…"}</strong>
          </div>
          <div className="stat">
            <span>Root keys resolved</span>
            <strong>{Object.keys(readiness.components ?? {}).length} / 9</strong>
          </div>
        </div>
      </Panel>

      <Panel
        title={<h2>Your identity</h2>}
        actions={<Link to="/identity">identity page</Link>}
      >
        {!address && <Empty>Unlock a wallet to see its identity.</Empty>}
        {address && identity.isLoading && <p className="muted">looking up {shortId(address, 10)}…</p>}
        {address && identity.isError && (
          <p className="muted">
            No identity registered for this address.{" "}
            <Link to="/identity">Create one</Link>.
          </p>
        )}
        {identity.data && (
          <p>
            <strong>{str(identity.data.data, "handle") ?? "unnamed"}</strong>{" "}
            <StatusPill status={str(identity.data.data, "status")} />{" "}
            <Uri value={str(identity.data.data, "uri")} />
          </p>
        )}
      </Panel>

      <Panel title={<h2>Open an entity</h2>}>
        <p className="muted small">
          There is no indexer. A URI is the share link: the entity lives at that registry name.
        </p>
        <div className="paste-row">
          <select value={kind} onChange={(event) => setKind(event.target.value)}>
            <option value="claim">claim</option>
            <option value="kasset">K-Asset</option>
            <option value="credential">credential</option>
            <option value="value">value proposition</option>
            <option value="case">oracle case</option>
            <option value="provenance">provenance</option>
          </select>
          <input
            value={uri}
            onChange={(event) => setUri(event.target.value)}
            placeholder="rho:id:…"
            className="mono"
            onKeyDown={(event) => event.key === "Enter" && open()}
          />
          <button onClick={open}>Open</button>
        </div>
        {error && <p className="error">{error}</p>}
      </Panel>

      <Panel
        title={<h2>Seeded bridge inspection</h2>}
        actions={<span className="muted small">real URIs, live status</span>}
      >
        {catalogue.isLoading && <p className="muted">loading catalogue…</p>}
        {catalogue.isError && <p className="error">{String(catalogue.error)}</p>}
        {catalogue.data && catalogue.data.length === 0 && (
          <Empty>
            No catalogue. Run <code>make demo-seed</code>, then <code>make sync-manifest</code>.
          </Empty>
        )}
        {catalogue.data && catalogue.data.length > 0 && (
          <div className="catalog">
            {catalogue.data.map((entry) => (
              <CatalogueCard key={`${entry.kind}:${entry.uri}`} entry={entry} />
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
