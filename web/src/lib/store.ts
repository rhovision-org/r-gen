import { create } from "zustand";
import { initWasm, Rgen } from "../wasm";
import * as db from "./db";
import {
  DEVNET,
  manifestUrl,
  networkForNode,
  type NetworkProfile,
} from "./network";
import type { StoredKeystore } from "./types";

const NODE_KEY = "rgen.node";
const manifestKey = (node: string) => `rgen.manifest.${node}`;

export type WalletStatus = "idle" | "loading" | "locked" | "unlocked" | "error";

export interface Readiness {
  state: "idle" | "checking" | "ready" | "error";
  networkId?: string;
  shard?: string;
  root?: string;
  components?: Record<string, { uri: string; version: number }>;
  error?: string;
}

interface WalletState {
  status: WalletStatus;
  address: string | null;
  publicKey: string | null;
  client: Rgen | null;
  node: string;
  profile: NetworkProfile;
  manifest: string | null;
  readiness: Readiness;
  profiles: StoredKeystore[];
  error: string | null;
  unlockOpen: boolean;

  boot: () => Promise<void>;
  setNode: (node: string) => Promise<void>;
  setManifest: (document: string) => Promise<void>;
  refreshReadiness: () => Promise<void>;
  refreshProfiles: () => Promise<void>;
  openUnlock: () => void;
  closeUnlock: () => void;
  createWallet: (password: string, label?: string) => Promise<string>;
  unlock: (document: string, password: string) => Promise<string>;
  unlockSaved: (address: string, password: string) => Promise<void>;
  switchProfile: (address: string, password: string) => Promise<void>;
  lock: () => void;
  exportKeystore: (password: string) => Promise<string>;
  clientOrThrow: () => Rgen;
  writesReady: () => boolean;
}

function initialNode(): string {
  return localStorage.getItem(NODE_KEY) || DEVNET.node;
}

function text(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

async function retry<T>(work: () => Promise<T>, attempts = 4): Promise<T> {
  let last: unknown;
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      return await work();
    } catch (error) {
      last = error;
      if (attempt + 1 < attempts) {
        await new Promise((resolve) => window.setTimeout(resolve, 1_200 * 2 ** attempt));
      }
    }
  }
  throw last;
}

// A manifest is an unsigned file of URI designations. When the build pins a Root,
// a substituted manifest is refused before any deploy is signed (RGA-051).
function assertPinnedRoot(document: string): string {
  const pinned = import.meta.env.VITE_RGEN_ROOT_URI as string | undefined;
  if (!pinned) return document;
  let root: unknown;
  try {
    root = JSON.parse(document).root_uri;
  } catch {
    throw new Error("manifest is not valid JSON");
  }
  if (root !== pinned) {
    throw new Error(`manifest Root ${String(root)} does not match the pinned Root ${pinned}`);
  }
  return document;
}

async function manifestFor(profile: NetworkProfile, node: string): Promise<string> {
  // A deployed manifest wins over a cached one: a reinstall changes the Root, and an old
  // Root resolves to nothing. The cache is only a fallback when the fetch is unavailable.
  const url = manifestUrl(profile);
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (response.ok) {
      const document = assertPinnedRoot(await response.text());
      localStorage.setItem(manifestKey(node), document);
      return document;
    }
  } catch {
    // offline or a static host without the file
  }
  const stored = localStorage.getItem(manifestKey(node));
  if (stored) return assertPinnedRoot(stored);
  throw new Error(
    `no manifest at ${url} and none saved. Install the contracts, then paste deployments/${profile.manifestPath} in Settings.`,
  );
}

