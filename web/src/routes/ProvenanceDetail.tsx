import { useState } from "react";
import { useParams } from "react-router-dom";
import DeployResult from "../components/DeployResult";
import EntityHeader from "../components/EntityHeader";
import { Field, Json, Panel, Uri } from "../components/ui";
import { message, parseRead } from "../lib/api";
import { str, useRead } from "../lib/entity";
import { shortId } from "../lib/format";
import { useWallet } from "../lib/store";
import { useAction } from "../lib/useAction";
import type { ProvenanceState, State } from "../lib/types";

export default function ProvenanceDetail() {
  const { uri } = useParams();
  const { client, address } = useWallet();
  const provenance = useRead<ProvenanceState>(
    ["provenance", uri],
    client && uri ? () => client.provenance_get(uri) : null,
  );
  const anchors = useRead<State>(
    ["provenance-anchors", uri],
    client && uri ? () => client.provenance_anchors(uri) : null,
  );
  const action = useAction("provenance", uri);
  const [kind, setKind] = useState("inspection-report");
  const [documentText, setDocumentText] = useState("");
  const [parentHash, setParentHash] = useState("");
  const [comment, setComment] = useState("");
  const [verifyHash, setVerifyHash] = useState("");
  const [verified, setVerified] = useState<string | null>(null);
  const [verifyError, setVerifyError] = useState<string | null>(null);

  if (!uri) return <p className="error">No provenance URI.</p>;
  if (!client) return <p className="muted">Booting the wallet…</p>;
  if (provenance.isLoading) return <p className="muted">Reading provenance {shortId(uri)}…</p>;
  if (provenance.isError) {
    return (
      <Panel title={<h1>Provenance</h1>}>
        <p className="error">{String(provenance.error)}</p>
      </Panel>
    );
  }

  const state = provenance.data!.data;
  const writers = (state.writers as string[] | undefined) ?? [];
  const anchorList = (anchors.data?.data as unknown as unknown[] | undefined) ?? [];

  const verify = async () => {
    setVerified(null);
    setVerifyError(null);
    try {
      const envelope = parseRead<unknown>(await client.provenance_verify(uri, verifyHash));
      setVerified(JSON.stringify(envelope.data));
    } catch (cause) {
      setVerifyError(message(cause));
    }
  };

  return (
    <div className="stack">
      <Panel>
        <EntityHeader
          kind="provenance"
          uri={uri}
          title="Provenance"
          status="append-only"
          meta={provenance.data!.read}
        />
        <dl className="kv">
          <dt>asset ref</dt>
          <dd><Uri value={str(state.assetRef as Record<string, unknown>, "uri")} /></dd>
          <dt>writers</dt>
          <dd>
            {writers.length === 0
              ? "—"
              : writers.map((writer) => (
                  <div key={writer}>
                    <Uri value={writer} />
                  </div>
                ))}
          </dd>
          <dt>version</dt>
          <dd>{String(state.version ?? "—")}</dd>
        </dl>
      </Panel>

      <Panel title={<h2>Actions</h2>}>
        <DeployResult
          busy={action.busy}
          error={action.error}
          refusal={action.refusal}
          receipt={action.receipt}
        />
        <div className="action-box">
          <h3>Anchor a document</h3>
          <p className="muted small">
            The document stays off-chain. The hash is BLAKE2b-256 of the text entered here.
          </p>
          <div className="grid three">
            <Field label="Kind">
              <input value={kind} onChange={(event) => setKind(event.target.value)} />
            </Field>
            <Field label="Document text" hint="hashed">
              <input
                value={documentText}
                onChange={(event) => setDocumentText(event.target.value)}
              />
            </Field>
            <Field label="Parent hash" hint="optional">
              <input
                value={parentHash}
                onChange={(event) => setParentHash(event.target.value)}
                className="mono"
              />
            </Field>
          </div>
          <button
            className="primary"
            disabled={action.busy || !address || !documentText}
            onClick={() =>
              action.run(
                "document anchored",
                () =>
                  client.provenance_anchor(
                    uri,
                    JSON.stringify({
                      kind,
                      hash: client.hash_text(documentText),
                      parentHash,
                    }),
                  ),
                [["provenance", uri], ["provenance-anchors", uri]],
              )
            }
          >
            Anchor
          </button>
        </div>

        <div className="action-box">
          <h3>Comment</h3>
          <Field label="Comment" hint="hashed">
            <input value={comment} onChange={(event) => setComment(event.target.value)} />
          </Field>
          <button
            disabled={action.busy || !address || !comment}
            onClick={() =>
              action.run(
                "provenance comment",
                () =>
                  client.provenance_comment(
                    uri,
                    JSON.stringify({ hash: client.hash_text(comment) }),
                  ),
                [["provenance", uri]],
              )
            }
          >
            Add comment
          </button>
        </div>

        <div className="action-box">
          <h3>Verify a hash (free read)</h3>
          <Field label="Hash">
            <input
              value={verifyHash}
              onChange={(event) => setVerifyHash(event.target.value)}
              className="mono"
            />
          </Field>
          <button className="ghost" disabled={!verifyHash} onClick={verify}>
            Verify
          </button>
          {verified && <p className="mono small">{verified}</p>}
          {verifyError && <p className="error">{verifyError}</p>}
        </div>
      </Panel>

      <Panel title={<h2>Anchors</h2>}>
        {anchorList.length === 0 ? (
          <p className="muted">No anchors yet.</p>
        ) : (
          <Json value={anchorList} />
        )}
      </Panel>

      <Panel title={<h2>Raw state</h2>}>
        <Json value={state} />
      </Panel>
    </div>
  );
}
