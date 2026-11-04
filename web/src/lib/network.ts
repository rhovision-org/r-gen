export interface NetworkProfile {
  name: "devnet" | "testnet" | "custom";
  node: string;
  shard: string;
  phloLimit: number;
  phloPrice: number;
  manifestPath: string;
  faucetUrl: string;
  expectedNetworkId?: string;
  genesis?: string;
}

export const DEVNET: NetworkProfile = {
  name: "devnet",
  node: "http://localhost:40403",
  shard: "/root",
  phloLimit: 8_000_000,
  phloPrice: 1,
  manifestPath: "devnet.json",
  faucetUrl: "http://localhost:40403/api/v1/faucet",
};

export const TESTNET: NetworkProfile = {
  name: "testnet",
  node: "https://testnet.rhobot.net",
  shard: "/testnet",
  phloLimit: 8_000_000,
  phloPrice: 1,
  manifestPath: "testnet.json",
  faucetUrl: "https://testnet.rhobot.net/api/faucet",
  expectedNetworkId: "testnet-133b1d307b175012",
  genesis: "133b1d307b1750129cf0cfb69c4c8f950da21c4e8db2a6a076464d0ccfd98d44",
};

const TESTNET_HINTS = ["rhobot.net", "164.90.140.144", "167.99.43.214"];

export function isTestnetNode(node: string): boolean {
  return TESTNET_HINTS.some((hint) => node.includes(hint));
}

export function networkForNode(node: string): NetworkProfile {
  if (isTestnetNode(node)) return { ...TESTNET, node };
  if (node.includes("localhost") || node.includes("127.0.0.1")) {
    return { ...DEVNET, node };
  }
  return {
    name: "custom",
    node,
    shard: "/root",
    phloLimit: 8_000_000,
    phloPrice: 1,
    manifestPath: "devnet.json",
    faucetUrl: `${node.replace(/\/$/, "")}/api/v1/faucet`,
  };
}

export function manifestUrl(profile: NetworkProfile): string {
  const base = import.meta.env.BASE_URL || "/";
  const prefix = base.endsWith("/") ? base : `${base}/`;
  return `${prefix}${profile.manifestPath.replace(/^\//, "")}`;
}

export function isRhoUri(value: string): boolean {
  return /^rho:id:[A-Za-z0-9:_/-]+$/.test(value.trim());
}
