import { useEffect, useState } from "react";
import { useWallet } from "../lib/store";
import { ErrorBox, Field } from "./ui";

type Mode = "unlock" | "create" | "import";

function download(document: string) {
  const blob = new Blob([document], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = window.document.createElement("a");
  anchor.href = url;
  anchor.download = "rgen-keystore.json";
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function Unlock() {
  const {
    status,
    profiles,
    refreshProfiles,
    createWallet,
    unlock,
    switchProfile,
    unlockOpen,
    closeUnlock,
  } = useWallet();
  const [mode, setMode] = useState<Mode>("unlock");
  const [selected, setSelected] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [documentText, setDocumentText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void refreshProfiles();
  }, [refreshProfiles]);

  useEffect(() => {
    if (!selected && profiles[0]) setSelected(profiles[0].address);
  }, [profiles, selected]);

  if (status !== "locked" || !unlockOpen) return null;

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const create = () =>
    run(async () => {
      if (password.length < 8) throw new Error("use at least 8 characters");
      if (password !== confirm) throw new Error("passwords do not match");
      const document = await createWallet(password, "wallet");
      download(document);
      setPassword("");
      setConfirm("");
    });

  const open = () =>
    run(async () => {
      if (!selected) throw new Error("choose a saved wallet");
      await switchProfile(selected, password);
      setPassword("");
    });

  const importDocument = () =>
    run(async () => {
      if (password.length < 8) throw new Error("use at least 8 characters");
      await unlock(documentText.trim(), password);
      setPassword("");
      setDocumentText("");
    });

  return (
    <div className="overlay">
      <div className="panel unlock">
        <div className="panel-head">
          <div>
            <h2>Wallet</h2>
            <p className="muted small">
              The key stays in the WASM module. Only the encrypted keystore is stored in
              this browser.
            </p>
          </div>
        </div>

        <div className="segmented">
          <button
            className={mode === "unlock" ? "active" : ""}
            onClick={() => setMode("unlock")}
            type="button"
          >
            Unlock
          </button>
          <button
            className={mode === "create" ? "active" : ""}
            onClick={() => setMode("create")}
            type="button"
          >
            Create
          </button>
          <button
            className={mode === "import" ? "active" : ""}
            onClick={() => setMode("import")}
            type="button"
          >
            Import
          </button>
        </div>

        {mode === "unlock" && (
          <>
            {profiles.length === 0 ? (
              <p className="muted">
                No saved wallets. Create one, or import a keystore from the demo bundle.
              </p>
            ) : (
              <>
                <Field label="Saved wallet">
                  <select value={selected} onChange={(event) => setSelected(event.target.value)}>
                    {profiles.map((profile) => (
                      <option key={profile.address} value={profile.address}>
                        {profile.label} · {profile.address.slice(0, 10)}…
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Password">
                  <input
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    onKeyDown={(event) => event.key === "Enter" && void open()}
                  />
                </Field>
                <button className="primary" onClick={open} disabled={busy}>
                  Unlock wallet
                </button>
              </>
            )}
          </>
        )}

        {mode === "create" && (
          <>
            <Field label="Password" hint="at least 8 characters">
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <Field label="Confirm password">
              <input
                type="password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
              />
            </Field>
            <button className="primary" onClick={create} disabled={busy}>
              Create wallet
            </button>
            <p className="muted small">
              The encrypted keystore downloads when it is created. Keep it; this browser
              also stores a copy in IndexedDB.
            </p>
          </>
        )}

        {mode === "import" && (
          <>
            <Field label="Keystore JSON">
              <textarea
                rows={6}
                value={documentText}
                onChange={(event) => setDocumentText(event.target.value)}
                placeholder='{"version":3,...}'
              />
            </Field>
            <Field label="Password">
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </Field>
            <button className="primary" onClick={importDocument} disabled={busy}>
              Import and unlock
            </button>
          </>
        )}

        <ErrorBox error={error} />
        <button className="ghost browse" onClick={closeUnlock} type="button">
          Browse without a wallet
        </button>
        <p className="muted small">
          Reads are free. Creating, validating and approving need an unlocked, funded
          wallet.
        </p>
      </div>
    </div>
  );
}
