import { describe, expect, it } from "vitest";
import { DEVNET, TESTNET, isRhoUri, isTestnetNode, networkForNode } from "./network";

describe("network profiles", () => {
  it("maps the public host to the testnet profile", () => {
    expect(isTestnetNode("https://testnet.rhobot.net")).toBe(true);
    expect(networkForNode("https://testnet.rhobot.net").shard).toBe("/testnet");
    expect(networkForNode("https://testnet.rhobot.net").expectedNetworkId).toBe(
      TESTNET.expectedNetworkId,
    );
  });

  it("keeps localhost on the devnet shard", () => {
    expect(networkForNode("http://localhost:40403").name).toBe("devnet");
    expect(networkForNode("http://localhost:40403").shard).toBe("/root");
    expect(DEVNET.faucetUrl).toContain("/api/v1/faucet");
  });

  it("treats an unknown host as custom without claiming its network id", () => {
    const profile = networkForNode("http://10.0.0.5:40403");
    expect(profile.name).toBe("custom");
    expect(profile.expectedNetworkId).toBeUndefined();
  });

  it("accepts only registry URIs", () => {
    expect(isRhoUri("rho:id:abc123")).toBe(true);
    expect(isRhoUri("https://example.com")).toBe(false);
    expect(isRhoUri("rho:id:")).toBe(false);
  });
});
