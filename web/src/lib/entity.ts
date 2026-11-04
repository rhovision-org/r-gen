import { useQuery } from "@tanstack/react-query";
import { useWallet } from "./store";
import { parseRead } from "./api";
import type { ReadEnvelope } from "./types";

export function str(value: unknown, key: string): string | undefined {
  if (!value || typeof value !== "object") return undefined;
  const item = (value as Record<string, unknown>)[key];
  return typeof item === "string" ? item : undefined;
}

export function num(value: unknown, key: string): number | undefined {
  if (!value || typeof value !== "object") return undefined;
  const item = (value as Record<string, unknown>)[key];
  return typeof item === "number" ? item : undefined;
}

export function obj(value: unknown, key: string): Record<string, unknown> | undefined {
  if (!value || typeof value !== "object") return undefined;
  const item = (value as Record<string, unknown>)[key];
  return item && typeof item === "object" && !Array.isArray(item)
    ? (item as Record<string, unknown>)
    : undefined;
}

export function list(value: unknown, key: string): unknown[] | undefined {
  if (!value || typeof value !== "object") return undefined;
  const item = (value as Record<string, unknown>)[key];
  return Array.isArray(item) ? item : undefined;
}

export function useHeight(enabled = true) {
  const client = useWallet((state) => state.client);
  return useQuery({
    queryKey: ["height"],
    enabled: enabled && !!client,
    refetchInterval: 8_000,
    queryFn: async () => Number(await client!.height()),
  });
}

export function useRead<T>(
  key: readonly unknown[],
  fetcher: (() => Promise<string>) | null,
) {
  return useQuery<ReadEnvelope<T>>({
    queryKey: key,
    enabled: !!fetcher,
    queryFn: async () => parseRead<T>(await fetcher!()),
  });
}

export function rhoOf(value: unknown, key: string): string | undefined {
  const reference = obj(value, key);
  return str(reference, "uri") ?? str(reference, "id");
}
