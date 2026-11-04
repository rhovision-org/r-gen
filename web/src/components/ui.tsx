import type { ReactNode } from "react";
import { copy } from "../lib/api";
import { shortId, statusTone } from "../lib/format";
import type { ReadMeta } from "../lib/types";

export function Panel({
  title,
  actions,
  children,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      {(title || actions) && (
        <div className="panel-head">
          <div>{title}</div>
          {actions && <div className="row gap wrap">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="field">
      <span>
        {label}
        {hint && <em className="hint"> · {hint}</em>}
      </span>
      {children}
    </label>
  );
}

export function ReadBadge({ meta }: { meta?: ReadMeta }) {
  if (!meta) return null;
  return (
    <span className={`badge ${meta.source}`}>
      {meta.source === "explore" ? "free read" : "signed read"} · block {meta.atHeight}
    </span>
  );
}

export function StatusPill({ status }: { status?: string }) {
  return <span className={`pill ${statusTone(status)}`}>{status ?? "unknown"}</span>;
}

export function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <p className="error">{error}</p>;
}

export function CopyButton({ value, label = "Copy" }: { value: string; label?: string }) {
  return (
    <button className="ghost small-button" onClick={() => void copy(value)} type="button">
      {label}
    </button>
  );
}

export function Uri({ value, kind }: { value?: string | null; kind?: string }) {
  if (!value) return <span className="muted">—</span>;
  return (
    <span className="row gap wrap">
      <span className="mono" title={value}>
        {shortId(value, 12)}
      </span>
      <CopyButton value={value} />
      {kind && (
        <a href={`#/${kind}/${value}`} className="small">
          open
        </a>
      )}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="muted empty">{children}</p>;
}

export function Json({ value }: { value: unknown }) {
  return <pre className="json">{JSON.stringify(value, null, 2)}</pre>;
}
