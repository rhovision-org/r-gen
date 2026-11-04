import RGen.Basic
import RGen.Model.Types
import RGen.Model.Proof
import RGen.Model.ValueProposition

/-!
# Oracle case

An oracle case names one adjudicator and the credential that proves the
adjudicator. `decide` requires that credential proof, matching subject and
requirement; no caller-supplied capability is accepted. `execute` is a two-phase
one-shot: `decided → executing → executed`, and only the subject may execute.
Execution is subject-bound because the subject is a stored field and no
transition rewrites it. `close` requires a finished case (executed or expired).
-/

namespace RGen

inductive OracleStatus where
  | open
  | decided
  | executing
  | executed
  | expired
  | closed
  deriving DecidableEq, Repr

structure OracleState where
  caseId : Id
  subject : Id
  claimant : Id
  adjudicator : Id
  adjudicatorCredential : Id
  requirement : Requirement
  deadline : Height
  status : OracleStatus
  decision : Option VPDecision
  evidence : List Id
  deriving DecidableEq, Repr

namespace OracleState

def decide (s : OracleState) (adjudicator : Id) (proof : ProofData) (d : VPDecision) :
    Option OracleState :=
  if s.status = OracleStatus.open ∧ adjudicator = s.adjudicator ∧
      proof.subject = adjudicator ∧ proof.credentialUri = s.adjudicatorCredential ∧
      proof.requirement = s.requirement then
    some { s with status := OracleStatus.decided, decision := some d }
  else none

/-- Execution is bound to the subject; the subject's private apply is the only
way the decision reaches the K-Asset. -/
def execute (s : OracleState) (caller : Id) : Option OracleState :=
  if s.status = OracleStatus.decided ∧ caller = s.subject then
    some { s with status := OracleStatus.executing }
  else none

def finishExecute (s : OracleState) : Option OracleState :=
  if s.status = OracleStatus.executing then
    some { s with status := OracleStatus.executed }
  else none

def expire (s : OracleState) (h : Height) : Option OracleState :=
  if s.status = OracleStatus.open ∧ s.deadline < h then
    some { s with status := OracleStatus.expired }
  else none

/-- Roll back a failed execution; the next execute is a new generation. -/
def rollbackExecute (s : OracleState) : Option OracleState :=
  if s.status = OracleStatus.executing then
    some { s with status := OracleStatus.decided }
  else none

def close (s : OracleState) : Option OracleState :=
  if s.status = OracleStatus.executed ∨ s.status = OracleStatus.expired then
    some { s with status := OracleStatus.closed }
  else none

def addEvidence (s : OracleState) (ref : Id) : Option OracleState :=
  if s.status = OracleStatus.open ∧ ref ∉ s.evidence then
    some { s with evidence := ref :: s.evidence }
  else none

