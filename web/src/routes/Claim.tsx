import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Empty, Field, Json, Panel, Uri } from "../components/ui";
import { num, rhoOf, str, useHeight, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { ClaimState } from "../lib/types";

function Comments({ comments }: { comments: unknown[] }) {
  if (comments.length === 0) return <Empty>No comments.</Empty>;
  return (
    <div className="timeline">
      {comments.map((item, index) => {
        const comment = item as Record<string, unknown>;
        return (
          <div className="timeline-row" key={String(comment.id ?? index)}>
            <div className="mono small">{shortId(String(comment.by ?? ""), 8)}</div>
            <div className="mono small">{String(comment.hash ?? "")}</div>
            <div className="muted small">block {String(comment.at ?? "?")}</div>
          </div>
        );
      })}
    </div>
  );
}

export default function Claim() {
  const { uri } = useParams();
  const client = useWallet((state) => state.client);
  const address = useWallet((state) => state.address);
  const height = useHeight();
  const claim = useRead<ClaimState>(
    ["claim", uri],
    client && uri ? () => client.claim_get(uri) : null,
  );
  const action = useAction("claim", uri);
  const [credential, setCredential] = useState("");
  const [verdict, setVerdict] = useState("valid");
  const [quality, setQuality] = useState(["5", "5", "5", "5"]);
  const [characteristics, setCharacteristics] = useState("");
  const [validationNote, setValidationNote] = useState("");
  const [comment, setComment] = useState("");

  if (!uri) return <p className="error">No claim URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (claim.isLoading) return <p className="muted">Reading claim {shortId(uri)}…</p>;
  if (claim.isError) {
    return (
      <Panel title={<h1>Claim</h1>}>
        <p className="error">{String(claim.error)}</p>
        <p className="muted">
          The claim may belong to another Root deployment, or the manifest may be stale.
        </p>
      </Panel>
    );
  }
  const state = claim.data!.data;
  const status = str(state, "status");
  const claimant = str(state, "claimant");
  const kasset = rhoOf(state, "kassetRef");
  const validation = claim.data!.data.validationRef as Record<string, unknown> | undefined;
  const comments = (state.comments as unknown[] | undefined) ?? [];
  const deadline = num(state, "deadlineHeight");
  const commentUntil = num(state, "commentUntilHeight");
  const now = height.data ?? 0;

  const validate = () =>
    action.run(
      "claim validated",
      async () => {
        const qualityMap = {
          completeness: Number(quality[0]),
          correctness: Number(quality[1]),
          traceability: Number(quality[2]),
          fitness: Number(quality[3]),
        };
        const payload = {
          verdict,
          quality: qualityMap,
          credentialUri: credential.trim(),
          characteristicsHash: client.hash_text(characteristics),
          commentHash: client.hash_text(validationNote),
          evidence: [],
        };
        return client.claim_validate(uri, credential.trim(), JSON.stringify(payload));
      },
      [["claim", uri], ["height"]],
    );

  const addComment = () =>
    action.run(
      "claim comment",
      () => client.claim_comment(uri, JSON.stringify({ hash: client.hash_text(comment) })),
      [["claim", uri], ["height"]],
    );

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="claims"
          uri={uri}
          title="Claim"
          status={status}
          meta={claim.data!.read}
          actions={
            kasset ? (
              <Link to={`/kassets/${kasset}`}>open K-Asset</Link>
            ) : null
          }
        />
        <div className="grid two">
          <dl className="kv">
            <dt>claimant</dt>
            <dd><Uri value={claimant} /></dd>
            <dt>discipline</dt>
            <dd>{str(state.work as Record<string, unknown>, "discipline") ?? "—"}</dd>
            <dt>jurisdiction</dt>
            <dd>{str(state.work as Record<string, unknown>, "jurisdiction") ?? "—"}</dd>
            <dt>project</dt>
            <dd>{str(state.work as Record<string, unknown>, "projectRef") ?? "—"}</dd>
            <dt>statement hash</dt>
            <dd className="mono small">{str(state, "statementHash") ?? "—"}</dd>
            <dt>definition hash</dt>
            <dd className="mono small">{str(state, "definitionHash") ?? "—"}</dd>
            <dt>quantity</dt>
            <dd>
              {num(state.quantity, "value") ?? "—"}{" "}
              {str(state.quantity, "unit") ?? ""}
            </dd>
          </dl>
          <dl className="kv">
            <dt>status</dt>
            <dd>{status ?? "—"}</dd>
            <dt>deadline</dt>
            <dd>{deadline ?? "—"} {now > (deadline ?? 0) ? "(passed)" : ""}</dd>
            <dt>comments close</dt>
            <dd>{commentUntil ?? "—"}</dd>
            <dt>value proposition</dt>
            <dd><Uri value={rhoOf(state, "valuePropositionRef")} kind="value" /></dd>
            <dt>K-Asset</dt>
            <dd><Uri value={kasset} kind="kassets" /></dd>
            <dt>validation</dt>
            <dd>{validation ? JSON.stringify(validation) : "—"}</dd>
            <dt>updated at block</dt>
            <dd>{num(state, "updatedAt") ?? "—"}</dd>
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

        {status === "validating" && (
          <div className="action-box">
            <h3>Resume validation</h3>
            <p className="muted small">
              The claim has a validation receipt but has not finalized. Any authenticated
              wallet can resume it; the contract returns the K-Asset URI.
            </p>
            <button
              className="primary"
              disabled={action.busy || !address}
              onClick={() =>
                action.run("claim validation resumed", () => client.claim_resume(uri), [
                  ["claim", uri],
                ])
              }
            >
              Resume
            </button>
          </div>
        )}

        {status === "open" && address && address !== claimant && (
          <div className="action-box">
            <h3>Validate</h3>
            <p className="muted small">
              The signer must hold the credential and match the claim's selection criteria.
              The same URI must appear in the argument and the payload.
            </p>
            <Field label="Credential URI" hint="your Validator credential">
              <input
                value={credential}
                onChange={(event) => setCredential(event.target.value)}
                placeholder="rho:id:…"
                className="mono"
              />
            </Field>
            <div className="grid three">
              <Field label="Verdict">
                <select value={verdict} onChange={(event) => setVerdict(event.target.value)}>
                  <option value="valid">valid</option>
                  <option value="partial">partial</option>
                  <option value="invalid">invalid</option>
                </select>
              </Field>
              {["completeness", "correctness", "traceability", "fitness"].map(
                (label, index) => (
                  <Field key={label} label={label} hint="1–5">
                    <input
                      type="number"
                      min={1}
                      max={5}
                      value={quality[index]}
                      onChange={(event) => {
                        const next = [...quality];
                        next[index] = event.target.value;
                        setQuality(next);
                      }}
                    />
                  </Field>
                ),
              )}
            </div>
            <Field label="Characteristics note" hint="hashed">
              <input
                value={characteristics}
                onChange={(event) => setCharacteristics(event.target.value)}
              />
            </Field>
            <Field label="Validation note" hint="hashed">
              <input
                value={validationNote}
                onChange={(event) => setValidationNote(event.target.value)}
              />
            </Field>
            <button className="primary" onClick={validate} disabled={action.busy || !credential}>
              Validate claim
            </button>
          </div>
        )}

        {status === "open" && address && now <= (commentUntil ?? 0) && (
          <div className="action-box">
            <h3>Comment</h3>
            <Field label="Comment" hint="hashed">
              <input value={comment} onChange={(event) => setComment(event.target.value)} />
            </Field>
            <button onClick={addComment} disabled={action.busy || !comment}>
              Add comment
            </button>
          </div>
        )}

        {status === "open" && address === claimant && (
          <div className="action-box">
            <h3>Claimant actions</h3>
            <div className="row gap wrap">
              <button
                className="ghost"
                disabled={action.busy}
                onClick={() =>
                  action.run("claim withdrawn", () => client.claim_withdraw(uri), [
                    ["claim", uri],
                  ])
                }
              >
                Withdraw
              </button>
              <button
                className="ghost"
                disabled={action.busy || now <= (deadline ?? 0)}
                onClick={() =>
                  action.run("claim expired", () => client.claim_expire(uri), [
                    ["claim", uri],
                  ])
                }
              >
                Expire
              </button>
            </div>
          </div>
        )}
      </Panel>

      <Panel title={<h2>Comments</h2>}>
        <Comments comments={comments} />
      </Panel>

      <Panel title={<h2>Raw state</h2>}>
        <Json value={state} />
      </Panel>
    </div>
  );
}
