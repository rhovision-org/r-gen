import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Empty, Field, Json, Panel, Uri } from "../components/ui";
import { num, rhoOf, str, useHeight, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { KAssetState, State } from "../lib/types";

export default function KAsset() {
  const { uri } = useParams();
  const client = useWallet((state) => state.client);
  const address = useWallet((state) => state.address);
  const height = useHeight();
  const kasset = useRead<KAssetState>(
    ["kasset", uri],
    client && uri ? () => client.kasset_get(uri) : null,
  );
  const children = useRead<State>(["kasset-children", uri], client && uri ? () => client.kasset_children(uri) : null);
  const revocation = useRead<State>(["kasset-revocation", uri], client && uri ? () => client.kasset_revocation(uri) : null);
  const action = useAction("kasset", uri);

  const [credential, setCredential] = useState("");
  const [conditions, setConditions] = useState("");
  const [responsible, setResponsible] = useState("");
  const [shareBps, setShareBps] = useState("10000");
  const [basis, setBasis] = useState("");
  const [grounds, setGrounds] = useState("");
  const [adjudicator, setAdjudicator] = useState("");
  const [adjudicatorCredential, setAdjudicatorCredential] = useState("");
  const [deadline, setDeadline] = useState("");
  const [childRefs, setChildRefs] = useState("");

  if (!uri) return <p className="error">No K-Asset URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (kasset.isLoading) return <p className="muted">Reading K-Asset {shortId(uri)}…</p>;
  if (kasset.isError) {
    return (
      <Panel title={<h1>K-Asset</h1>}>
        <p className="error">{String(kasset.error)}</p>
      </Panel>
    );
  }

  const state = kasset.data!.data;
  const status = str(state, "status");
  const claimant = str(state, "claimant");
  const validator = str(state, "validator");
  const now = height.data ?? 0;
  const approval = state.approval as Record<string, unknown> | undefined;
  const dispute = state.dispute as Record<string, unknown> | undefined;
  const childList = (children.data?.data as unknown as unknown[] | undefined) ?? [];

  const approvalPayload = (decision: "approve" | "reject") => ({
    decision,
    conditionsHash: client.hash_text(conditions),
    credentialUri: credential.trim(),
    liability: {
      responsible: responsible.trim() || address || "",
      shareBps: Number(shareBps),
      basisHash: client.hash_text(basis),
    },
  });

  const approve = (decision: "approve" | "reject") =>
    action.run(
      decision === "approve" ? "K-Asset approved" : "K-Asset rejected",
      () =>
        decision === "approve"
          ? client.kasset_approve(
              uri,
              credential.trim(),
              JSON.stringify(approvalPayload(decision)),
            )
          : client.kasset_reject(
              uri,
              credential.trim(),
              JSON.stringify(approvalPayload(decision)),
            ),
      [["kasset", uri], ["height"]],
    );

  const openDispute = () =>
    action.run(
      "dispute opened",
      () =>
        client.kasset_open_dispute(
          uri,
          JSON.stringify({
            kind: "dispute",
            groundsHash: client.hash_text(grounds),
            adjudicator: adjudicator.trim(),
            adjudicatorCredentialUri: adjudicatorCredential.trim(),
            deadlineHeight: Number(deadline || now + 1000),
          }),
        ),
      [["kasset", uri], ["height"]],
    );

  const nest = () =>
    action.run(
      "child K-Assets nested",
      () => client.kasset_nest(uri, JSON.stringify(JSON.parse(childRefs))),
      [["kasset", uri], ["kasset-children", uri]],
    );

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="kassets"
          uri={uri}
          title="K-Asset"
          status={status}
          meta={kasset.data!.read}
          actions={
            <>
              <Link to={`/claims/${rhoOf(state, "claimRef") ?? ""}`}>open claim</Link>
              {rhoOf(state, "valuePropositionRef") && (
                <Link to={`/value/${rhoOf(state, "valuePropositionRef")}`}>value proposition</Link>
              )}
            </>
          }
        />
        <div className="grid two">
          <dl className="kv">
            <dt>claim</dt>
            <dd><Uri value={rhoOf(state, "claimRef")} kind="claims" /></dd>
            <dt>value proposition</dt>
            <dd><Uri value={rhoOf(state, "valuePropositionRef")} kind="value" /></dd>
            <dt>claimant</dt>
            <dd><Uri value={claimant} /></dd>
            <dt>validator</dt>
            <dd><Uri value={validator} /></dd>
            <dt>verdict</dt>
            <dd>{str(state, "verdict") ?? "—"}</dd>
            <dt>quality</dt>
            <dd>{JSON.stringify(state.quality ?? "—")}</dd>
          </dl>
          <dl className="kv">
            <dt>status</dt>
            <dd>{status ?? "—"}</dd>
            <dt>approver</dt>
            <dd><Uri value={str(state, "approver")} /></dd>
            <dt>approved at</dt>
            <dd>{num(state, "approvedAt") ?? "—"}</dd>
            <dt>approval</dt>
            <dd>{approval ? JSON.stringify(approval) : "—"}</dd>
            <dt>dispute</dt>
            <dd><Uri value={str(dispute, "uri")} kind="cases" /></dd>
            <dt>revocation</dt>
            <dd>{revocation.data ? JSON.stringify(revocation.data.data) : "—"}</dd>
          </dl>
        </div>
      </Panel>

      <Panel title={<h2>Actions</h2>}>
        {!address && <Empty>Connect a wallet to see the lifecycle actions.</Empty>}
        <DeployResult
          busy={action.busy}
          error={action.error}
          refusal={action.refusal}
          receipt={action.receipt}
        />

        {(status === "validated" || status === "conditional") &&
          address &&
          address !== claimant &&
          address !== validator && (
          <div className="action-box">
            <h3>Approve or reject</h3>
            <p className="muted small">
              The signer must hold an active Approver credential for this discipline and
              jurisdiction. If the K-Asset names a value proposition, the contract also
              requires it to be validated at this height.
            </p>
            <Field label="Approver credential URI">
              <input
                value={credential}
                onChange={(event) => setCredential(event.target.value)}
                placeholder="rho:id:…"
                className="mono"
              />
            </Field>
            <Field label="Conditions note" hint="hashed">
              <input value={conditions} onChange={(event) => setConditions(event.target.value)} />
            </Field>
            <div className="grid three">
              <Field label="Liability holder">
                <input
                  value={responsible}
                  onChange={(event) => setResponsible(event.target.value)}
                  placeholder={address ?? "REV address"}
                  className="mono"
                />
              </Field>
              <Field label="Share (bps)" hint="0–10000">
                <input
                  type="number"
                  min={0}
                  max={10000}
                  value={shareBps}
                  onChange={(event) => setShareBps(event.target.value)}
                />
              </Field>
              <Field label="Liability basis" hint="hashed">
                <input value={basis} onChange={(event) => setBasis(event.target.value)} />
              </Field>
            </div>
            <div className="row gap wrap">
              <button className="primary" disabled={action.busy || !credential} onClick={() => approve("approve")}>
                Approve
              </button>
              <button className="ghost" disabled={action.busy || !credential} onClick={() => approve("reject")}>
                Reject
              </button>
            </div>
          </div>
        )}

        {status === "approved" && address === claimant && (
          <div className="action-box">
            <h3>Nest child K-Assets</h3>
            <p className="muted small">
              Children must be approved earlier, share the discipline and jurisdiction, and
              be sorted by <code>approvedAt</code>. At most 32 per batch.
            </p>
            <Field label="Child refs (JSON)">
              <textarea
                rows={4}
                value={childRefs}
                onChange={(event) => setChildRefs(event.target.value)}
                placeholder='[{"id":"rho:id:…","uri":"rho:id:…"}]'
              />
            </Field>
            <button disabled={action.busy || !childRefs} onClick={nest}>
              Nest children
            </button>
          </div>
        )}

        {status === "approved" && (address === claimant || address === validator) && (
          <div className="action-box">
            <h3>Open dispute</h3>
            <p className="muted small">
              The contract fills the opener, parties and requirement. Name an adjudicator and
              the credential the adjudicator will prove.
            </p>
            <Field label="Grounds" hint="hashed">
              <input value={grounds} onChange={(event) => setGrounds(event.target.value)} />
            </Field>
            <Field label="Adjudicator REV address">
              <input
                value={adjudicator}
                onChange={(event) => setAdjudicator(event.target.value)}
                className="mono"
              />
            </Field>
            <Field label="Adjudicator credential URI">
              <input
                value={adjudicatorCredential}
                onChange={(event) => setAdjudicatorCredential(event.target.value)}
                className="mono"
              />
            </Field>
            <Field label="Deadline height" hint={`current ${now}`}>
              <input
                type="number"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
                placeholder={String(now + 1000)}
              />
            </Field>
            <button
              className="primary"
              disabled={action.busy || !adjudicator || !adjudicatorCredential}
              onClick={openDispute}
            >
              Open case
            </button>
          </div>
        )}

        {status !== "validated" && status !== "conditional" && status !== "approved" && (
          <Empty>No lifecycle action is available in status “{status}”.</Empty>
        )}
      </Panel>

      <Panel title={<h2>Children</h2>}>
        {childList.length === 0 ? (
          <Empty>No nested children.</Empty>
        ) : (
          <div className="list">
            {childList.map((child, index) => (
              <div className="list-row" key={index}>
                <Uri value={typeof child === "string" ? child : str(child, "uri")} kind="kassets" />
              </div>
            ))}
          </div>
        )}
      </Panel>

      <Panel title={<h2>Raw state</h2>}>
        <Json value={state} />
      </Panel>
    </div>
  );
}