theorem addEvidence_requires_open {s s' : OracleState} {ref : Id}
    (h : s.addEvidence ref = some s') : s.status = OracleStatus.open := by
  unfold addEvidence at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem addEvidence_no_duplicate {s s' : OracleState} {ref : Id}
    (h : s.addEvidence ref = some s') : ref ∉ s.evidence := by
  unfold addEvidence at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

theorem addEvidence_appends {s s' : OracleState} {ref : Id}
    (h : s.addEvidence ref = some s') : s'.evidence = ref :: s.evidence := by
  unfold addEvidence at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem rollbackExecute_requires_executing {s s' : OracleState}
    (h : s.rollbackExecute = some s') : s.status = OracleStatus.executing := by
  unfold rollbackExecute at h
  split at h
  · rename_i hg
    exact hg
  · simp at h

theorem rollbackExecute_sets_decided {s s' : OracleState}
    (h : s.rollbackExecute = some s') : s'.status = OracleStatus.decided := by
  unfold rollbackExecute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem rollbackExecute_preserves_subject {s s' : OracleState}
    (h : s.rollbackExecute = some s') : s'.subject = s.subject := by
  unfold rollbackExecute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-! ### Decision -/

theorem decide_requires_open {s s' : OracleState} {adjudicator : Id} {proof : ProofData}
    {d : VPDecision} (h : s.decide adjudicator proof d = some s') :
    s.status = OracleStatus.open := by
  unfold decide at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem decide_requires_adjudicator {s s' : OracleState} {adjudicator : Id}
    {proof : ProofData} {d : VPDecision}
    (h : s.decide adjudicator proof d = some s') : adjudicator = s.adjudicator := by
  unfold decide at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem decide_requires_proof {s s' : OracleState} {adjudicator : Id}
    {proof : ProofData} {d : VPDecision}
    (h : s.decide adjudicator proof d = some s') :
    proof.subject = adjudicator ∧ proof.credentialUri = s.adjudicatorCredential ∧
      proof.requirement = s.requirement := by
  unfold decide at h
  split at h
  · rename_i hg
    exact ⟨hg.2.2.1, hg.2.2.2.1, hg.2.2.2.2⟩
  · simp at h

theorem decide_sets_status {s s' : OracleState} {adjudicator : Id} {proof : ProofData}
    {d : VPDecision} (h : s.decide adjudicator proof d = some s') :
    s'.status = OracleStatus.decided := by
  unfold decide at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem execute_sets_status {s s' : OracleState} {caller : Id}
    (h : s.execute caller = some s') : s'.status = OracleStatus.executing := by
  unfold execute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem finishExecute_sets_status {s s' : OracleState}
    (h : s.finishExecute = some s') : s'.status = OracleStatus.executed := by
  unfold finishExecute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem expire_sets_status {s s' : OracleState} {hgt : Height}
    (h : s.expire hgt = some s') : s'.status = OracleStatus.expired := by
  unfold expire at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem close_sets_status {s s' : OracleState}
    (h : s.close = some s') : s'.status = OracleStatus.closed := by
  unfold close at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem decide_once {s s' : OracleState} {adjudicator : Id} {proof : ProofData}
    {d : VPDecision} {adjudicator' : Id} {proof' : ProofData} {d' : VPDecision}
    (h : s.decide adjudicator proof d = some s') :
    s'.decide adjudicator' proof' d' = none := by
  unfold decide at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [decide]
  · simp at h

/-! ### Execution -/

theorem execute_requires_decided {s s' : OracleState} {caller : Id}
    (h : s.execute caller = some s') : s.status = OracleStatus.decided := by
  unfold execute at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem execute_subject_bound {s s' : OracleState} {caller : Id}
    (h : s.execute caller = some s') : caller = s.subject := by
  unfold execute at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

theorem execute_preserves_subject {s s' : OracleState} {caller : Id}
    (h : s.execute caller = some s') : s'.subject = s.subject := by
  unfold execute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-- Execution is one-shot: once executing or executed, `execute` fails. -/
theorem execute_once {s s' : OracleState} {caller caller' : Id}
    (h : s.execute caller = some s') : s'.execute caller' = none := by
  unfold execute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [execute]
  · simp at h

theorem finish_execute_once {s s' : OracleState} {caller : Id}
    (h : s.finishExecute = some s') : s'.execute caller = none := by
  unfold finishExecute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [execute]
  · simp at h

theorem finishExecute_requires_executing {s s' : OracleState}
    (h : s.finishExecute = some s') : s.status = OracleStatus.executing := by
  unfold finishExecute at h
  split at h
  · rename_i hg
    exact hg
  · simp at h

/-! ### Closure -/

theorem close_requires_finished {s s' : OracleState} (h : s.close = some s') :
    s.status = OracleStatus.executed ∨ s.status = OracleStatus.expired := by
  unfold close at h
  split at h
  · rename_i hg
    exact hg
  · simp at h

/-- An open case cannot be closed. -/
theorem close_open_refused {s : OracleState} (h : s.status = OracleStatus.open) :
    s.close = none := by
  unfold close
  rw [if_neg]
  intro hg
  rcases hg with hg | hg <;> rw [h] at hg <;> simp at hg

theorem close_once {s s' : OracleState} (h : s.close = some s') : s'.close = none := by
  unfold close at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [close]
  · simp at h

theorem expire_requires_open {s s' : OracleState} {hgt : Height}
    (h : s.expire hgt = some s') : s.status = OracleStatus.open := by
  unfold expire at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem expire_after_deadline {s s' : OracleState} {hgt : Height}
    (h : s.expire hgt = some s') : s.deadline < hgt := by
  unfold expire at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

/-! ### Progress -/

theorem open_progress {s : OracleState}
    (adjudicator : Id) (proof : ProofData) (d : VPDecision)
    (hok : s.status = OracleStatus.open ∧ adjudicator = s.adjudicator ∧
      proof.subject = adjudicator ∧ proof.credentialUri = s.adjudicatorCredential ∧
      proof.requirement = s.requirement) :
    (s.decide adjudicator proof d).isSome := by
  simp [decide, hok]

theorem decided_progress {s : OracleState} (h : s.status = OracleStatus.decided) :
    (s.execute s.subject).isSome := by
  simp [execute, h]

theorem executing_progress {s : OracleState} (h : s.status = OracleStatus.executing) :
    s.finishExecute.isSome := by
  simp [finishExecute, h]

end OracleState

end RGen
