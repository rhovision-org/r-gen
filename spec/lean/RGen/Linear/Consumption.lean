import RGen.Linear.Lift

/-!
# Proof-cell consumption traces

`Arm.proofCells` is metadata unless a trace semantics reads it. This module gives the
minimal trace discipline:

* a `proof` action consumes one proof cell;
* a `commit` action for an arm may occur only after every cell in the arm's
  `proofCells` list has been consumed;
* a proof cell cannot be consumed twice in one trace.

This is a model of the consumption obligation, not a refinement of the deployed
Rholang capability. It makes the metadata live and gives the ordering theorem a
precise statement.
-/

namespace RGen

structure ProofUse where
  cell : CellId
  gen : Nat
  deriving Repr

structure ArmUse (σ π : Type) where
  arm : Arm σ π
  param : π
  gen : Nat

inductive Action (σ π : Type) where
  | proof (u : ProofUse)
  | commit (u : ArmUse σ π)

namespace Action

variable {σ π : Type}

/-- A trace is well formed relative to the proof cells already consumed. A proof action
adds its cell and cannot repeat a cell; a commit may occur only if all its declared proof
cells are already present. -/
def WellFormedFrom : List CellId → List (Action σ π) → Prop
  | _, [] => True
  | seen, .proof u :: rest =>
      u.cell ∉ seen ∧ WellFormedFrom (u.cell :: seen) rest
  | seen, .commit u :: rest =>
      (∀ c ∈ u.arm.proofCells, c ∈ seen) ∧ WellFormedFrom seen rest

def WellFormed (es : List (Action σ π)) : Prop := WellFormedFrom [] es

/-- A commit at the head of a well-formed trace has consumed every declared proof cell. -/
theorem commit_requires_declared_proofs {seen : List CellId} {u : ArmUse σ π}
    {rest : List (Action σ π)} (h : WellFormedFrom seen (.commit u :: rest)) :
    ∀ c ∈ u.arm.proofCells, c ∈ seen :=
  h.1

/-- A proof action cannot repeat a cell already consumed in the trace. -/
theorem proof_cell_not_reused {seen : List CellId} {u : ProofUse}
    {rest : List (Action σ π)} (h : WellFormedFrom seen (.proof u :: rest)) :
    u.cell ∉ seen :=
  h.1

/-- The head-commit obligation for a trace starting empty. -/
theorem commit_requires_declared_proofs_empty {u : ArmUse σ π}
    {rest : List (Action σ π)} (h : WellFormed (.commit u :: rest)) :
    ∀ c ∈ u.arm.proofCells, c ∈ ([] : List CellId) :=
  commit_requires_declared_proofs h

end Action

/-- The stable headline: a well-formed trace consumes every declared proof cell before the
arm commit. `Action.proof_cell_not_reused` is the one-shot side. -/
theorem core_proof_cells_consumed_before_commit {σ π : Type} {seen : List CellId}
    {u : ArmUse σ π} {rest : List (Action σ π)}
    (h : Action.WellFormedFrom seen (.commit u :: rest)) :
    ∀ c ∈ u.arm.proofCells, c ∈ seen :=
  Action.commit_requires_declared_proofs h

end RGen

namespace RGen

/-- A proof token is a cell generation. Two arms that consume the same token are a reuse. -/
structure ProofToken where
  cell : CellId
  gen : Nat
  deriving DecidableEq, Repr

inductive TokenAction where
  | issue (t : ProofToken)
  | consume (t : ProofToken)
  | commit (t : ProofToken)

/-- Issuance is unique; consumption requires an issued token and is unique; a commit
requires the token to have been consumed. -/
def TokenWellFormedFrom (issued consumed : List ProofToken) : List TokenAction → Prop
  | [] => True
  | .issue t :: rest => t ∉ issued ∧ TokenWellFormedFrom (t :: issued) consumed rest
  | .consume t :: rest =>
      t ∈ issued ∧ t ∉ consumed ∧ TokenWellFormedFrom issued (t :: consumed) rest
  | .commit t :: rest => t ∈ consumed ∧ TokenWellFormedFrom issued consumed rest

/-- No token is consumed twice in the suffix. -/
def NoDoubleConsumeFrom (consumed : List ProofToken) : List TokenAction → Prop
  | [] => True
  | .consume t :: rest => t ∉ consumed ∧ NoDoubleConsumeFrom (t :: consumed) rest
  | _ :: rest => NoDoubleConsumeFrom consumed rest

theorem wf_no_double_consume {issued consumed : List ProofToken}
    {trace : List TokenAction} (h : TokenWellFormedFrom issued consumed trace) :
    NoDoubleConsumeFrom consumed trace := by
  induction trace generalizing issued consumed with
  | nil => simp [NoDoubleConsumeFrom]
  | cons a rest ih =>
      cases a with
      | issue t =>
          unfold TokenWellFormedFrom at h
          exact ih h.2
      | consume t =>
          unfold TokenWellFormedFrom at h
          exact ⟨h.2.1, ih h.2.2⟩
      | commit t =>
          unfold TokenWellFormedFrom at h
          exact ih h.2

/-- No proof token is consumed by two arms in one well-formed trace. -/
theorem core_no_proof_reuse_across_arms {trace : List TokenAction}
    (h : TokenWellFormedFrom [] [] trace) : NoDoubleConsumeFrom [] trace :=
  wf_no_double_consume h

theorem commit_requires_consumed {issued consumed : List ProofToken}
    {t : ProofToken} {rest : List TokenAction}
    (h : TokenWellFormedFrom issued consumed (.commit t :: rest)) : t ∈ consumed :=
  h.1

theorem core_proof_token_unique_in_trace {trace : List TokenAction}
    (h : TokenWellFormedFrom [] [] trace) : NoDoubleConsumeFrom [] trace :=
  core_no_proof_reuse_across_arms h

end RGen
