import RGen.Basic
import RGen.Model.Types

/-!
# Deadline boundaries

Every deployed arm that compares a height to a deadline uses one of two
conventions: `now ≤ deadline` admits, `deadline < now` refuses. This module
pins those conventions and proves that every height falls on exactly one side.
It also makes the Nil comment window total: an omitted window is normalized to
the deadline, so no arm evaluates `Int > Nil`.
-/

namespace RGen

/-- An omitted comment window is the claim deadline. -/
def normalizeCommentWindow (window : Option Height) (deadline : Height) : Height :=
  match window with
  | none => deadline
  | some h => h

theorem nil_comment_window_total (deadline : Height) :
    normalizeCommentWindow none deadline = deadline := rfl

theorem comment_window_total (window : Option Height) (deadline : Height) :
    normalizeCommentWindow window deadline = deadline ∨
      ∃ h, window = some h ∧ normalizeCommentWindow window deadline = h := by
  cases window with
  | none => exact Or.inl rfl
  | some h => exact Or.inr ⟨h, rfl, rfl⟩

/-- Claim, VP, and oracle admission use the inclusive boundary. -/
def admitted (deadline now : Height) : Bool := now ≤ deadline

/-- Expiry uses the strict boundary. -/
def expired (deadline now : Height) : Bool := deadline < now

theorem claim_validate_at_deadline_admitted (deadline : Height) :
    admitted deadline deadline = true := by
  simp [admitted]

theorem claim_expire_after_deadline (deadline now : Height) :
    expired deadline now = true ↔ ¬ admitted deadline now = true := by
  simp [expired, admitted]

theorem oracle_expire_after_deadline (deadline now : Height) :
    expired deadline now = true ↔ admitted deadline now = false := by
  simp [expired, admitted]

theorem oracle_open_requires_future (deadline now : Height)
    (h : ¬ admitted deadline now = true) : expired deadline now = true := by
  have hAdm : admitted deadline now = true ↔ now ≤ deadline := by simp [admitted]
  have hExp : expired deadline now = true ↔ deadline < now := by simp [expired]
  exact hExp.mpr (Nat.lt_of_not_le (fun hle => h (hAdm.mpr hle)))

theorem vp_validate_after_deadline_refused (deadline now : Height)
    (h : expired deadline now = true) : admitted deadline now = false := by
  have hExp : expired deadline now = true ↔ deadline < now := by simp [expired]
  have hAdm : admitted deadline now = false ↔ ¬ now ≤ deadline := by simp [admitted]
  exact hAdm.mpr (Nat.not_le_of_lt (hExp.mp h))

/-- Exactly one side of the boundary admits. -/
theorem deadline_boundary_deterministic (deadline now : Height) :
    admitted deadline now = true ∨ expired deadline now = true := by
  by_cases h : now ≤ deadline
  · exact Or.inl (by simp [admitted, h])
  · have hExp : expired deadline now = true ↔ deadline < now := by simp [expired]
    exact Or.inr (hExp.mpr (Nat.lt_of_not_le h))

theorem deadline_boundary_exclusive (deadline now : Height) :
    ¬ (admitted deadline now = true ∧ expired deadline now = true) := by
  have hAdm : admitted deadline now = true ↔ now ≤ deadline := by simp [admitted]
  have hExp : expired deadline now = true ↔ deadline < now := by simp [expired]
  intro h
  have h1 := hAdm.mp h.1
  have h2 := hExp.mp h.2
  exact Nat.lt_irrefl now (Nat.lt_of_le_of_lt h1 h2)

/-- A claim whose window is omitted has the deadline as its comment boundary. -/
theorem nil_window_comment_at_deadline (deadline now : Height)
    (h : now ≤ deadline) : now ≤ normalizeCommentWindow none deadline := by
  simpa [normalizeCommentWindow] using h

end RGen
