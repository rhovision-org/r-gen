import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import * as journal from "./journal";
import { message, parseWrite, receiptOf, refusalOf } from "./api";
import type { Receipt, WriteEnvelope } from "./types";

/**
 * Run one signed write. Every outcome re-reads the entity: a refusal can still change
 * state (expiry, a failed execution receipt), so "refused" is not "nothing happened".
 */
export function useAction(kind: string, uri?: string) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const run = useCallback(
    async (
      summary: string,
      fn: () => Promise<string>,
      invalidate: readonly unknown[][] = [],
    ): Promise<WriteEnvelope<unknown> | null> => {
      setBusy(true);
      setError(null);
      setRefusal(null);
      setReceipt(null);
      try {
        const envelope = parseWrite<unknown>(await fn());
        setReceipt(envelope.deploy);
        await journal.fromReceipt(kind, envelope.deploy, summary, uri);
        await Promise.all(
          invalidate.map((key) => queryClient.invalidateQueries({ queryKey: key })),
        );
        return envelope;
      } catch (cause) {
        const refused = refusalOf(cause);
        if (refused) {
          setRefusal(refused.message);
          const deploy = receiptOf(cause);
          if (deploy) {
            await journal.fromRefusal(kind, refused.message, summary, deploy, uri);
          }
          await Promise.all(
            invalidate.map((key) => queryClient.invalidateQueries({ queryKey: key })),
          );
        } else {
          setError(message(cause));
        }
        return null;
      } finally {
        setBusy(false);
      }
    },
    [kind, uri, queryClient],
  );

  return { busy, error, receipt, refusal, run };
}
