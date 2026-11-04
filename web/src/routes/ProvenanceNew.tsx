import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { message, parseWrite } from "../lib/api";
import { commaList } from "../lib/format";
import * as journal from "../lib/journal";
import { useWallet } from "../lib/store";
import { ErrorBox, Field, Panel } from "../components/ui";

export default function ProvenanceNew() {
  const navigate = useNavigate();
  const { client, address, status } = useWallet();
  const [assetRef, setAssetRef] = useState("");
  const [writers, setWriters] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    if (!client) return;
    setBusy(true);
    setError(null);
    try {
      const declared = commaList(writers);
      if (address && !declared.includes(address)) declared.push(address);
      const envelope = parseWrite<{ id?: string; uri?: string }>(
        await client.provenance_create(
          JSON.stringify({
            assetRef: { uri: assetRef.trim() },
            writers: declared,
          }),
        ),
      );
      const uri = envelope.data.uri ?? envelope.data.id;
      await journal.fromReceipt("provenance", envelope.deploy, "provenance created", uri);
      if (uri) navigate(`/provenance/${uri}`);
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy(false);
    }
  };

  if (status !== "unlocked") {
    return (
      <Panel title={<h1>New provenance record</h1>}>
        <p className="muted">Unlock a writer wallet.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel title={<h1>New provenance record</h1>}>
        <p className="muted small">
          The creator is derived from the signing key. Writers can anchor and comment; the
          creator is added automatically.
        </p>
        <Field label="Asset reference URI">
          <input
            value={assetRef}
            onChange={(event) => setAssetRef(event.target.value)}
            placeholder="rho:id:… of the K-Asset or claim"
            className="mono"
          />
        </Field>
        <Field label="Writers" hint="comma-separated REV addresses">
          <input
            value={writers}
            onChange={(event) => setWriters(event.target.value)}
            placeholder={address ?? "REV address"}
            className="mono"
          />
        </Field>
        <ErrorBox error={error} />
        <button
          className="primary"
          onClick={submit}
          disabled={busy || !client || !assetRef}
        >
          {busy ? "signing and waiting for finality…" : "Create provenance"}
        </button>
      </Panel>
    </div>
  );
}
