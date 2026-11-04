import { useState } from "react";
import { useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import { Empty, Field, Json, Panel, Uri } from "../components/ui";
import { str, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { IdentityState, State } from "../lib/types";

export default function Identity() {
  const params = useParams();
  const { client, address, status } = useWallet();
  const target = params.address ?? address ?? "";
  const own = !!address && target === address;
  const lookup = useRead<State>(
    ["identity-lookup", target],
    client && target ? () => client.identity_lookup(target) : null,
  );
  const identityUri = typeof lookup.data?.data === "string" ? lookup.data.data : undefined;
  const identity = useRead<IdentityState>(
    ["identity-get", identityUri],
    client && identityUri ? () => client.identity_get(identityUri) : null,
  );
  const action = useAction("identity", identityUri);
  const [handle, setHandle] = useState("");
  const [display, setDisplay] = useState("");
  const [org, setOrg] = useState("");
  const [contact, setContact] = useState("");

  const create = () =>
    action.run(
      "identity created",
      () =>
        client!.identity_create(
          JSON.stringify({
            handle,
            displayNameHash: client!.hash_text(display),
            orgHash: client!.hash_text(org),
            contactHash: client!.hash_text(contact),
          }),
        ),
      [["identity-lookup", target]],
    );

  const update = () =>
    action.run(
      "identity updated",
      () =>
        client!.identity_update(
          identityUri!,
          JSON.stringify({
            displayNameHash: client!.hash_text(display),
            orgHash: client!.hash_text(org),
            contactHash: client!.hash_text(contact),
          }),
        ),
      [["identity-get", identityUri]],
    );

  if (!client) return <p className="muted">Booting the wallet…</p>;

  return (
    <div className="stack">
      <Panel title={<h1>{own ? "Your identity" : "Identity"}</h1>}>
        <p className="muted small">
          The identity directory is first-writer-wins per REV address. The handle is fixed
          at creation; only the three hashes can be updated by the owner.
        </p>
        <dl className="kv">
          <dt>address</dt>
          <dd><Uri value={target} /></dd>
          <dt>identity</dt>
          <dd>{identityUri ? <Uri value={identityUri} /> : "not registered"}</dd>
          {identity.data && (
            <>
              <dt>handle</dt>
              <dd>{str(identity.data.data, "handle") ?? "—"}</dd>
              <dt>status</dt>
              <dd>{str(identity.data.data, "status") ?? "—"}</dd>
              <dt>display name hash</dt>
              <dd className="mono small">{str(identity.data.data, "displayNameHash") ?? "—"}</dd>
              <dt>organisation hash</dt>
              <dd className="mono small">{str(identity.data.data, "orgHash") ?? "—"}</dd>
              <dt>contact hash</dt>
              <dd className="mono small">{str(identity.data.data, "contactHash") ?? "—"}</dd>
              <dt>version</dt>
              <dd>{String(identity.data.data.version ?? "—")}</dd>
            </>
          )}
        </dl>
        {lookup.isError && <Empty>No identity for {shortId(target, 10)}.</Empty>}
      </Panel>

      {own && status === "unlocked" && !identityUri && (
        <Panel title={<h2>Create identity</h2>}>
          <Field label="Handle" hint="letters, digits, -_.:">
            <input value={handle} onChange={(event) => setHandle(event.target.value)} />
          </Field>
          <Field label="Display name" hint="hashed">
            <input value={display} onChange={(event) => setDisplay(event.target.value)} />
          </Field>
          <Field label="Organisation" hint="hashed">
            <input value={org} onChange={(event) => setOrg(event.target.value)} />
          </Field>
          <Field label="Contact" hint="hashed">
            <input value={contact} onChange={(event) => setContact(event.target.value)} />
          </Field>
          <DeployResult
            busy={action.busy}
            error={action.error}
            refusal={action.refusal}
            receipt={action.receipt}
          />
          <button className="primary" onClick={create} disabled={action.busy || !handle}>
            Create identity
          </button>
        </Panel>
      )}

      {own && status === "unlocked" && identityUri && (
        <Panel title={<h2>Update profile</h2>}>
          <p className="muted small">
            The contract replaces all three hashes, so every field is sent. The handle stays
            what it was.
          </p>
          <Field label="Display name" hint="hashed">
            <input value={display} onChange={(event) => setDisplay(event.target.value)} />
          </Field>
          <Field label="Organisation" hint="hashed">
            <input value={org} onChange={(event) => setOrg(event.target.value)} />
          </Field>
          <Field label="Contact" hint="hashed">
            <input value={contact} onChange={(event) => setContact(event.target.value)} />
          </Field>
          <DeployResult
            busy={action.busy}
            error={action.error}
            refusal={action.refusal}
            receipt={action.receipt}
          />
          <button onClick={update} disabled={action.busy}>
            Update profile
          </button>
        </Panel>
      )}

      {identity.data && (
        <Panel title={<h2>Raw state</h2>}>
          <Json value={identity.data.data} />
        </Panel>
      )}
    </div>
  );
}
