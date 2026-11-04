import { describe, expect, it } from "vitest";
import { commaList, shortHash, shortId, statusTone } from "./format";

describe("formatting", () => {
  it("shortens long identifiers and leaves short ones", () => {
    expect(shortId("rho:id:abc", 4)).toBe("rho:id:abc");
    expect(shortHash("a".repeat(80), 4)).toBe("aaaa…aaaa");
  });

  it("classifies statuses for the pill", () => {
    expect(statusTone("approved")).toBe("good");
    expect(statusTone("validating")).toBe("warn");
    expect(statusTone("revoked")).toBe("bad");
    expect(statusTone("unknown-status")).toBe("plain");
  });

  it("splits comma-separated writers", () => {
    expect(commaList("alice, bob,, carol ")).toEqual(["alice", "bob", "carol"]);
  });
});
