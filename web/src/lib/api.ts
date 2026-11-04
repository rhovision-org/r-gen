import type {
  Envelope,
  ReadEnvelope,
  Receipt,
  RefusalEnvelope,
  WriteEnvelope,
} from "./types";

export class ChainRefusal extends Error {
  readonly envelope: RefusalEnvelope;
  constructor(envelope: RefusalEnvelope) {
    super(envelope.message || envelope.code || "refused");
    this.name = "ChainRefusal";
    this.envelope = envelope;
  }
}

export function decode<T>(text: string): Envelope<T> {
  const value = JSON.parse(text) as Envelope<T>;
  if (typeof value !== "object" || value === null || !("ok" in value)) {
    throw new Error("chain reply is not an envelope");
  }
  return value;
}

export function parseRead<T>(text: string): ReadEnvelope<T> {
  const envelope = decode<T>(text);
  if (!envelope.ok) throw new ChainRefusal(envelope);
  if (!("read" in envelope)) throw new Error("expected a read envelope");
  return envelope as ReadEnvelope<T>;
}

export function parseWrite<T>(text: string): WriteEnvelope<T> {
  const envelope = decode<T>(text);
  if (!envelope.ok) throw new ChainRefusal(envelope);
  if (!("deploy" in envelope)) throw new Error("expected a write envelope");
  return envelope as WriteEnvelope<T>;
}

export function refusalOf(error: unknown): RefusalEnvelope | null {
  return error instanceof ChainRefusal ? error.envelope : null;
}

export function message(error: unknown): string {
  if (error instanceof Error) return error.message;
  return String(error);
}

export function receiptOf(error: unknown): Receipt | undefined {
  return error instanceof ChainRefusal ? error.envelope.deploy : undefined;
}

export function copy(text: string): Promise<void> {
  return navigator.clipboard.writeText(text);
}

export function shareUrl(kind: string, uri: string): string {
  return `${window.location.origin}${window.location.pathname}#/${kind}/${uri}`;
}

export function parseJson<T>(text: string, label: string): T {
  try {
    return JSON.parse(text) as T;
  } catch (error) {
    throw new Error(`${label}: ${message(error)}`);
  }
}
