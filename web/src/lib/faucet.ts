import type { NetworkProfile } from "./network";

export interface FaucetResult {
  ok: boolean;
  message: string;
}

/**
 * The faucet is an unauthenticated node route. Devnet serves `/api/v1/faucet`;
 * the public testnet serves `/api/faucet`. The policy is one drip per address.
 */
export async function requestFaucet(
  profile: NetworkProfile,
  address: string,
): Promise<FaucetResult> {
  const candidates = [profile.faucetUrl];
  if (profile.name === "testnet" && !candidates.includes(`${profile.node}/api/v1/faucet`)) {
    candidates.push(`${profile.node}/api/v1/faucet`);
  }
  let last = "faucet did not answer";
  for (const url of candidates) {
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ address }),
      });
      const text = await response.text();
      if (response.ok) {
        return { ok: true, message: text || "faucet accepted the request" };
      }
      if (response.status === 400 && /already|funded|drip/i.test(text)) {
        return { ok: true, message: `${address} has already had its drip` };
      }
      if (response.status === 429) {
        return { ok: false, message: "faucet is rate limited; wait and retry" };
      }
      last = `${response.status}: ${text}`;
    } catch (error) {
      last = error instanceof Error ? error.message : String(error);
    }
  }
  return { ok: false, message: last };
}