export const useWallet = create<WalletState>((set, get) => ({
  status: "idle",
  address: null,
  publicKey: null,
  client: null,
  node: initialNode(),
  profile: networkForNode(initialNode()),
  manifest: null,
  readiness: { state: "idle" },
  profiles: [],
  error: null,
  unlockOpen: true,

  boot: async () => {
    if (get().status === "loading") return;
    set({ status: "loading", error: null, readiness: { state: "checking" } });
    try {
      await initWasm();
      const node = get().node;
      const profile = networkForNode(node);
      const manifest = await manifestFor(profile, node);
      const client = new Rgen(node, manifest);
      client.set_network(
        profile.shard,
        BigInt(profile.phloLimit),
        BigInt(profile.phloPrice),
      );
      const profiles = await db.listKeystores();
      set({
        client,
        profile,
        manifest,
        profiles,
        status: "locked",
      });
      await get().refreshReadiness();
    } catch (error) {
      set({
        status: "error",
        error: text(error),
        readiness: { state: "error", error: text(error) },
      });
    }
  },

  setNode: async (node: string) => {
    localStorage.setItem(NODE_KEY, node);
    const current = get();
    try {
      current.client?.lock();
    } catch {
      // A reader with no key is already locked.
    }
    set({
      node,
      profile: networkForNode(node),
      client: null,
      manifest: null,
      address: null,
      publicKey: null,
      status: "idle",
      error: null,
      readiness: { state: "idle" },
    });
    await get().boot();
  },

  setManifest: async (document: string) => {
    const node = get().node;
    const profile = networkForNode(node);
    const checked = assertPinnedRoot(document);
    const client = new Rgen(node, checked);
    client.set_network(
      profile.shard,
      BigInt(profile.phloLimit),
      BigInt(profile.phloPrice),
    );
    localStorage.setItem(manifestKey(node), checked);
    set({ client, manifest: checked, profile, status: "locked", error: null });
    await get().refreshReadiness();
  },

  refreshReadiness: async () => {
    const client = get().client;
    if (!client) return;
    set({ readiness: { ...get().readiness, state: "checking", error: undefined } });
    try {
      const status = JSON.parse(await retry(() => client.status())) as {
        networkId?: string;
        shardId?: string;
      };
      const profile = get().profile;
      if (
        profile.expectedNetworkId &&
        status.networkId &&
        status.networkId !== profile.expectedNetworkId
      ) {
        throw new Error(
          `network mismatch: expected ${profile.expectedNetworkId}, node reports ${status.networkId}`,
        );
      }
      if (status.shardId && status.shardId !== profile.shard) {
        throw new Error(
          `shard mismatch: expected ${profile.shard}, node reports ${status.shardId}`,
        );
      }
      const components = JSON.parse(await retry(() => client.resolve_all())) as Record<
        string,
        { uri: string; version: number }
      >;
      set({
        readiness: {
          state: "ready",
          networkId: status.networkId,
          shard: status.shardId,
          root: get().manifest ? JSON.parse(get().manifest!).root_uri : undefined,
          components,
        },
      });
    } catch (error) {
      set({
        readiness: { state: "error", error: text(error) },
      });
    }
  },

  refreshProfiles: async () => {
    set({ profiles: await db.listKeystores() });
  },

  openUnlock: () => set({ unlockOpen: true }),
  closeUnlock: () => set({ unlockOpen: false }),

  createWallet: async (password: string, label = "wallet") => {
    const client = get().client;
    if (!client) throw new Error("the wallet has not booted");
    const document = await client.create_wallet(password);
    const address = client.address();
    if (!address) throw new Error("the new wallet has no address");
    await db.saveKeystore(address, document, label);
    set({
      status: "unlocked",
      address,
      publicKey: client.public_key() ?? null,
      profiles: await db.listKeystores(),
      error: null,
      unlockOpen: false,
    });
    return document;
  },

  unlock: async (document: string, password: string) => {
    const client = get().client;
    if (!client) throw new Error("the wallet has not booted");
    const address = await client.unlock(document, password);
    await db.saveKeystore(address, document);
    set({
      status: "unlocked",
      address,
      publicKey: client.public_key() ?? null,
      profiles: await db.listKeystores(),
      error: null,
      unlockOpen: false,
    });
    return address;
  },

  unlockSaved: async (address: string, password: string) => {
    const stored = await db.loadKeystore(address);
    if (!stored) throw new Error(`no saved keystore for ${address}`);
    await get().unlock(stored.document, password);
  },

  switchProfile: async (address: string, password: string) => {
    get().lock();
    await get().unlockSaved(address, password);
  },

  lock: () => {
    const client = get().client;
    try {
      client?.lock();
    } catch {
      // already locked
    }
    set({ status: "locked", address: null, publicKey: null, unlockOpen: true });
  },

  exportKeystore: async (password: string) => {
    const client = get().clientOrThrow();
    return client.export_keystore(password);
  },

  clientOrThrow: () => {
    const client = get().client;
    if (!client) throw new Error("the wallet has not booted");
    return client;
  },

  writesReady: () => get().readiness.state === "ready" && get().status === "unlocked",
}));
