import RGen.Basic
import RGen.Model.Types
import RGen.Model.Proof

/-!
# Claim

A claim is open until it is validated, rejected, withdrawn, or expired. All four
ends are terminal. Validation requires a non-claimant validator, a height within
the deadline, a credential proof whose subject and requirement match, and an
unset K-Asset reference. A successful validation creates exactly one K-Asset
reference and that reference is never rewritten.
-/

namespace RGen

inductive ClaimStatus where
  | open
  | validated
  | rejected
  | withdrawn
  | expired
  deriving DecidableEq, Repr

structure ClaimState where
  uri : Id
  claimant : Id
  requirement : Requirement
  deadline : Height
  status : ClaimStatus
  validator : Option Id
  kassetRef : Option Id
  commentUntilHeight : Height
  comments : List Id
  deriving DecidableEq, Repr

namespace ClaimState

def IsTerminal (s : ClaimState) : Prop :=
  s.status = ClaimStatus.validated ∨ s.status = ClaimStatus.rejected ∨
    s.status = ClaimStatus.withdrawn ∨ s.status = ClaimStatus.expired

def validate (s : ClaimState) (validator : Id) (proof : ProofData) (atHeight : Height)
    (kassetId : Id) : Option ClaimState :=
  if s.status = ClaimStatus.open ∧ s.deadline < atHeight then
    some { s with status := ClaimStatus.expired, validator := some validator }
  else if s.status = ClaimStatus.open ∧ validator ≠ s.claimant ∧ atHeight ≤ s.deadline ∧
      proof.subject = validator ∧ proof.requirement = s.requirement ∧
      s.kassetRef = none then
    some { s with status := ClaimStatus.validated, validator := some validator, kassetRef := some kassetId }
  else none

/-- Append a comment while the claim is open and inside the comment window. -/
def comment (s : ClaimState) (commentId : Id) (atHeight : Height) : Option ClaimState :=
  if s.status = ClaimStatus.open ∧ atHeight ≤ s.commentUntilHeight then
    some { s with comments := commentId :: s.comments }
  else none

def reject (s : ClaimState) (validator : Id) (proof : ProofData) (atHeight : Height) :
    Option ClaimState :=
  if s.status = ClaimStatus.open ∧ validator ≠ s.claimant ∧ atHeight ≤ s.deadline ∧
      proof.subject = validator ∧ proof.requirement = s.requirement then
    some { s with status := ClaimStatus.rejected, validator := some validator }
  else none

def withdraw (s : ClaimState) (caller : Id) : Option ClaimState :=
  if caller = s.claimant ∧ s.status = ClaimStatus.open then
    some { s with status := ClaimStatus.withdrawn }
  else none

def expire (s : ClaimState) (h : Height) : Option ClaimState :=
  if s.status = ClaimStatus.open ∧ s.deadline < h then
    some { s with status := ClaimStatus.expired }
  else none

/-! ### Guards -/

