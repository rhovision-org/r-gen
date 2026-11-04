// Offline WASM smoke: no node, no chain writes.
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import init, { Rgen, version } from "../src/wasm/pkg/rgen_wasm.js";

const here = dirname(fileURLToPath(import.meta.url));
const wasm = readFileSync(resolve(here, "../src/wasm/pkg/rgen_wasm_bg.wasm"));
await init(wasm);

const manifest = JSON.stringify({ root_uri: "rho:id:smoke", components: {} });
const client = new Rgen("http://127.0.0.1:1", manifest);
client.set_network("/root", 8_000_000n, 1n);

if (version() === "") throw new Error("version is empty");
if (client.is_unlocked()) throw new Error("a fresh client must be locked");
if (client.address() !== undefined) throw new Error("a reader has no address");

const emptyHash = client.hash_text("");
if (emptyHash !== "0e5751c026e543b2e8ab2eb06099daa1d1e5df47778f7787faab45cdf12fe3a8") {
  throw new Error(`unexpected BLAKE2b-256: ${emptyHash}`);
}

const op = client.new_op_id("smoke", 1_700_000_000_000n);
if (!op.startsWith("smoke-1700000000000-")) throw new Error(`unexpected op id: ${op}`);

const document = client.create_wallet("smoke-password");
if (!document.includes('"version":3') || !document.includes("aes-128-ctr")) {
  throw new Error("wallet did not return a v3 keystore");
}
if (!client.is_unlocked() || !client.address()) throw new Error("create_wallet did not unlock");
const address = client.address();
const exported = client.export_keystore("smoke-password");
if (!exported.includes('"version":3')) throw new Error("export failed");
client.lock();
if (client.is_unlocked()) throw new Error("lock did not drop the key");
const imported = new Rgen("http://127.0.0.1:1", manifest);
imported.set_network("/root", 8_000_000n, 1n);
const importedAddress = imported.unlock(exported, "smoke-password");
if (importedAddress !== address) throw new Error("unlock returned a different address");

const claim = {
  work: { titleHash: "t", discipline: "structural", jurisdiction: "US-TX", projectRef: "p" },
  selectionCriteria: {
    ctype: "Validator",
    discipline: "structural",
    jurisdiction: "US-TX",
    role: "validator",
    minLevel: 1,
  },
  selectionCriteriaHash: "s",
  statementHash: "s",
  definitionHash: "d",
  quantity: { unit: "bays", value: 12 },
  evidence: [],
  valuePropositionRef: null,
  deadlineHeight: 100,
  commentUntilHeight: 50,
};
imported.validate_payload("claim", JSON.stringify(claim), 10n);
let refused = false;
try {
  imported.validate_payload("claim", JSON.stringify(claim), 100n);
} catch {
  refused = true;
}
if (!refused) throw new Error("a past deadline must be refused offline");

console.log("wasm-smoke: ok", version(), address);
