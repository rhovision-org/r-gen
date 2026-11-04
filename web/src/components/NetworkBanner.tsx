import { useWallet } from "../lib/store";

export default function NetworkBanner() {
  const { readiness, profile, node, status } = useWallet();
  if (status === "loading" || readiness.state === "checking") {
    return <div className="banner warn">Checking the node and resolving the Root…</div>;
  }
  if (readiness.state === "error") {
    return (
      <div className="banner bad">
        <strong>{profile.name} is not ready.</strong> {readiness.error}
        <span className="muted"> · node {node}. Fix the manifest in Settings or start the devnet.</span>
      </div>
    );
  }
  if (readiness.state === "ready") {
    return (
      <div className="banner good">
        {profile.name}
        {profile.name === "testnet" && readiness.networkId ? ` · ${readiness.networkId}` : ""} ·
        shard {readiness.shard ?? "?"} · Root resolved (
        {Object.keys(readiness.components ?? {}).length}/9 keys)
      </div>
    );
  }
  return null;
}
