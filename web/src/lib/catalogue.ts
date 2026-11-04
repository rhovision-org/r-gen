import type { Catalogue, CatalogueEntry } from "./types";

/**
 * The catalogue is a list of real on-chain URIs produced by `harness/demo_seed.py`.
 * It is not an index: every card is re-read from the chain.
 */
export async function loadCatalogue(
  networkId: string | undefined,
  root: string | undefined,
): Promise<CatalogueEntry[]> {
  const base = import.meta.env.BASE_URL || "/";
  const prefix = base.endsWith("/") ? base : `${base}/`;
  const response = await fetch(`${prefix}catalogue.json`, { cache: "no-store" });
  if (!response.ok) return [];
  const catalogue = (await response.json()) as Catalogue;
  if (catalogue.networkId && networkId && catalogue.networkId !== networkId) {
    throw new Error(
      `catalogue belongs to ${catalogue.networkId}, connected chain is ${networkId}`,
    );
  }
  if (catalogue.root && root && catalogue.root !== root) {
    throw new Error("catalogue belongs to a different Root deployment");
  }
  return catalogue.entries ?? catalogue.entities ?? [];
}
