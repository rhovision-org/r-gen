import { afterEach, describe, expect, it, vi } from "vitest";
import { assertPinnedRoot } from "./manifest";
import { DEVNET, TESTNET } from "./network";

const document = JSON.stringify({ root_uri: "rho:id:abc" });

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("manifest Root pinning", () => {
  it("devnet trusts the local manifest without a pin", () => {
    vi.stubEnv("VITE_RGEN_ROOT_URI", "");
    expect(assertPinnedRoot(document, DEVNET)).toBe(document);
  });

  it("testnet refuses an unpinned manifest", () => {
    vi.stubEnv("VITE_RGEN_ROOT_URI", "");
    expect(() => assertPinnedRoot(document, TESTNET)).toThrow(/not pinned/);
  });

  it("testnet rejects a substituted Root", () => {
    vi.stubEnv("VITE_RGEN_ROOT_URI", "rho:id:other");
    expect(() => assertPinnedRoot(document, TESTNET)).toThrow(/does not match/);
  });

  it("testnet accepts the pinned Root", () => {
    vi.stubEnv("VITE_RGEN_ROOT_URI", "rho:id:abc");
    expect(assertPinnedRoot(document, TESTNET)).toBe(document);
  });
});
