import { describe, expect, it } from "vitest";
import { ChainRefusal, message, parseRead, parseWrite, refusalOf } from "./api";

describe("envelopes", () => {
  it("parses a read envelope", () => {
    const envelope = parseRead<{ status: string }>(
      JSON.stringify({
        ok: true,
        data: { status: "approved" },
        read: { atHeight: 7, blockHash: "ab", source: "explore", deployId: null },
      }),
    );
    expect(envelope.data.status).toBe("approved");
    expect(envelope.read.atHeight).toBe(7);
  });

  it("parses a write receipt", () => {
    const envelope = parseWrite<{ uri: string }>(
      JSON.stringify({
        ok: true,
        data: { uri: "rho:id:abc" },
        deploy: {
          deployId: "00",
          finalized: true,
          blockHash: "ab",
          blockNumber: 9,
          termBytes: 100,
          status: "processedWithSuccess",
        },
      }),
    );
    expect(envelope.deploy.blockNumber).toBe(9);
  });

  it("turns a refusal into a typed error that keeps the deploy", () => {
    const text = JSON.stringify({
      ok: false,
      code: "refused",
      message: "not open",
      deploy: {
        deployId: "11",
        finalized: true,
        blockHash: null,
        blockNumber: 10,
        termBytes: 80,
        status: "processedWithSuccess",
      },
    });
    try {
      parseWrite(text);
      throw new Error("expected a refusal");
    } catch (error) {
      expect(error).toBeInstanceOf(ChainRefusal);
      const envelope = refusalOf(error);
      expect(envelope?.message).toBe("not open");
      expect(envelope?.deploy?.blockNumber).toBe(10);
      expect(message(error)).toBe("not open");
    }
  });

  it("rejects a non-envelope", () => {
    expect(() => parseRead("{}")).toThrow();
  });
});
