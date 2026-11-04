import { Json } from "./ui";
import type { Receipt } from "../lib/types";

export default function DeployResult({
  busy,
  error,
  refusal,
  receipt,
}: {
  busy: boolean;
  error: string | null;
  refusal: string | null;
  receipt: Receipt | null;
}) {
  return (
    <>
      {busy && <p className="muted">waiting for finality…</p>}
      {refusal && (
        <p className="warn-box">
          <strong>Refused:</strong> {refusal}. The entity was re-read; a refusal can still
          change state.
        </p>
      )}
      {error && <p className="error">{error}</p>}
      {receipt && (
        <details className="receipt">
          <summary>
            finalized in block {receipt.blockNumber} · {receipt.status}
          </summary>
          <Json value={receipt} />
        </details>
      )}
    </>
  );
}
