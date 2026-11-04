import RGen.Arms.Basic
import RGen.Model.KAsset

/-!
# K-Asset arm pairs

Approve and reject are two-way exclusive from validated/conditional. Prove-approved and
dispute are ordered: dispute-first refuses the proof, proof-first is a non-retroactive
snapshot. Nesting the same child twice is refused by the existing-children guard; the
second nest sees the first's appended child list.
-/

namespace RGen

structure KApproveArgs where
  approver : Id
  credProof : ProofData
  vpProof : ProofData
  atHeight : Height

structure KRejectArgs where
  approver : Id
  credProof : ProofData
  atHeight : Height

def kassetApprove (s : KAssetState) (a : KApproveArgs) : Option KAssetState :=
  s.approve a.approver a.credProof a.vpProof a.atHeight

def kassetReject (s : KAssetState) (a : KRejectArgs) : Option KAssetState :=
  s.reject a.approver a.credProof a.atHeight

def kassetProveApproved (s : KAssetState) (uri : Id) : Option KAssetState :=
  match s.proveApproved uri with
  | none => none
  | some _ => some s

def kassetOpenDispute (s : KAssetState) (caller caseId : Id) : Option KAssetState :=
  s.openDispute caller caseId

def kassetDecision (s : KAssetState) (caseId : Id) (d : VPDecision) : Option KAssetState :=
  s.applyDecision caseId d

def kassetNest (s : KAssetState) (caller : Id) (children : List ApprovedProofData) :
    Option KAssetState :=
  s.nest caller children

theorem kasset_approve_approve_never_after {a : KApproveArgs} :
    NeverAfter (fun s => kassetApprove s a) (fun s => kassetApprove s a) := by
  intro s s1 h
  exact KAssetState.approve_once h

theorem kasset_approve_reject_never_after {a : KApproveArgs} {b : KRejectArgs} :
    NeverAfter (fun s => kassetApprove s a) (fun s => kassetReject s b) := by
  intro s s1 ha
  have hs := KAssetState.approve_sets_status ha
  simp [kassetReject, KAssetState.reject, hs]

theorem kasset_reject_approve_never_after {a : KRejectArgs} {b : KApproveArgs} :
    NeverAfter (fun s => kassetReject s a) (fun s => kassetApprove s b) := by
  intro s s1 hr
  have hs := KAssetState.reject_sets_status hr
  simp [kassetApprove, KAssetState.approve, hs]

theorem kasset_approve_reject_two_way {a : KApproveArgs} {b : KRejectArgs} :
    TwoWayExclusive (fun s => kassetApprove s a) (fun s => kassetReject s b) :=
  ⟨kasset_approve_reject_never_after, kasset_reject_approve_never_after⟩

theorem kasset_reject_reject_never_after {a : KRejectArgs} :
    NeverAfter (fun s => kassetReject s a) (fun s => kassetReject s a) := by
  intro s s1 h
  exact KAssetState.reject_once h

theorem kasset_openDispute_approve_never_after {party caseId : Id} {a : KApproveArgs} :
    NeverAfter (fun s => kassetOpenDispute s party caseId) (fun s => kassetApprove s a) := by
  intro s s1 hd
  have hs := KAssetState.openDispute_sets_status hd
  simp [kassetApprove, KAssetState.approve, hs]

theorem kasset_openDispute_proveApproved_never_after {party caseId uri : Id} :
    NeverAfter (fun s => kassetOpenDispute s party caseId)
      (fun s => kassetProveApproved s uri) := by
  intro s s1 hd
  have hs := KAssetState.openDispute_sets_status hd
  cases ha : s1.approver <;> simp [kassetProveApproved, KAssetState.proveApproved, ha, hs]

theorem kasset_openDispute_openDispute_never_after {party caseId party' caseId' : Id} :
    NeverAfter (fun s => kassetOpenDispute s party caseId)
      (fun s => kassetOpenDispute s party' caseId') := by
  intro s s1 h
  exact KAssetState.openDispute_once h

theorem kasset_decision_decision_never_after {caseId : Id} {d : VPDecision} :
    NeverAfter (fun s => kassetDecision s caseId d) (fun s => kassetDecision s caseId d) := by
  intro s s1 h
  exact KAssetState.decision_once h

theorem kasset_nest_same_never_after {s : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s')
    (hne : children ≠ []) : s'.nest caller children = none := by
  have hchild : s'.children = s.children ++ children.map (fun c => c.id) := by
    unfold KAssetState.nest at h
    split at h
    · simp only [Option.some.injEq] at h
      rcases h with rfl
      rfl
    · simp at h
  have hfalse : KAssetState.idsNotIn s'.children children = false := by
    rw [hchild]
    exact KAssetState.idsNotIn_append_self s.children children hne
  unfold KAssetState.nest
  simp [hfalse]

theorem kasset_nest_same_never_after_arm {caller : Id} {children : List ApprovedProofData}
    (hne : children ≠ []) :
    ∀ s s1, kassetNest s caller children = some s1 →
      kassetNest s1 caller children = none := by
  intro s s1 h
  exact kasset_nest_same_never_after h hne

end RGen
