// Typed re-export of the wasm-pack output. The generated module is in src/wasm/pkg.
import init, { Rgen, version } from "./pkg/rgen_wasm.js";

let ready: Promise<unknown> | null = null;

export async function initWasm(): Promise<void> {
  if (!ready) ready = init();
  await ready;
}

export { Rgen, version };
