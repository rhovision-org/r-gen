export type EntityKind =
  | "claim"
  | "kasset"
  | "credential"
  | "value"
  | "case"
  | "provenance"
  | "identity";

export interface ReadMeta {
  atHeight: number;
  blockHash: string;
  source: "explore" | "signedDeploy";
  deployId: string | null;
}

export interface Receipt {
  deployId: string;
  finalized: boolean;
  blockHash: string | null;
  blockNumber: number;
  termBytes: number;
  status: string;
}

export interface ReadEnvelope<T> {
  ok: true;
  data: T;
  read: ReadMeta;
}

export interface WriteEnvelope<T> {
  ok: true;
  data: T;
  deploy: Receipt;
}

export interface RefusalEnvelope {
  ok: false;
  code: string;
  message: string;
  refusal?: string;
  deploy?: Receipt;
  deployId?: string | null;
}

export type Envelope<T> = ReadEnvelope<T> | WriteEnvelope<T> | RefusalEnvelope;

/** A contract state map. Optional fields are absent when the chain has `Nil`. */
export type State = Record<string, unknown>;

export interface CatalogueEntry {
  kind: EntityKind;
  uri: string;
  label: string;
  detail?: string;
}

export interface Catalogue {
  networkId?: string;
  shard?: string;
  root?: string;
  generatedAt?: string;
  entries?: CatalogueEntry[];
  entities?: CatalogueEntry[];
}

export interface JournalEntry {
  id: string;
  kind: string;
  uri?: string;
  related?: string;
  opId?: string;
  deployId?: string;
  blockNumber?: number;
  status:
    | "submitted"
    | "finalized"
    | "refused"
    | "failed"
    | "unknown";
  refusal?: string;
  summary: string;
  createdAt: number;
}

export interface StoredKeystore {
  address: string;
  document: string;
  label: string;
  createdAt: number;
}

export interface IdentityState extends State {
  uri?: string;
  subject?: string;
  handle?: string;
  status?: string;
}

export interface CredentialState extends State {
  uri?: string;
  subject?: string;
  issuer?: string;
  ctype?: string;
  discipline?: string;
  jurisdiction?: string;
  role?: string;
  level?: number;
  status?: string;
  expiresAt?: number;
}

export interface ClaimState extends State {
  uri?: string;
  claimant?: string;
  status?: string;
  deadlineHeight?: number;
  commentUntilHeight?: number;
  kassetRef?: { id?: string; uri?: string };
  validationRef?: Record<string, unknown>;
}

export interface KAssetState extends State {
  uri?: string;
  status?: string;
  claimant?: string;
  validator?: string;
  claimRef?: { id?: string; uri?: string };
  valuePropositionRef?: { id?: string; uri?: string };
  approval?: Record<string, unknown>;
  dispute?: Record<string, unknown>;
}

export interface ValuePropositionState extends State {
  uri?: string;
  proposer?: string;
  validator?: string;
  status?: string;
  deadlineHeight?: number;
  dispute?: { id?: string; uri?: string };
}

export interface CaseState extends State {
  uri?: string;
  status?: string;
  adjudicator?: string;
  parties?: string[];
  decision?: Record<string, unknown>;
  execution?: Record<string, unknown>;
  deadlineHeight?: number;
}

export interface ProvenanceState extends State {
  uri?: string;
  assetRef?: { uri?: string };
  writers?: string[];
  anchors?: Array<Record<string, unknown>>;
}
