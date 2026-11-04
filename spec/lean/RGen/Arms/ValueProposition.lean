import RGen.Arms.Basic
import RGen.Model.ValueProposition

/-!
# Value-proposition arm pairs

`validate` moves proposed to validated; `withdraw` is proposed-only; `openDispute`
accepts proposed or validated. Validate-then-validate and withdraw/validate are
exclusive. Dispute-first refuses validation and proveValidated; proveValidated-then-dispute
is the ordered, non-retroactive case.
-/

namespace RGen

structure VPValidateArgs where
  validator : Id
  proof : ProofData

def vpValidate (s : VPState) (a : VPValidateArgs) : Option VPState :=
  s.validate a.validator a.proof

def vpWithdraw (s : VPState) (proposer : Id) : Option VPState :=
  s.withdraw proposer

def vpOpenDispute (s : VPState) (party caseId : Id) : Option VPState :=
  s.openDispute party caseId

def vpProveValidated (s : VPState) (uri : Id) (atHeight : Height) (caller : Id) : Option VPState :=
  match s.proveValidated uri atHeight caller with
  | none => none
  | some _ => some s

def vpDecision (s : VPState) (caseId : Id) (d : VPDecision) : Option VPState :=
  s.applyDecision caseId d

theorem vp_validate_validate_never_after {a : VPValidateArgs} :
    NeverAfter (fun s => vpValidate s a) (fun s => vpValidate s a) := by
  intro s s1 h
  exact VPState.validate_once h

theorem vp_validate_withdraw_never_after {a : VPValidateArgs} {proposer : Id} :
    NeverAfter (fun s => vpValidate s a) (fun s => vpWithdraw s proposer) := by
  intro s s1 hv
  have hs := VPState.validate_sets_status hv
  simp [vpWithdraw, VPState.withdraw, hs]

theorem vp_withdraw_validate_never_after {proposer : Id} {a : VPValidateArgs} :
    NeverAfter (fun s => vpWithdraw s proposer) (fun s => vpValidate s a) := by
  intro s s1 hw
  have hs := VPState.withdraw_sets_status hw
  simp [vpValidate, VPState.validate, hs]

theorem vp_validate_withdraw_two_way {a : VPValidateArgs} {proposer : Id} :
    TwoWayExclusive (fun s => vpValidate s a) (fun s => vpWithdraw s proposer) :=
  ⟨vp_validate_withdraw_never_after, vp_withdraw_validate_never_after⟩

/-- Dispute-first refuses validation: the ordered pair. -/
theorem vp_validate_openDispute_ordered {a : VPValidateArgs} {party caseId : Id} :
    OrderedAfter (fun s => vpValidate s a) (fun s => vpOpenDispute s party caseId) := by
  intro s s1 hd
  have hs := VPState.openDispute_sets_status hd
  simp [vpValidate, VPState.validate, hs]

theorem vp_proveValidated_openDispute_ordered {uri : Id} {atHeight : Height}
    {caller party caseId : Id} :
    OrderedAfter (fun s => vpProveValidated s uri atHeight caller)
      (fun s => vpOpenDispute s party caseId) := by
  intro s s1 hd
  dsimp only [vpOpenDispute] at hd
  have hs := VPState.prove_after_dispute (uri := uri) (atHeight := atHeight) (proofCaller := caller) hd
  simp [vpProveValidated, hs]

theorem vp_decision_decision_never_after {caseId : Id} {d : VPDecision} :
    NeverAfter (fun s => vpDecision s caseId d) (fun s => vpDecision s caseId d) := by
  intro s s1 h
  exact VPState.decision_once h

end RGen
