import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Empty, Field, Json, Panel, Uri } from "../components/ui";
import { num, str, useHeight, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { CaseState } from "../lib/types";

export default function Case() {
  const { uri } = useParams();
  const { client, address } = useWallet();
  const height = useHeight();
  const caseState = useRead<CaseState>(
    ["case", uri],
    client && uri ? () => client.case_get(uri) : null,
  );
  const action = useAction("case", uri);
  const [evidence, setEvidence] = useState("");
  const [outcome, setOutcome] = useState("uphold");
  const [rationale, setRationale] = useState("");
  const [responsible, setResponsible] = useState("");
  const [shareBps, setShareBps] = useState("10000");
  const [basis, setBasis] = useState("");

  if (!uri) return <p className="error">No case URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (caseState.isLoading) return <p className="muted">Reading case {shortId(uri)}…</p>;
  if (caseState.isError) {
    return (
      <Panel title={<h1>Oracle case</h1>}>
        <p className="error">{String(caseState.error)}</p>
      </Panel>
    );
  }

  const state = caseState.data!.data;
  const status = str(state, "status");
  const adjudicator = str(state, "adjudicator");
  const parties = (state.parties as string[] | undefined) ?? [];
  const now = height.data ?? 0;
  const deadline = num(state, "deadlineHeight") ?? 0;
  const isParty = !!address && parties.includes(address);

  const decide = () =>
    action.run(
      "case decided",
      () =>
        client.case_decide(
          uri,
          JSON.stringify({
            outcome,
            rationaleHash: client.hash_text(rationale),
            liability: {
              responsible: responsible.trim() || parties[0] || address || "",
              shareBps: Number(shareBps),
              basisHash: client.hash_text(basis),
            },
          }),
        ),
      [["case", uri], ["height"]],
    );

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="cases"
          uri={uri}
          title="Oracle case"
          status={status}
          meta={caseState.data!.read}
          actions={<Link to="/cases">all cases</Link>}
        />
        <div className="grid two">
          <dl className="kv">
            <dt>kind</dt>
            <dd>{str(state, "kind") ?? "—"}</dd>
            <dt>subject</dt>
            <dd>{JSON.stringify(state.subjectRef ?? "—")}</dd>
            <dt>opened by</dt>
            <dd><Uri value={str(state, "openedBy")} /></dd>
            <dt>parties</dt>
            <dd>
              {parties.length === 0
                ? "—"
                : parties.map((party) => (
                    <div key={party}>
                      <Uri value={party} />
                    </div>
                  ))}
            </dd>
            <dt>grounds hash</dt>
            <dd className="mono small">{str(state, "groundsHash") ?? "—"}</dd>
          </dl>
          <dl className="kv">
            <dt>adjudicator</dt>
            <dd><Uri value={adjudicator} /></dd>
            <dt>adjudicator credential</dt>
            <dd><Uri value={str(state, "adjudicatorCredentialUri")} kind="credentials" /></dd>
            <dt>requirement</dt>
            <dd>{JSON.stringify(state.requirement ?? "—")}</dd>
            <dt>deadline</dt>
            <dd>{deadline || "—"} {now > deadline ? "(passed)" : ""}</dd>
            <dt>decision</dt>
            <dd>{JSON.stringify(state.decision ?? "—")}</dd>
            <dt>execution</dt>
            <dd>{JSON.stringify(state.execution ?? "—")}</dd>
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

        {status === "open" && (isParty || address === adjudicator) && (
          <div className="action-box">
            <h3>Add evidence</h3>
            <Field label="Evidence" hint="hashed">
              <input value={evidence} onChange={(event) => setEvidence(event.target.value)} />
            </Field>
            <button
              disabled={action.busy || !evidence}
              onClick={() =>
                action.run(
                  "case evidence added",
                  () =>
                    client.case_evidence(uri, JSON.stringify({ hash: client.hash_text(evidence) })),
                  [["case", uri]],
                )
              }
            >
              Add evidence
            </button>
          </div>
        )}

        {status === "open" && address === adjudicator && (
          <div className="action-box">
            <h3>Decide</h3>
            <p className="muted small">
              The signer must be the stored adjudicator and must prove the named credential
              against the case requirement.
            </p>
            <div className="grid three">
              <Field label="Outcome">
                <select value={outcome} onChange={(event) => setOutcome(event.target.value)}>
                  <option value="uphold">uphold</option>
                  <option value="revoke">revoke</option>
                  <option value="partial">partial</option>
                </select>
              </Field>
              <Field label="Liability holder">
                <input
                  value={responsible}
                  onChange={(event) => setResponsible(event.target.value)}
                  placeholder={parties[0] ?? address ?? ""}
                  className="mono"
                />
              </Field>
              <Field label="Share (bps)">
                <input
                  type="number"
                  min={0}
                  max={10000}
                  value={shareBps}
                  onChange={(event) => setShareBps(event.target.value)}
                />
              </Field>
            </div>
            <Field label="Liability basis" hint="hashed">
              <input value={basis} onChange={(event) => setBasis(event.target.value)} />
            </Field>
            <Field label="Rationale" hint="hashed">
              <input value={rationale} onChange={(event) => setRationale(event.target.value)} />
            </Field>
            <button className="primary" disabled={action.busy || !rationale} onClick={decide}>
              Decide case
            </button>
          </div>
        )}

        {status === "decided" && (
          <div className="action-box">
            <h3>Execute</h3>
            <p className="muted small">
              Execution is permissionless and outcome-blind: the case applies its stored
              decision to the subject.
            </p>
            <button
              className="primary"
              disabled={action.busy || !address}
              onClick={() =>
                action.run("decision executed", () => client.case_execute(uri), [
                  ["case", uri],
                  ["height"],
                ])
              }
            >
              Execute decision
            </button>
          </div>
        )}

        {status === "open" && now > deadline && (
          <div className="action-box">
            <h3>Expire</h3>
            <button
              className="ghost"
              disabled={action.busy || !address}
              onClick={() =>
                action.run("case expired", () => client.case_expire(uri), [["case", uri]])
              }
            >
              Expire case
            </button>
          </div>
        )}

        {(status === "executed" || status === "expired") && (
          <div className="action-box">
            <h3>Close</h3>
            <button
              className="ghost"
              disabled={action.busy || !address}
              onClick={() =>
                action.run("case closed", () => client.case_close(uri), [["case", uri]])
              }
            >
              Close case
            </button>
          </div>
        )}
      </Panel>

      <Panel title={<h2>Evidence</h2>}>
        <Json value={state.evidence ?? []} />
      </Panel>
      <Panel title={<h2>Raw state</h2>}>
        <Json value={state} />
      </Panel>
    </div>
  );
}
