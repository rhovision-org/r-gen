import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { message, parseWrite } from "../lib/api";
import { str, useRead } from "../lib/entity";
import * as journal from "../lib/journal";
import { useWallet } from "../lib/store";
import { ErrorBox, Field, Panel } from "../components/ui";
import type { State } from "../lib/types";

export default function CredentialIssue() {
  const navigate = useNavigate();
  const { client, address, readiness, status } = useWallet();
  const issuer = useRead<State>(
    ["issuer"],
    client ? () => client.issuer_get() : null,
  );
  const [subject, setSubject] = useState("");
  const [ctype, setCtype] = useState("Validator");
  const [discipline, setDiscipline] = useState("structural");
  const [jurisdiction, setJurisdiction] = useState("US-TX");
  const [role, setRole] = useState("validator");
  const [level, setLevel] = useState("1");
  const [evidence, setEvidence] = useState("");
  const [expiresAt, setExpiresAt] = useState("0");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const issuerSubject = str(issuer.data?.data, "subject");
  const isIssuer = !!address && !!issuerSubject && address === issuerSubject;

  const submit = async () => {
    if (!client) return;
    setBusy(true);
    setError(null);
    try {
      const issuerUri =
        readiness.components?.["component:issuer"]?.uri ?? "";
      const payload = {
        subject: subject.trim(),
        ctype,
        discipline,
        jurisdiction,
        role,
        level: Number(level),
        evidenceHash: client.hash_text(evidence),
        issuerUri,
        expiresAt: Number(expiresAt),
      };
      const envelope = parseWrite<string | { uri?: string }>(
        await client.credential_issue(JSON.stringify(payload)),
      );
      const uri =
        typeof envelope.data === "string" ? envelope.data : envelope.data.uri;
      await journal.fromReceipt("credential", envelope.deploy, `issued ${ctype}`, uri);
      if (uri) navigate(`/credentials/${uri}`);
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy(false);
    }
  };

  if (status !== "unlocked") {
    return (
      <Panel title={<h1>Issue a credential</h1>}>
        <p className="muted">Unlock the genesis issuer wallet.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel title={<h1>Issue a credential</h1>}>
        <p className="muted small">
          The contract refuses a signer that is not the genesis issuer, and refuses
          self-issue. The issuer subject is read from <code>Issuer.get</code>.
        </p>
        <p className="muted">
          issuer subject: <span className="mono">{issuerSubject ?? "…"}</span>
          {address && (
            <>
              {" "}· your address: <span className="mono">{address}</span>
            </>
          )}
        </p>
        {!isIssuer && (
          <p className="warn-box">
            This wallet is not the genesis issuer. The contract will refuse the deploy.
          </p>
        )}
        <div className="grid two">
          <div>
            <Field label="Subject REV address">
              <input
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                className="mono"
              />
            </Field>
            <Field label="Credential type" hint="e.g. Validator, Approver, Oracle">
              <input value={ctype} onChange={(event) => setCtype(event.target.value)} />
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
          </div>
          <div>
            <Field label="Role">
              <input value={role} onChange={(event) => setRole(event.target.value)} />
            </Field>
            <Field label="Level">
              <input
                type="number"
                min={1}
                value={level}
                onChange={(event) => setLevel(event.target.value)}
              />
            </Field>
            <Field label="Evidence" hint="hashed">
              <input value={evidence} onChange={(event) => setEvidence(event.target.value)} />
            </Field>
            <Field label="Expires at height" hint="0 = no expiry">
              <input
                type="number"
                min={0}
                value={expiresAt}
                onChange={(event) => setExpiresAt(event.target.value)}
              />
            </Field>
          </div>
        </div>
        <ErrorBox error={error} />
        <button
          className="primary"
          onClick={submit}
          disabled={busy || !client || !subject}
        >
          {busy ? "signing and waiting for finality…" : "Issue credential"}
        </button>
      </Panel>
    </div>
  );
}
