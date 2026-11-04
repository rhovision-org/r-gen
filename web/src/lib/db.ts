import type { JournalEntry, StoredKeystore } from "./types";

const DB_NAME = "rgen";
const DB_VERSION = 1;

function open(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("keystores")) {
        db.createObjectStore("keystores", { keyPath: "address" });
      }
      if (!db.objectStoreNames.contains("journal")) {
        db.createObjectStore("journal", { keyPath: "id" });
      }
      if (!db.objectStoreNames.contains("prefs")) {
        db.createObjectStore("prefs", { keyPath: "key" });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function all<T>(store: IDBObjectStore): Promise<T[]> {
  return new Promise((resolve, reject) => {
    const result = store.getAll();
    result.onsuccess = () => resolve(result.result as T[]);
    result.onerror = () => reject(result.error);
  });
}

export async function saveKeystore(
  address: string,
  document: string,
  label = "wallet",
): Promise<void> {
  const db = await open();
  const entry: StoredKeystore = {
    address,
    document,
    label,
    createdAt: Date.now(),
  };
  const tx = db.transaction("keystores", "readwrite");
  tx.objectStore("keystores").put(entry);
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function loadKeystore(address: string): Promise<StoredKeystore | undefined> {
  const db = await open();
  const tx = db.transaction("keystores", "readonly");
  const value = await new Promise<StoredKeystore | undefined>((resolve, reject) => {
    const result = tx.objectStore("keystores").get(address);
    result.onsuccess = () => resolve(result.result as StoredKeystore | undefined);
    result.onerror = () => reject(result.error);
  });
  db.close();
  return value;
}

export async function listKeystores(): Promise<StoredKeystore[]> {
  const db = await open();
  const tx = db.transaction("keystores", "readonly");
  const values = await all<StoredKeystore>(tx.objectStore("keystores"));
  db.close();
  return values;
}

export async function addJournal(entry: JournalEntry): Promise<void> {
  const db = await open();
  const tx = db.transaction("journal", "readwrite");
  tx.objectStore("journal").put(entry);
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}

export async function listJournal(): Promise<JournalEntry[]> {
  const db = await open();
  const tx = db.transaction("journal", "readonly");
  const values = await all<JournalEntry>(tx.objectStore("journal"));
  db.close();
  return values.sort((left, right) => right.createdAt - left.createdAt);
}

export async function getPref<T>(key: string): Promise<T | undefined> {
  const db = await open();
  const tx = db.transaction("prefs", "readonly");
  const value = await new Promise<{ key: string; value: T } | undefined>(
    (resolve, reject) => {
      const result = tx.objectStore("prefs").get(key);
      result.onsuccess = () => resolve(result.result as { key: string; value: T } | undefined);
      result.onerror = () => reject(result.error);
    },
  );
  db.close();
  return value?.value;
}

export async function setPref<T>(key: string, value: T): Promise<void> {
  const db = await open();
  const tx = db.transaction("prefs", "readwrite");
  tx.objectStore("prefs").put({ key, value });
  await new Promise<void>((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
  db.close();
}
