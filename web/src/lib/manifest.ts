import type { NetworkProfile } from "./network";

// A manifest is an unsigned file of URI designations. Devnet may trust the local file;
// every other network must pin a Root, and a substituted manifest is refused before any
// deploy is signed (RGA-051).
export function assertPinnedRoot(document: string, profile: NetworkProfile): string {
  const pinned = import.meta.env.VITE_RGEN_ROOT_URI as string | undefined;
  if (!pinned) {
    if (profile.name === "devnet") return document;
    throw new Error(`manifest Root is not pinned; set VITE_RGEN_ROOT_URI for ${profile.name}`);
  }
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
