import RGen.Invariants

/-!
# Conformance corpus emitter

The vectors in `spec/vectors/core.tsv` are emitted from this table; no other
file is the source of truth. Each row names the deployed primitive and arm, the
input class, the expected outcome, and the Lean declaration that justifies it.

`lake exe rgen-emit` writes `../vectors/core.tsv`; `--stdout` prints the table
so `tools/check_vectors.py` can compare it with the checked-in file.
-/

namespace RGen

structure VectorRow where
  caseId : String
  primitive : String
  arm : String
  input : String
  expected : String
  leanDecl : String

def coreRows : List VectorRow :=
  [ ⟨"D1-peek-put", "linear", "peek-then-put", "nonempty cell", "reject", "RGen.D1_peek_put"⟩
  , ⟨"D1-put-no-take", "linear", "put", "empty not held", "reject", "RGen.D1_put_without_take"⟩
  , ⟨"D2-take-no-put", "linear", "take", "trace ends holding", "not-wf", "RGen.D2_take_without_put"⟩
  , ⟨"D3-call-held", "linear", "call", "held cell", "reject", "RGen.D3_nested_call"⟩
  , ⟨"C1-prove-revoked", "credential", "prove", "revoked credential", "none", "RGen.C2_revoke_blocks_prove"⟩
  , ⟨"C1-prove-wrong-subject", "credential", "prove", "caller not subject", "none", "RGen.CredentialState.prove_wrong_subject"⟩
  , ⟨"C1-prove-active", "credential", "prove", "active credential", "some", "RGen.C1_prove_requires_active"⟩
  , ⟨"V1-validate-twice", "value", "validate", "second validate", "none", "RGen.V1_validate_once"⟩
  , ⟨"V2-prove-disputed", "value", "proveValidated", "disputed proposition", "none", "RGen.V2_dispute_blocks_prove"⟩
  , ⟨"K1-approve-self", "kasset", "approve", "approver is claimant", "none", "RGen.KAssetState.approve_by_claimant_refused"⟩
  , ⟨"K1-approve-proof", "kasset", "approve", "credential proof subject", "approver", "RGen.K1_approve_credential"⟩
  , ⟨"K2-approve-status", "kasset", "approve", "approved already", "none", "RGen.K2_approve_status"⟩
  , ⟨"K3-nest-unsorted", "kasset", "nest", "children not rising", "none", "RGen.KAssetState.nest_refused_unsorted"⟩
  , ⟨"K3-nest-acyclic", "kasset", "nest", "any child set", "acyclic", "RGen.K3_nest_acyclic"⟩
  , ⟨"O1-execute-twice", "oracle", "execute", "second execute", "already executed", "RGen.O1_execute_bound_once"⟩
  , ⟨"C1-claim-validate-once", "claim", "validate", "second validate", "none", "RGen.ClaimState.validate_once"⟩
  , ⟨"O2-close-open", "oracle", "close", "open case", "none", "RGen.OracleState.close_open_refused"⟩
  , ⟨"P1-anchor-duplicate", "provenance", "anchor", "existing anchor", "none", "RGen.ProvenanceState.addAnchor_refused_duplicate"⟩
  , ⟨"P1-anchor-append", "provenance", "anchor", "existing anchors", "preserved", "RGen.P1_anchors_append_only"⟩
  , ⟨"L1-disjoint-commute", "linear", "interleave", "disjoint footprints", "commute", "RGen.L1_disjoint_commute"⟩
  , ⟨"L2-same-cell-serialize", "linear", "interleave", "same cell", "compose", "RGen.L2_shared_serializes"⟩
  , ⟨"L3-acquire-acyclic", "concurrency", "acquire", "any acquisition", "no-cycle", "RGen.L3_mayAcquire_acyclic"⟩
  ]

def renderRows (rows : List VectorRow) : String :=
  let header := "case_id\tprimitive\tarm\tinput\texpected\tlean_decl"
  let line := fun r => s!"{r.caseId}\t{r.primitive}\t{r.arm}\t{r.input}\t{r.expected}\t{r.leanDecl}"
  String.intercalate "\n" (header :: rows.map line) ++ "\n"

end RGen

open RGen

/-- Print the corpus to stdout. The Python tool owns the file write. -/
def main : IO Unit :=
  IO.print (renderRows coreRows)
