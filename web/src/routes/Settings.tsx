import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { parseRead } from "../lib/api";
import { requestFaucet } from "../lib/faucet";
import { manifestUrl, DEVNET, TESTNET } from "../lib/network";
import { useWallet } from "../lib/store";
import { ErrorBox, Field, Panel, StatusPill } from "../components/ui";

export default function Settings() {
  const {
    node,
    profile,
    manifest,
    readiness,
    address,
    status,
    profiles,
    setNode,
    setManifest,
    refreshReadiness,
    exportKeystore,
    lock,
  } = useWallet();
  const queryClient = useQueryClient();
  const [nodeInput, setNodeInput] = useState(node);
  const [manifestInput, setManifestInput] = useState(manifest ?? "");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [faucetMessage, setFaucetMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setNodeInput(node);
  }, [node]);
  useEffect(() => {
    setManifestInput(manifest ?? "");
  }, [manifest]);

  const balance = useQuery({
    queryKey: ["balance", address],
    enabled: status === "unlocked" && !!address,
    queryFn: async () =>
      parseRead<number>(await useWallet.getState().clientOrThrow().native_rev_balance(address!)),
  });

  const applyManifest = async () => {
    setBusy(true);
    setError(null);
    try {
      await setManifest(manifestInput);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const faucet = async () => {
    if (!address) return;
    setBusy(true);
    setFaucetMessage(null);
    setError(null);
    try {
      const result = await requestFaucet(profile, address);
      setFaucetMessage(result.message);
      if (result.ok) {
        // A faucet transfer is a deploy; wait until the balance actually moves.
        for (let attempt = 0; attempt < 12; attempt += 1) {
          await new Promise((resolve) => window.setTimeout(resolve, 1_500));
          const latest = await useWallet.getState().clientOrThrow().native_rev_balance(address);
          const amount = parseRead<number>(latest).data;
          if (amount > 0) break;
        }
        await queryClient.invalidateQueries({ queryKey: ["balance"] });
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const exportWallet = async () => {
    setBusy(true);
    setError(null);
    try {
      const document = await exportKeystore(password);
      const blob = new Blob([document], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = window.document.createElement("a");
      anchor.href = url;
      anchor.download = "rgen-keystore.json";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="stack">
      <Panel title={<h1>Settings</h1>}>
        <p className="muted small">
          The app has no server. The node and the Root manifest are the whole configuration.
          A manifest from another chain is refused by the readiness check.
        </p>
        <div className="grid two">
          <dl className="kv">
            <dt>profile</dt>
            <dd>{profile.name}</dd>
            <dt>node</dt>
            <dd className="mono small">{node}</dd>
            <dt>manifest URL</dt>
            <dd className="mono small">{manifestUrl(profile)}</dd>
            <dt>network id</dt>
            <dd>{readiness.networkId ?? "—"}</dd>
            <dt>shard</dt>
            <dd>{readiness.shard ?? "—"}</dd>
            <dt>readiness</dt>
            <dd><StatusPill status={readiness.state} /></dd>
          </dl>
          <div>
            <div className="row gap wrap">
              <button className="ghost" onClick={() => void setNode(DEVNET.node)}>
                Use local devnet
              </button>
              <button className="ghost" onClick={() => void setNode(TESTNET.node)}>
                Use public testnet
              </button>
              <button className="ghost" onClick={() => void refreshReadiness()}>
                Recheck
              </button>
            </div>
            <Field label="Node URL">
              <input
                value={nodeInput}
                onChange={(event) => setNodeInput(event.target.value)}
                className="mono"
              />
            </Field>
            <button disabled={busy || nodeInput === node} onClick={() => void setNode(nodeInput)}>
              Connect node
            </button>
          </div>
        </div>
        {readiness.error && <p className="error">{readiness.error}</p>}
      </Panel>

      <Panel title={<h2>Manifest</h2>}>
        <p className="muted small">
          Paste <code>deployments/[devnet,testnet].json</code> when the sync script has not
          run. The Root URI is the authority; component URIs are resolved from it.
        </p>
        <Field label="Manifest JSON">
          <textarea
            rows={8}
            value={manifestInput}
            onChange={(event) => setManifestInput(event.target.value)}
            className="mono"
          />
        </Field>
        <button className="primary" onClick={applyManifest} disabled={busy || !manifestInput}>
          Apply manifest
        </button>
      </Panel>

      <Panel title={<h2>Wallet and funding</h2>}>
        {status !== "unlocked" ? (
          <p className="muted">Unlock a wallet to use the faucet and export a keystore.</p>
        ) : (
          <>
            <dl className="kv">
              <dt>address</dt>
              <dd className="mono small">{address}</dd>
              <dt>native REV</dt>
              <dd>
                {balance.data?.data !== undefined
                  ? (balance.data.data / 1e8).toFixed(8)
                  : balance.isError
                    ? "unavailable"
                    : "…"}
              </dd>
              <dt>saved profiles</dt>
              <dd>{profiles.length}</dd>
            </dl>
            <div className="row gap wrap">
              <button className="ghost" onClick={faucet} disabled={busy}>
                Request faucet drip
              </button>
              <button className="ghost" onClick={lock}>
                Lock wallet
              </button>
            </div>
            {faucetMessage && <p className="muted small">{faucetMessage}</p>}
            <Field label="Keystore password" hint="to export the encrypted file">
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <button onClick={exportWallet} disabled={busy || password.length < 8}>
              Export keystore
            </button>
          </>
        )}
        <ErrorBox error={error} />
      </Panel>

      <Panel title={<h2>Resolved components</h2>}>
        {!readiness.components || Object.keys(readiness.components).length === 0 ? (
          <p className="muted">Resolve the Root to see the installed components.</p>
        ) : (
          <div className="list">
            {Object.entries(readiness.components).map(([key, component]) => (
              <div className="list-row" key={key}>
                <span className="mono small">{key}</span>
                <span className="mono small">
                  {component.uri} · v{component.version}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}
