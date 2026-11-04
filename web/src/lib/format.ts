export function shortId(value: string | undefined | null, length = 10): string {
  if (!value) return "—";
  if (value.length <= length * 2 + 3) return value;
  return `${value.slice(0, length)}…${value.slice(-length)}`;
}

export function shortHash(value: string | undefined | null, length = 8): string {
  if (!value) return "—";
  if (value.length <= length * 2 + 3) return value;
  return `${value.slice(0, length)}…${value.slice(-length)}`;
}

export function block(value: unknown): string {
  if (typeof value === "number") return value.toLocaleString();
  if (typeof value === "string" && value) return value;
  return "—";
}

export function when(ms: number): string {
  return new Date(ms).toLocaleString();
}

export function relative(ms: number): string {
  const seconds = Math.round((Date.now() - ms) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  if (seconds < 86_400) return `${Math.round(seconds / 3600)}h ago`;
  return `${Math.round(seconds / 86_400)}d ago`;
}

export function statusTone(status: string | undefined): "good" | "warn" | "bad" | "plain" {
  switch (status) {
    case "active":
    case "validated":
    case "approved":
    case "executed":
    case "closed":
    case "upheld":
      return "good";
    case "open":
    case "proposed":
    case "conditional":
    case "validating":
    case "decided":
    case "executing":
    case "submitted":
    case "finalized":
      return "warn";
    case "rejected":
    case "withdrawn":
    case "expired":
    case "revoked":
    case "disputed":
    case "partially_revoked":
    case "failed":
    case "refused":
      return "bad";
    default:
      return "plain";
  }
}

export function commaList(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function asText(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
