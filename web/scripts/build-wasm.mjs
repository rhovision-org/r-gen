// Build the r-gen wasm module into web/src/wasm/pkg. Paths are repo-relative.
import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const webDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const repo = resolve(webDir, "..");
const outDir = resolve(webDir, "src/wasm/pkg");
const result = spawnSync(
  "wasm-pack",
  [
    "build",
    resolve(repo, "crates/rgen-wasm"),
    "--target",
    "web",
    "--release",
    "--out-dir",
    outDir,
  ],
  { cwd: repo, stdio: "inherit" },
);
process.exit(result.status ?? 1);
