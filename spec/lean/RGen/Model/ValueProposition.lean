import RGen.Basic
import RGen.Linear.Protocol
import RGen.Model.Types
import RGen.Model.Proof

/-!
# Value proposition

A value proposition is proposed, validated once by a non-proposer holding a
credential proof, and then either withdrawn, disputed, or proved-validated as a
one-shot capability. A dispute resolves to upheld or revoked. `Withdrawn`,
`Upheld`, and `Revoked` are terminal.

`proveValidated` consumes the proposition cell in the linear model; here it is a
pure function that yields a one-shot proof and leaves the state unchanged. A
dispute after a proof is non-retroactive for the same reason as credentials: the
proof is a snapshot.
-/

namespace RGen

inductive VPStatus where
  | proposed
  | validated
  | withdrawn
  | disputed
  | upheld
  | revoked
  | partiallyRevoked
  deriving DecidableEq, Repr

inductive VPDecision where
  | uphold
  | revoke
  | partially
  deriving DecidableEq, Repr

structure VPState where
  uri : Id
  proposer : Id
  requirement : Requirement
  status : VPStatus
  validatedBy : Option Id
  disputeCase : Option Id
  deadlineHeight : Height
  comments : List Id
  /-- Declared quantity mean and variance rate (basis points). -/
  quantityMean : Nat
  quantityBps : Nat
  /-- Declared quality mean (4..20) and variance rate (basis points). -/
  qualityMean : Nat
  qualityBps : Nat
  varianceN : Nat
  deriving DecidableEq, Repr

/-- The declared variance rates are non-negative, bounded, and sum to at most 100%. -/
def VarianceSound (s : VPState) : Prop :=
  s.quantityMean > 0 ∧
  s.qualityMean ≥ 4 ∧ s.qualityMean ≤ 20 ∧
  s.quantityBps ≤ 10000 ∧ s.qualityBps ≤ 10000 ∧
  s.quantityBps + s.qualityBps ≤ 10000 ∧ s.varianceN ≥ 1

namespace VPState

def IsTerminal (s : VPState) : Prop :=
  s.status = VPStatus.withdrawn ∨ s.status = VPStatus.upheld ∨ s.status = VPStatus.revoked

def validate (s : VPState) (validator : Id) (proof : ProofData) : Option VPState :=
  if s.status = VPStatus.proposed ∧ validator ≠ s.proposer ∧
      proof.subject = validator ∧ proof.requirement = s.requirement then
    some { s with status := VPStatus.validated, validatedBy := some validator }
  else none

def withdraw (s : VPState) (caller : Id) : Option VPState :=
  if caller = s.proposer ∧ s.status = VPStatus.proposed then
    some { s with status := VPStatus.withdrawn }
  else none

def openDispute (s : VPState) (caller : Id) (caseId : Id) : Option VPState :=
  if (s.status = VPStatus.proposed ∨ s.status = VPStatus.validated) ∧
      (caller = s.proposer ∨ s.validatedBy = some caller) ∧ s.disputeCase = none then
    some { s with status := VPStatus.disputed, disputeCase := some caseId }
  else none

/-- Append a comment while the proposition is proposed and inside its comment window. -/
def comment (s : VPState) (commentId : Id) (atHeight : Height) : Option VPState :=
  if s.status = VPStatus.proposed ∧ atHeight ≤ s.deadlineHeight then
    some { s with comments := commentId :: s.comments }
  else none

def applyDecision (s : VPState) (caseId : Id) (d : VPDecision) : Option VPState :=
  if s.status = VPStatus.disputed ∧ s.disputeCase = some caseId then
    some { s with status :=
      match d with
      | VPDecision.uphold => VPStatus.upheld
      | VPDecision.revoke => VPStatus.revoked
      | VPDecision.partially => VPStatus.partiallyRevoked }
  else none

/-- A proof that the proposition is validated. -/
def proveValidated (s : VPState) (proofUri : Id) (atHeight : Height) (caller : Id) :
    Option (ProofState (Id × Height × Id)) :=
  if s.status = VPStatus.validated then some ⟨(proofUri, atHeight, caller), false⟩ else none

/-! ### Guards and once-only transitions -/

