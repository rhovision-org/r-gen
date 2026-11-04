import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Empty, Field, Json, Panel, Uri } from "../components/ui";
import { num, rhoOf, str, useHeight, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { State, ValuePropositionState } from "../lib/types";

export default function ValueProposition() {
  const { uri } = useParams();
  const { client, address } = useWallet();
  const height = useHeight();
  const value = useRead<ValuePropositionState>(
    ["value", uri],
    client && uri ? () => client.vp_get(uri) : null,
  );
  const comments = useRead<State>(
    ["value-comments", uri],
    client && uri ? () => client.vp_comments(uri) : null,
  );
  const revocation = useRead<State>(
    ["value-revocation", uri],
    client && uri ? () => client.vp_revocation(uri) : null,
  );
  const action = useAction("value", uri);
  const [credential, setCredential] = useState("");
  const [notes, setNotes] = useState("");
  const [comment, setComment] = useState("");
  const [grounds, setGrounds] = useState("");
  const [adjudicator, setAdjudicator] = useState("");
  const [adjudicatorCredential, setAdjudicatorCredential] = useState("");
  const [deadline, setDeadline] = useState("");

  if (!uri) return <p className="error">No value proposition URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (value.isLoading) return <p className="muted">Reading value proposition {shortId(uri)}…</p>;
  if (value.isError) {
    return (
      <Panel title={<h1>Value proposition</h1>}>
        <p className="error">{String(value.error)}</p>
      </Panel>
    );
  }

  const state = value.data!.data;
  const status = str(state, "status");
  const proposer = str(state, "proposer");
  const validator = str(state, "validator");
  const now = height.data ?? 0;
  const commentList = (comments.data?.data as unknown as unknown[] | undefined) ?? [];

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="value"
          uri={uri}
          title="Value proposition"
          status={status}
          meta={value.data!.read}
          actions={
            rhoOf(state, "dispute") ? (
              <Link to={`/cases/${rhoOf(state, "dispute")}`}>open case</Link>
            ) : null
          }
        />
        <div className="grid two">
          <dl className="kv">
            <dt>proposer</dt>
            <dd><Uri value={proposer} /></dd>
            <dt>validator</dt>
            <dd><Uri value={validator} /></dd>
            <dt>subject ref</dt>
            <dd>{JSON.stringify(state.subjectRef ?? "—")}</dd>
            <dt>statement hash</dt>
            <dd className="mono small">{str(state, "statementHash") ?? "—"}</dd>
            <dt>terms hash</dt>
            <dd className="mono small">{str(state, "termsHash") ?? "—"}</dd>
            <dt>value model hash</dt>
            <dd className="mono small">{str(state, "valueModelHash") ?? "—"}</dd>
          </dl>
          <dl className="kv">
            <dt>status</dt>
            <dd>{status ?? "—"}</dd>
            <dt>deadline</dt>
            <dd>{num(state, "deadlineHeight") ?? "—"} {now > (num(state, "deadlineHeight") ?? 0) ? "(passed)" : ""}</dd>
            <dt>beneficiaries</dt>
            <dd>{JSON.stringify(state.beneficiaries ?? [])}</dd>
            <dt>validation</dt>
            <dd>{JSON.stringify(state.validation ?? "—")}</dd>
            <dt>dispute</dt>
            <dd><Uri value={rhoOf(state, "dispute")} kind="cases" /></dd>
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

        {status === "proposed" && address && address !== proposer && (
          <div className="action-box">
            <h3>Validate</h3>
            <Field label="Validator credential URI">
              <input
                value={credential}
                onChange={(event) => setCredential(event.target.value)}
                className="mono"
                placeholder="rho:id:…"
              />
            </Field>
            <Field label="Notes" hint="hashed">
              <input value={notes} onChange={(event) => setNotes(event.target.value)} />
            </Field>
            <button
              className="primary"
              disabled={action.busy || !credential}
              onClick={() =>
                action.run(
                  "value proposition validated",
                  () =>
                    client.vp_validate(
                      uri,
                      credential.trim(),
                      JSON.stringify({
                        credentialUri: credential.trim(),
                        notesHash: client.hash_text(notes),
                      }),
                    ),
                  [["value", uri], ["height"]],
                )
              }
            >
              Validate
            </button>
          </div>
        )}

        {status === "proposed" && address && now <= (num(state, "deadlineHeight") ?? 0) && (
          <div className="action-box">
            <h3>Comment</h3>
            <Field label="Comment" hint="hashed">
              <input value={comment} onChange={(event) => setComment(event.target.value)} />
            </Field>
            <button
              disabled={action.busy || !comment}
              onClick={() =>
                action.run(
                  "value proposition comment",
                  () => client.vp_comment(uri, JSON.stringify({ hash: client.hash_text(comment) })),
                  [["value", uri], ["value-comments", uri]],
                )
              }
            >
              Add comment
            </button>
          </div>
        )}

        {status === "proposed" && address === proposer && (
          <div className="action-box">
            <h3>Withdraw</h3>
            <button
              className="ghost"
              disabled={action.busy}
              onClick={() =>
                action.run("value proposition withdrawn", () => client.vp_withdraw(uri), [
                  ["value", uri],
                ])
              }
            >
              Withdraw proposal
            </button>
          </div>
        )}

        {(status === "proposed" || status === "validated") &&
          (address === proposer || address === validator) && (
            <div className="action-box">
              <h3>Open dispute</h3>
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
                onClick={() =>
                  action.run(
                    "value proposition dispute opened",
                    () =>
                      client.vp_open_dispute(
                        uri,
                        JSON.stringify({
                          kind: "dispute",
                          groundsHash: client.hash_text(grounds),
                          adjudicator: adjudicator.trim(),
                          adjudicatorCredentialUri: adjudicatorCredential.trim(),
                          deadlineHeight: Number(deadline || now + 1000),
                        }),
                      ),
                    [["value", uri], ["height"]],
                  )
                }
              >
                Open case
              </button>
            </div>
          )}
      </Panel>

      <Panel title={<h2>Comments</h2>}>
        {commentList.length === 0 ? (
          <Empty>No comments.</Empty>
        ) : (
          <div className="timeline">
            {commentList.map((item, index) => (
              <div className="timeline-row" key={index}>
                <div className="mono small">{JSON.stringify(item)}</div>
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
