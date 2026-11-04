import RGen.Concurrency
import RGen.Model.Claim
import RGen.Model.KAsset
import RGen.Model.Oracle
import RGen.Model.Provenance

/-!
# Composition of primitive guarantees

The primitives compose because each guarantee is local to one entity and the
only cross-entity reads are one-shot proofs. These theorems restate the composed
claims that the deployed arms are checked against.
-/

namespace RGen

/-- A validated claim has exactly one K-Asset reference. -/
theorem claim_validation_exactly_one_kasset {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) :
    ∃ k, s'.kassetRef = some k :=
  ClaimState.validate_creates_exactly_one_kasset h hs

/-- Approval composes a credential proof and a value-proposition proof, both
bound to the approver. -/
theorem approval_composes_credential_and_vp_proofs {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    credProof.subject = approver ∧ vpProof.subject = approver ∧
      vpProof.requirement.ctype = "ValueProposition" := by
  obtain ⟨hv, hc⟩ := KAssetState.approve_requires_vp_proof h
  exact ⟨KAssetState.approve_requires_credential_proof h, hv, hc⟩

/-- Nesting is a forest: strict `(approvedAt, id)` order and no nesting cycle. -/
theorem nesting_is_a_forest_with_strict_order {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    KAssetState.strictRising (children.map KAssetState.childKey) = true ∧
      (∀ a, ¬ Relation.TransGen KAssetState.NestStep a a) :=
  ⟨KAssetState.nest_requires_order h, fun _ => KAssetState.nest_acyclic⟩

/-- Oracle execution is subject-bound and one-shot. -/
theorem oracle_execution_exactly_once_and_subject_bound {s s' : OracleState}
    {caller caller' : Id} (h : s.execute caller = some s') :
    caller = s.subject ∧ s'.subject = s.subject ∧ s'.execute caller' = none :=
  ⟨OracleState.execute_subject_bound h, OracleState.execute_preserves_subject h,
   OracleState.execute_once h⟩

/-- Provenance anchors are append-only. -/
theorem provenance_is_append_only {s s' : ProvenanceState} {caller : Id}
    {a b : Id × Id} (h : s.addAnchor caller a = some s') (hb : b ∈ s.anchors) :
    b ∈ s'.anchors :=
  ProvenanceState.anchors_append_only h hb

/-- An example composed guarantee: independence of commits plus one-shot proofs. -/
theorem composed_invariants {α : Type} (w : World α) (c1 c2 : CellId)
    (f1 f2 : α → Option α) (hne : c1 ≠ c2) (p : ProofState α) (hused : p.used = true) :
    ((w.commit c1 f1).bind (fun w' => w'.commit c2 f2)
        = (w.commit c2 f2).bind (fun w' => w'.commit c1 f1)) ∧
      p.take = none :=
  ⟨independent_commute w c1 c2 f1 f2 hne, proof_one_shot p hused⟩

end RGen