theorem validate_requires_proposed {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : s.status = VPStatus.proposed := by
  unfold validate at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem validate_requires_non_proposer {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : validator ≠ s.proposer := by
  unfold validate at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem validate_requires_subject {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : proof.subject = validator := by
  unfold validate at h
  split at h
  · rename_i hg
    exact hg.2.2.1
  · simp at h

theorem validate_sets_status {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : s'.status = VPStatus.validated := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem withdraw_sets_status {s s' : VPState} {caller : Id}
    (h : s.withdraw caller = some s') : s'.status = VPStatus.withdrawn := by
  unfold withdraw at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem openDispute_sets_status {s s' : VPState} {caller caseId : Id}
    (h : s.openDispute caller caseId = some s') : s'.status = VPStatus.disputed := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem validate_once {s s' : VPState} {validator : Id} {proof : ProofData}
    (h : s.validate validator proof = some s') : s'.validate validator proof = none := by
  unfold validate at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [validate]
  · simp at h

theorem proveValidated_requires_validated {s : VPState} {uri : Id} {atHeight : Height}
    {caller : Id} {p : ProofState (Id × Height × Id)}
    (hp : s.proveValidated uri atHeight caller = some p) : s.status = VPStatus.validated := by
  unfold proveValidated at hp
  split at hp
  · rename_i hg
    exact hg
  · simp at hp

theorem openDispute_requires_status {s s' : VPState} {caller caseId : Id}
    (h : s.openDispute caller caseId = some s') :
    s.status = VPStatus.proposed ∨ s.status = VPStatus.validated := by
  unfold openDispute at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem comment_requires_proposed {s s' : VPState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : s.status = VPStatus.proposed := by
  unfold comment at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem comment_within_window {s s' : VPState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : atHeight ≤ s.deadlineHeight := by
  unfold comment at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

theorem comment_appends {s s' : VPState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') :
    s'.comments = commentId :: s.comments := by
  unfold comment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem comment_preserves_status {s s' : VPState} {commentId : Id} {atHeight : Height}
    (h : s.comment commentId atHeight = some s') : s'.status = s.status := by
  unfold comment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-- A disputed proposition cannot be proved as validated. -/
theorem prove_after_dispute {s s' : VPState} {caller caseId uri : Id} {atHeight : Height}
    {proofCaller : Id} (h : s.openDispute caller caseId = some s') :
    s'.proveValidated uri atHeight proofCaller = none := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [proveValidated]
  · simp at h

/-- A second dispute cannot open: the first moved the status out of `validated`. -/
theorem dispute_once {s s' : VPState} {caller caseId caller' caseId' : Id}
    (h : s.openDispute caller caseId = some s') :
    s'.openDispute caller' caseId' = none := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [openDispute]
  · simp at h

theorem withdraw_requires_proposer {s s' : VPState} {caller : Id}
    (h : s.withdraw caller = some s') : caller = s.proposer := by
  unfold withdraw at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem decision_once {s s' : VPState} {caseId : Id} {d : VPDecision} {caseId' : Id}
    {d' : VPDecision} (h : s.applyDecision caseId d = some s') :
    s'.applyDecision caseId' d' = none := by
  unfold applyDecision at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    cases d <;> simp [applyDecision]
  · simp at h

/-- Terminal states have no outgoing transition. -/
theorem terminal_no_transition {s : VPState} (ht : s.IsTerminal) :
    (∀ (validator : Id) (proof : ProofData), s.validate validator proof = none) ∧
    (∀ caller : Id, s.withdraw caller = none) ∧
    (∀ (caller caseId : Id), s.openDispute caller caseId = none) ∧
    (∀ (caseId : Id) (d : VPDecision), s.applyDecision caseId d = none) := by
  rcases ht with h | h | h
  · exact ⟨fun _ _ => by simp [validate, h],
           fun _ => by simp [withdraw, h],
           fun _ _ => by simp [openDispute, h],
           fun _ _ => by simp [applyDecision, h]⟩
  · exact ⟨fun _ _ => by simp [validate, h],
           fun _ => by simp [withdraw, h],
           fun _ _ => by simp [openDispute, h],
           fun _ _ => by simp [applyDecision, h]⟩
  · exact ⟨fun _ _ => by simp [validate, h],
           fun _ => by simp [withdraw, h],
           fun _ _ => by simp [openDispute, h],
           fun _ _ => by simp [applyDecision, h]⟩

/-! ### Progress -/

theorem proposed_progress {s : VPState} (h : s.status = VPStatus.proposed) :
    (s.withdraw s.proposer).isSome := by
  simp [withdraw, h]

theorem validated_progress {s : VPState} (h : s.status = VPStatus.validated)
    (uri : Id) (atHeight : Height) (caller : Id) :
    (s.proveValidated uri atHeight caller).isSome := by
  simp [proveValidated, h]

theorem disputed_progress {s : VPState} (h : s.status = VPStatus.disputed)
    {caseId : Id} (hc : s.disputeCase = some caseId) (d : VPDecision) :
    (s.applyDecision caseId d).isSome := by
  simp [applyDecision, h, hc]

end VPState

end RGen
