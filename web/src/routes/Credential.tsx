import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Field, Json, Panel, Uri } from "../components/ui";
import { message, parseRead } from "../lib/api";
import { num, str, useHeight, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { CredentialState } from "../lib/types";

export default function Credential() {
  const { uri } = useParams();
  const { client, address } = useWallet();
  const height = useHeight();
  const credential = useRead<CredentialState>(
    ["credential", uri],
    client && uri ? () => client.credential_get(uri) : null,
  );
  const action = useAction("credential", uri);
  const [reason, setReason] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [evidence, setEvidence] = useState("");
  const [attestation, setAttestation] = useState("");
  const [check, setCheck] = useState<string | null>(null);
  const [checkError, setCheckError] = useState<string | null>(null);

  if (!uri) return <p className="error">No credential URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (credential.isLoading) return <p className="muted">Reading credential {shortId(uri)}…</p>;
  if (credential.isError) {
    return (
      <Panel title={<h1>Credential</h1>}>
        <p className="error">{String(credential.error)}</p>
      </Panel>
    );
  }

  const state = credential.data!.data;
  const status = str(state, "status");
  const subject = str(state, "subject");

  const checkCredential = async () => {
    setCheck(null);
    setCheckError(null);
    try {
      const requirement = {
        ctype: str(state, "ctype") ?? "",
        discipline: str(state, "discipline") ?? "",
        jurisdiction: str(state, "jurisdiction") ?? "",
        role: str(state, "role") ?? "",
        minLevel: num(state, "level") ?? 1,
      };
      const envelope = parseRead<unknown>(
        await client.credential_check(
          uri,
          address ?? "",
          JSON.stringify(requirement),
          BigInt(height.data ?? 0),
        ),
      );
      setCheck(JSON.stringify(envelope.data));
    } catch (cause) {
      setCheckError(message(cause));
    }
  };

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="credentials"
          uri={uri}
          title={str(state, "ctype") ?? "Credential"}
          status={status}
          meta={credential.data!.read}
        />
        <div className="grid two">
          <dl className="kv">
            <dt>subject</dt>
            <dd><Uri value={subject} /></dd>
            <dt>issuer</dt>
            <dd><Uri value={str(state, "issuer")} /></dd>
            <dt>issuer cell</dt>
            <dd><Uri value={str(state, "issuerUri")} /></dd>
            <dt>type</dt>
            <dd>{str(state, "ctype") ?? "—"}</dd>
            <dt>discipline</dt>
            <dd>{str(state, "discipline") ?? "—"}</dd>
            <dt>jurisdiction</dt>
            <dd>{str(state, "jurisdiction") ?? "—"}</dd>
          </dl>
          <dl className="kv">
            <dt>role</dt>
            <dd>{str(state, "role") ?? "—"}</dd>
            <dt>level</dt>
            <dd>{num(state, "level") ?? "—"}</dd>
            <dt>issued at</dt>
            <dd>{num(state, "issuedAt") ?? "—"}</dd>
            <dt>expires at</dt>
            <dd>{num(state, "expiresAt") ?? "—"}</dd>
            <dt>revoked at</dt>
            <dd>{num(state, "revokedAt") ?? "—"}</dd>
            <dt>reason</dt>
            <dd>{str(state, "reason") ?? "—"}</dd>
          </dl>
        </div>
      </Panel>

      <Panel title={<h2>Actions</h2>}>
        <DeployResult
          busy={action.busy}
          error={action.error}
          refusal={action.refusal}
          receipt={action.receipt}
        />

        <div className="action-box">
          <h3>Check (free read)</h3>
          <p className="muted small">
            This is the advisory predicate. It takes the caller string as an argument; it
            does not authorise anything on its own.
          </p>
          <button className="ghost" disabled={!address} onClick={checkCredential}>
            Check with this wallet
          </button>
          {check && <p className="mono small">{check}</p>}
          {checkError && <p className="error">{checkError}</p>}
        </div>

        <div className="action-box">
          <h3>Revoke</h3>
          <Field label="Reason">
            <input value={reason} onChange={(event) => setReason(event.target.value)} />
          </Field>
          <button
            className="ghost"
            disabled={action.busy || !address}
            onClick={() =>
              action.run("credential revoked", () => client.credential_revoke(uri, reason), [
                ["credential", uri],
              ])
            }
          >
            Revoke
          </button>
        </div>

        <div className="action-box">
          <h3>Renew (issuer only)</h3>
          <Field label="New expiry height">
            <input
              type="number"
              value={expiresAt}
              onChange={(event) => setExpiresAt(event.target.value)}
            />
          </Field>
          <Field label="Evidence" hint="hashed">
            <input value={evidence} onChange={(event) => setEvidence(event.target.value)} />
          </Field>
          <button
            disabled={action.busy || !address || !expiresAt}
            onClick={() =>
              action.run(
                "credential renewed",
                () =>
                  client.credential_renew(
                    uri,
                    BigInt(expiresAt),
                    client.hash_text(evidence),
                  ),
                [["credential", uri]],
              )
            }
          >
            Renew
          </button>
        </div>

        <div className="action-box">
          <h3>Attest (anyone but the subject)</h3>
          <Field label="Attestation" hint="hashed">
            <input
              value={attestation}
              onChange={(event) => setAttestation(event.target.value)}
            />
          </Field>
          <button
            disabled={action.busy || !address || !attestation}
            onClick={() =>
              action.run(
                "credential attested",
                () => client.credential_attest(uri, client.hash_text(attestation)),
                [["credential", uri]],
              )
            }
          >
            Attest
          </button>
        </div>
      </Panel>

      <Panel title={<h2>Attestations and renewals</h2>}>
        <dl className="kv">
          <dt>attestations</dt>
          <dd>{JSON.stringify(state.attestations ?? [])}</dd>
          <dt>renewals</dt>
          <dd>{JSON.stringify(state.renewals ?? [])}</dd>
        </dl>
        {subject && <Link to={`/identity/${subject}`}>subject identity</Link>}
      </Panel>

      <Panel title={<h2>Raw state</h2>}>
        <Json value={state} />
      </Panel>
    </div>
  );
}