theorem validate_requires_open {s s' : ClaimState} {validator : Id} {proof : ProofData}
    {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s') :
    s.status = ClaimStatus.open := by
  unfold validate at h
  split at h
  · rename_i hg
    exact hg.1
  · split at h
    · rename_i hg
      exact hg.1
    · simp at h

/-- A successful validation either validates or expires the claim. -/
theorem validate_status {s s' : ClaimState} {validator : Id} {proof : ProofData}
    {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s') :
    s'.status = ClaimStatus.validated ∨ s'.status = ClaimStatus.expired := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact Or.inr rfl
  · split at h
    · simp only [Option.some.injEq] at h
      rcases h with rfl
      exact Or.inl rfl
    · simp at h

theorem validate_expired_after_deadline {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.expired) : s.deadline < atHeight := by
  unfold validate at h
  split at h
  · rename_i hg
    exact hg.2
  · split at h
    · simp only [Option.some.injEq] at h
      rcases h with rfl
      simp at hs
    · simp at h

theorem validate_requires_non_claimant {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) : validator ≠ s.claimant := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp at hs
  · split at h
    · rename_i hg
      exact hg.2.1
    · simp at h

theorem validate_within_deadline {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) : atHeight ≤ s.deadline := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp at hs
  · split at h
    · rename_i hg
      exact hg.2.2.1
    · simp at h

theorem validate_requires_subject {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) : proof.subject = validator := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp at hs
  · split at h
    · rename_i hg
      exact hg.2.2.2.1
    · simp at h

theorem validate_requires_no_kasset {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) : s.kassetRef = none := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp at hs
  · split at h
    · rename_i hg
      exact hg.2.2.2.2.2
    · simp at h

/-! ### Once-only and exactly-one-K-Asset -/

theorem validate_sets_kasset {s s' : ClaimState} {validator : Id} {proof : ProofData}
    {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) : s'.kassetRef = some kassetId := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp at hs
  · split at h
    · simp only [Option.some.injEq] at h
      rcases h with rfl
      rfl
    · simp at h

theorem validate_once {s s' : ClaimState} {validator : Id} {proof : ProofData}
    {atHeight : Height} {kassetId : Id} {validator' : Id} {proof' : ProofData}
    {atHeight' : Height} {kassetId' : Id}
    (h : s.validate validator proof atHeight kassetId = some s') :
    s'.validate validator' proof' atHeight' kassetId' = none := by
  have hs := validate_status h
  unfold validate
  rcases hs with hs | hs <;> simp [hs]

/-- A validation creates exactly one K-Asset reference. -/
theorem validate_creates_exactly_one_kasset {s s' : ClaimState} {validator : Id}
    {proof : ProofData} {atHeight : Height} {kassetId : Id}
    (h : s.validate validator proof atHeight kassetId = some s')
    (hs : s'.status = ClaimStatus.validated) :
    ∃ k, s'.kassetRef = some k := ⟨kassetId, validate_sets_kasset h hs⟩

theorem withdraw_sets_status {s s' : ClaimState} {caller : Id}
    (h : s.withdraw caller = some s') : s'.status = ClaimStatus.withdrawn := by
  unfold withdraw at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem expire_sets_status {s s' : ClaimState} {hgt : Height}
    (h : s.expire hgt = some s') : s'.status = ClaimStatus.expired := by
  unfold expire at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem reject_sets_status {s s' : ClaimState} {validator : Id} {proof : ProofData}
    {atHeight : Height} (h : s.reject validator proof atHeight = some s') :
    s'.status = ClaimStatus.rejected := by
  unfold reject at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem comment_requires_open {s s' : ClaimState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : s.status = ClaimStatus.open := by
  unfold comment at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem comment_within_window {s s' : ClaimState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : atHeight ≤ s.commentUntilHeight := by
  unfold comment at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

theorem comment_appends {s s' : ClaimState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') :
    s'.comments = commentId :: s.comments := by
  unfold comment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem comment_preserves_status {s s' : ClaimState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : s'.status = s.status := by
  unfold comment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-- The K-Asset reference is never rewritten by a later claim transition. -/
theorem kassetRef_stable {s : ClaimState}
    (h : s.status = ClaimStatus.validated) :
    (∀ (v : Id) (p : ProofData) (hgt k : Id),
      s.validate v p hgt k = none) ∧
    (∀ (v : Id) (p : ProofData) (hgt : Height), s.reject v p hgt = none) ∧
    (∀ caller : Id, s.withdraw caller = none) ∧
    (∀ hgt : Height, s.expire hgt = none) := by
  exact ⟨fun _ _ _ _ => by simp [validate, h],
         fun _ _ _ => by simp [reject, h],
         fun _ => by simp [withdraw, h],
         fun _ => by simp [expire, h]⟩

/-- Terminal claims have no outgoing transition. -/
theorem terminal_no_transition {s : ClaimState} (ht : s.IsTerminal) :
    (∀ (v : Id) (p : ProofData) (hgt k : Id), s.validate v p hgt k = none) ∧
    (∀ (v : Id) (p : ProofData) (hgt : Height), s.reject v p hgt = none) ∧
    (∀ caller : Id, s.withdraw caller = none) ∧
    (∀ hgt : Height, s.expire hgt = none) := by
  rcases ht with h | h | h | h
  · exact kassetRef_stable h
  · exact ⟨fun _ _ _ _ => by simp [validate, h],
           fun _ _ _ => by simp [reject, h],
           fun _ => by simp [withdraw, h],
           fun _ => by simp [expire, h]⟩
  · exact ⟨fun _ _ _ _ => by simp [validate, h],
           fun _ _ _ => by simp [reject, h],
           fun _ => by simp [withdraw, h],
           fun _ => by simp [expire, h]⟩
  · exact ⟨fun _ _ _ _ => by simp [validate, h],
           fun _ _ _ => by simp [reject, h],
           fun _ => by simp [withdraw, h],
           fun _ => by simp [expire, h]⟩

theorem withdraw_requires_claimant {s s' : ClaimState} {caller : Id}
    (h : s.withdraw caller = some s') : caller = s.claimant := by
  unfold withdraw at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

/-! ### Progress -/

theorem open_progress {s : ClaimState} (h : s.status = ClaimStatus.open) :
    (s.withdraw s.claimant).isSome := by
  simp [withdraw, h]

theorem expire_after_deadline {s s' : ClaimState} {hgt : Height}
    (h : s.expire hgt = some s') : s.deadline < hgt := by
  unfold expire at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

end ClaimState

end RGen
