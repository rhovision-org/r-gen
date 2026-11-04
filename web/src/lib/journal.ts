import { addJournal, listJournal } from "./db";
import type { JournalEntry, Receipt } from "./types";

export type { JournalEntry };

export async function record(
  entry: Omit<JournalEntry, "id" | "createdAt"> & { id?: string },
): Promise<string> {
  const id = entry.id ?? `${entry.kind}-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`;
  await addJournal({ ...entry, id, createdAt: Date.now() });
  return id;
}

export function fromReceipt(
  kind: string,
  receipt: Receipt,
  summary: string,
  uri?: string,
): Promise<string> {
  return record({
    kind,
    uri,
    opId: undefined,
    deployId: receipt.deployId,
    blockNumber: receipt.blockNumber,
    status: receipt.finalized ? "finalized" : "submitted",
    summary,
  });
}

export function fromRefusal(
  kind: string,
  reason: string,
  summary: string,
  receipt?: Receipt,
  uri?: string,
): Promise<string> {
  return record({
    kind,
    uri,
    deployId: receipt?.deployId,
    blockNumber: receipt?.blockNumber,
    status: "refused",
    refusal: reason,
    summary,
  });
}

export async function list(): Promise<JournalEntry[]> {
  return listJournal();
}

export async function mark(
  id: string,
  patch: Partial<Pick<JournalEntry, "status" | "deployId" | "blockNumber" | "refusal">>,
): Promise<void> {
  const entries = await listJournal();
  const entry = entries.find((item) => item.id === id);
  if (!entry) return;
  await addJournal({ ...entry, ...patch });
}
