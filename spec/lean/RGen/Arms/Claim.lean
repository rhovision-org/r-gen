import RGen.Arms.Basic
import RGen.Model.Claim

/-!
# Claim arm pairs

`validate` is terminal (validated or expired); `withdraw`, `expire`, and `reject` are
terminal. Any two of the terminal transitions are two-way exclusive. Comments append and
preserve status, so comment-then-comment is serialized with no lost update; validate-first
makes a later comment refuse.
-/

namespace RGen

structure ClaimValidateArgs where
  validator : Id
  proof : ProofData
  atHeight : Height
  kassetId : Id

def claimValidate (s : ClaimState) (a : ClaimValidateArgs) : Option ClaimState :=
  s.validate a.validator a.proof a.atHeight a.kassetId

def claimWithdraw (s : ClaimState) (claimant : Id) : Option ClaimState :=
  s.withdraw claimant

def claimExpire (s : ClaimState) (h : Height) : Option ClaimState :=
  s.expire h

def claimReject (s : ClaimState) (a : ClaimValidateArgs) : Option ClaimState :=
  s.reject a.validator a.proof a.atHeight

def claimComment (s : ClaimState) (commentId : Id) (atHeight : Height) : Option ClaimState :=
  s.comment commentId atHeight

theorem claim_validate_validate_never_after {a : ClaimValidateArgs} :
    NeverAfter (fun s => claimValidate s a) (fun s => claimValidate s a) := by
  intro s s1 h
  exact ClaimState.validate_once h

theorem claim_validate_withdraw_never_after {a : ClaimValidateArgs} {claimant : Id} :
    NeverAfter (fun s => claimValidate s a) (fun s => claimWithdraw s claimant) := by
  intro s s1 hv
  have hs := ClaimState.validate_status hv
  rcases hs with hs | hs <;> simp [claimWithdraw, ClaimState.withdraw, hs]

theorem claim_withdraw_validate_never_after {claimant : Id} {a : ClaimValidateArgs} :
    NeverAfter (fun s => claimWithdraw s claimant) (fun s => claimValidate s a) := by
  intro s s1 hw
  have hs := ClaimState.withdraw_sets_status hw
  simp [claimValidate, ClaimState.validate, hs]

theorem claim_validate_withdraw_two_way {a : ClaimValidateArgs} {claimant : Id} :
    TwoWayExclusive (fun s => claimValidate s a) (fun s => claimWithdraw s claimant) :=
  ⟨claim_validate_withdraw_never_after, claim_withdraw_validate_never_after⟩

theorem claim_validate_expire_never_after {a : ClaimValidateArgs} {hgt : Height} :
    NeverAfter (fun s => claimValidate s a) (fun s => claimExpire s hgt) := by
  intro s s1 hv
  have hs := ClaimState.validate_status hv
  rcases hs with hs | hs <;> simp [claimExpire, ClaimState.expire, hs]

theorem claim_expire_validate_never_after {hgt : Height} {a : ClaimValidateArgs} :
    NeverAfter (fun s => claimExpire s hgt) (fun s => claimValidate s a) := by
  intro s s1 he
  have hs := ClaimState.expire_sets_status he
  simp [claimValidate, ClaimState.validate, hs]

theorem claim_validate_expire_two_way {a : ClaimValidateArgs} {hgt : Height} :
    TwoWayExclusive (fun s => claimValidate s a) (fun s => claimExpire s hgt) :=
  ⟨claim_validate_expire_never_after, claim_expire_validate_never_after⟩

theorem claim_validate_reject_never_after {a : ClaimValidateArgs} :
    NeverAfter (fun s => claimValidate s a) (fun s => claimReject s a) := by
  intro s s1 hv
  have hs := ClaimState.validate_status hv
  rcases hs with hs | hs <;> simp [claimReject, ClaimState.reject, hs]

theorem claim_reject_validate_never_after {a : ClaimValidateArgs} :
    NeverAfter (fun s => claimReject s a) (fun s => claimValidate s a) := by
  intro s s1 hr
  have hs := ClaimState.reject_sets_status hr
  simp [claimValidate, ClaimState.validate, hs]

theorem claim_validate_reject_two_way {a : ClaimValidateArgs} :
    TwoWayExclusive (fun s => claimValidate s a) (fun s => claimReject s a) :=
  ⟨claim_validate_reject_never_after, claim_reject_validate_never_after⟩

/-- Validate-first refuses a later comment. -/
theorem claim_validate_blocks_comment {a : ClaimValidateArgs} {commentId : Id}
    {atHeight : Height} :
    NeverAfter (fun s => claimValidate s a) (fun s => claimComment s commentId atHeight) := by
  intro s s1 hv
  have hs := ClaimState.validate_status hv
  rcases hs with hs | hs <;> simp [claimComment, ClaimState.comment, hs]

theorem claim_expire_blocks_comment {hgt : Height} {commentId : Id} {atHeight : Height} :
    NeverAfter (fun s => claimExpire s hgt) (fun s => claimComment s commentId atHeight) := by
  intro s s1 he
  have hs := ClaimState.expire_sets_status he
  simp [claimComment, ClaimState.comment, hs]

/-- Two comments serialize; the second is computed from the first's post-state and both
hashes are present. -/
theorem claim_comment_comment_appends {s s1 s2 : ClaimState} {c1 c2 : Id} {h1 h2 : Height}
    (hc1 : s.comment c1 h1 = some s1) (hc2 : s1.comment c2 h2 = some s2) :
    s2.comments = c2 :: c1 :: s.comments := by
  rw [ClaimState.comment_appends hc2, ClaimState.comment_appends hc1]

end RGen
