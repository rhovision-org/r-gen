import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { message, parseWrite } from "../lib/api";
import { useHeight } from "../lib/entity";
import * as journal from "../lib/journal";
import { useWallet } from "../lib/store";
import { ErrorBox, Field, Panel } from "../components/ui";

export default function ClaimNew() {
  const navigate = useNavigate();
  const client = useWallet((state) => state.client);
  const status = useWallet((state) => state.status);
  const height = useHeight();
  const [title, setTitle] = useState("Bridge deck inspection");
  const [discipline, setDiscipline] = useState("structural");
  const [jurisdiction, setJurisdiction] = useState("US-TX");
  const [projectRef, setProjectRef] = useState("bridge-deck-2026");
  const [statement, setStatement] = useState(
    "Inspect twelve deck bays and report every defect.",
  );
  const [definition, setDefinition] = useState(
    "Each bay inspected against the 2026 bridge inspection plan; report hash anchored to the evidence log.",
  );
  const [ctype, setCtype] = useState("Validator");
  const [role, setRole] = useState("validator");
  const [minLevel, setMinLevel] = useState("1");
  const [unit, setUnit] = useState("bay-inspections");
  const [quantity, setQuantity] = useState("12");
  const [deadline, setDeadline] = useState("");
  const [commentUntil, setCommentUntil] = useState("");
  const [vp, setVp] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (height.data !== undefined && !deadline) {
      setDeadline(String(height.data + 1000));
      setCommentUntil(String(height.data + 500));
    }
  }, [height.data, deadline]);

  const submit = async () => {
    if (!client) return;
    setBusy(true);
    setError(null);
    try {
      const criteria = {
        ctype,
        discipline,
        jurisdiction,
        role,
        minLevel: Number(minLevel),
      };
      const payload = {
        work: {
          titleHash: client.hash_text(title),
          discipline,
          jurisdiction,
          projectRef,
        },
        selectionCriteria: criteria,
        selectionCriteriaHash: client.hash_text(JSON.stringify(criteria)),
        statementHash: client.hash_text(statement),
        definitionHash: client.hash_text(definition),
        quantity: { unit, value: Number(quantity) },
        evidence: [],
        valuePropositionRef: vp.trim() ? { id: vp.trim(), uri: vp.trim() } : null,
        deadlineHeight: Number(deadline),
        commentUntilHeight: commentUntil ? Number(commentUntil) : undefined,
      };
      const envelope = parseWrite<{ id?: string; uri?: string }>(
        await client.claim_create(JSON.stringify(payload)),
      );
      const uri = envelope.data.uri ?? envelope.data.id;
      await journal.fromReceipt("claim", envelope.deploy, "claim created", uri);
      if (uri) navigate(`/claims/${uri}`);
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy(false);
    }
  };

  if (status !== "unlocked") {
    return (
      <Panel title={<h1>New claim</h1>}>
        <p className="muted">Unlock the claimant wallet to create a claim.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel title={<h1>New claim</h1>}>
        <p className="muted small">
          Text is hashed in the browser with BLAKE2b-256; only the hash reaches the chain.
          The deadline is an absolute block height.
        </p>
        <div className="grid two">
          <div>
            <Field label="Work title">
              <input value={title} onChange={(event) => setTitle(event.target.value)} />
            </Field>
            <Field label="Discipline">
              <input value={discipline} onChange={(event) => setDiscipline(event.target.value)} />
            </Field>
            <Field label="Jurisdiction">
              <input
                value={jurisdiction}
                onChange={(event) => setJurisdiction(event.target.value)}
              />
            </Field>
            <Field label="Project reference">
              <input value={projectRef} onChange={(event) => setProjectRef(event.target.value)} />
            </Field>
            <Field label="Statement of work" hint="hashed">
              <textarea
                rows={4}
                value={statement}
                onChange={(event) => setStatement(event.target.value)}
              />
            </Field>
            <Field label="Definition / quantity basis" hint="hashed">
              <textarea
                rows={4}
                value={definition}
                onChange={(event) => setDefinition(event.target.value)}
              />
            </Field>
          </div>
          <div>
            <Field label="Validator credential type">
              <input value={ctype} onChange={(event) => setCtype(event.target.value)} />
            </Field>
            <Field label="Validator role">
              <input value={role} onChange={(event) => setRole(event.target.value)} />
            </Field>
            <Field label="Minimum level">
              <input
                type="number"
                min={1}
                value={minLevel}
                onChange={(event) => setMinLevel(event.target.value)}
              />
            </Field>
            <Field label="Quantity unit">
              <input value={unit} onChange={(event) => setUnit(event.target.value)} />
            </Field>
            <Field label="Quantity value">
              <input
                type="number"
                min={0}
                value={quantity}
                onChange={(event) => setQuantity(event.target.value)}
              />
            </Field>
            <Field label="Deadline height" hint={`current ${height.data ?? "…"}`}>
              <input
                type="number"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
              />
            </Field>
            <Field label="Comments close at height">
              <input
                type="number"
                value={commentUntil}
                onChange={(event) => setCommentUntil(event.target.value)}
              />
            </Field>
            <Field label="Value proposition URI" hint="optional">
              <input
                value={vp}
                onChange={(event) => setVp(event.target.value)}
                placeholder="rho:id:…"
                className="mono"
              />
            </Field>
          </div>
        </div>
        <ErrorBox error={error} />
        <button
          className="primary"
          onClick={submit}
          disabled={busy || !client || !deadline || height.data === undefined}
        >
          {busy ? "signing and waiting for finality…" : "Create claim"}
        </button>
      </Panel>
    </div>
  );
}
