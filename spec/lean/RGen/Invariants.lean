import RGen.Composition
import RGen.Model.Credential
import RGen.Model.Issuer

/-!
# Stable invariant names

These aliases are the vocabulary the flow manifest and the conformance corpus
refer to. Each name is a theorem, not a restatement: the alias adds no
assumption.

* `D1`–`D3` — the linear-discipline rejection laws.
* `C*` — credential proof guards and revocation.
* `V*` — value-proposition transitions.
* `K*` — K-Asset approval, nesting, and disputes.
* `O*` — oracle decision and execution.
* `P*` — provenance append-only.
* `L1`–`L4` — independence, serialization, acquisition acyclicity, rank deadlock freedom.
-/

namespace RGen

/-! ### D1–D3 -/

/-- D1: a peek followed by a put is not a committed update. -/
theorem D1_peek_put {α : Type} {s : Store α} {h : List CellId} {c : CellId} {v : α}
    (hne : s.cells c ≠ []) : run s h [Op.peek c, Op.put c v] = none :=
  peek_then_put_rejected hne

/-- D1: a put with no take is refused. -/
theorem D1_put_without_take {α : Type} {s : Store α} {h : List CellId} {c : CellId} {v : α}
    (hempty : s.cells c = []) (hnot : c ∉ h) : run s h [Op.put c v] = none :=
  put_without_take_rejected hempty hnot

/-- D2: a take with no put is not well formed. -/
theorem D2_take_without_put {α : Type} {s : Store α} {h : List CellId} {c : CellId} {v : α}
    (hcell : s.cells c = [v]) : ¬ WF s h [Op.take c] :=
  take_without_put_not_wf hcell

/-- D3: a call on a held cell is blocked. -/
theorem D3_nested_call {α : Type} {s : Store α} {h : List CellId} {c : CellId}
    (hheld : c ∈ h) : run s h [Op.call c] = none :=
  nested_call_rejected hheld

/-! ### C — credentials -/

/-- C1: a proof requires an active credential at the stated height. -/
theorem C1_prove_requires_active {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {h : Height}
    {p : ProofState ProofData}
    (hp : c.prove proofUri credentialUri issuerScope caller r h = some p) :
    CredentialState.activeAt c h = true :=
  CredentialState.prove_requires_active hp

/-- C2: a revoked credential cannot prove. -/
theorem C2_revoke_blocks_prove {c c' : CredentialState} {caller caller' : Id}
    {issuerScope : IssuerScope} {proofUri credentialUri : Id} {r : Requirement} {h : Height}
    (hr : c.revoke caller = some c') :
    c'.prove proofUri credentialUri issuerScope caller' r h = none :=
  CredentialState.prove_after_revoke hr

/-- C3: the issuer is immutable. -/
theorem C3_issuer_immutable {i j : Issuer} (h : Issuer.IssuerStep i j) : False :=
  Issuer.issuer_immutable h

/-! ### V — value propositions -/

/-- V1: a proposition validates once. -/
theorem V1_validate_once {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : s'.validate validator proof = none :=
  VPState.validate_once h

/-- V2: a disputed proposition cannot be proved validated. -/
theorem V2_dispute_blocks_prove {s s' : VPState} {caller caseId uri : Id} {atHeight : Height}
    (h : s.openDispute caller caseId = some s') :
    s'.proveValidated uri atHeight = none :=
  VPState.prove_after_dispute h

/-! ### K — K-Assets -/

/-- K1: approval requires the credential proof's subject to be the approver. -/
theorem K1_approve_credential {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    credProof.subject = approver :=
  KAssetState.approve_requires_credential_proof h

/-- K2: approval is only from validated or conditional. -/
theorem K2_approve_status {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional :=
  KAssetState.approve_only_from_validated_or_conditional h

/-- K3: nest requires strict order and is acyclic. -/
theorem K3_nest_acyclic {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    KAssetState.strictRising (children.map KAssetState.childKey) = true ∧
      (∀ a, ¬ Relation.TransGen KAssetState.NestStep a a) :=
  nesting_is_a_forest_with_strict_order h

/-! ### O — oracle -/

/-- O1: execution is subject-bound and one-shot. -/
theorem O1_execute_bound_once {s s' : OracleState} {caller caller' : Id}
    (h : s.execute caller = some s') :
    caller = s.subject ∧ s'.execute caller' = none :=
  ⟨OracleState.execute_subject_bound h, OracleState.execute_once h⟩

/-- O2: closing requires a finished case. -/
theorem O2_close_finished {s s' : OracleState} (h : s.close = some s') :
    s.status = OracleStatus.executed ∨ s.status = OracleStatus.expired :=
  OracleState.close_requires_finished h

/-! ### P — provenance -/

/-- P1: anchors are append-only. -/
theorem P1_anchors_append_only {s s' : ProvenanceState} {caller : Id} {a b : Id × Id}
    (h : s.addAnchor caller a = some s') (hb : b ∈ s.anchors) : b ∈ s'.anchors :=
  provenance_is_append_only h hb

/-! ### L — concurrency -/

/-- L1: traces with disjoint footprints commute on the store. -/
theorem L1_disjoint_commute {α : Type} (s : Store α) (h : List CellId)
    (ops1 ops2 : List (Op α)) (hd : FootprintDisjoint ops1 ops2) :
    (run s h (ops1 ++ ops2)).map Prod.fst = (run s h (ops2 ++ ops1)).map Prod.fst :=
  disjoint_cells_commute s h ops1 ops2 hd

/-- L2: two commits on the same cell serialize. -/
theorem L2_shared_serializes {α : Type} (w : World α) (c : CellId)
    (f1 f2 : α → Option α) :
    (w.commit c f1).bind (fun w' => w'.commit c f2)
      = w.commit c (fun v => (f1 v).bind f2) :=
  shared_serializes w c f1 f2

/-- L3: the acquisition relation is acyclic. -/
theorem L3_mayAcquire_acyclic {a : CellKind} (h : Relation.TransGen MayAcquire a a) : False :=
  mayAcquire_acyclic h

/-- L4: rank-decreasing wait edges admit no cycle. -/
theorem L4_deadlock_free {σ : Type} (rank : σ → Nat) (wait : σ → σ → Prop)
    (hdec : ∀ a b, wait a b → rank b < rank a) :
    ∀ a, ¬ Relation.TransGen wait a a :=
  deadlock_free_of_rank rank wait hdec

end RGen
