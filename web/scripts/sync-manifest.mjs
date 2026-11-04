// Copy generated deployment manifests and the demo catalogue into public/.
// These are outputs of the installer and seed commands, not hand-written data.
import { copyFileSync, existsSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(webDir, "..");
const publicDir = resolve(webDir, "public");
mkdirSync(publicDir, { recursive: true });

for (const [source, target] of [
  ["deployments/devnet.json", "devnet.json"],
  ["deployments/testnet.json", "testnet.json"],
  ["deployments/catalogue.json", "catalogue.json"],
]) {
  const from = resolve(repo, source);
  if (existsSync(from)) {
    copyFileSync(from, resolve(publicDir, target));
    console.log(`sync-manifest: ${source} -> public/${target}`);
  } else {
    console.warn(`sync-manifest: no ${source}`);
  }
}
