import RGen.Linear.Authority

/-!
# Lifting pure arm guards into the versioned model

An `Arm` is a cell, a pure step `σ → π → Option σ`, and the proof cells its decision
consumes. `Arm.decision` reads only the arm's cell and applies the step; the existing model
guard functions are used directly, not re-encoded.
-/

namespace RGen

structure Arm (σ π : Type) where
  cell : CellId
  step : σ → π → Option σ
  proofCells : List CellId
  kind : Nat

namespace Arm

variable {σ π : Type}

def decision (a : Arm σ π) (w : VWorld σ) (p : π) : Option σ :=
  match w.cell a.cell with
  | none => none
  | some vc => a.step vc.val p

def event (a : Arm σ π) (p : π) (expected : Nat) : Event σ :=
  ⟨a.cell, expected, fun s => a.step s p⟩

theorem decision_factors (a : Arm σ π) (p : π) :
    FactorsThroughCell (fun w => a.decision w p) a.cell := by
  refine ⟨fun vc => vc.bind (fun vc => a.step vc.val p), fun w => ?_⟩
  cases h : w.cell a.cell <;> simp [decision, h]

theorem decision_authority (a : Arm σ π) (p : π) :
    DependsOnlyOn (fun w => a.decision w p) [a.cell] :=
  (factors_iff_depends_only _ _).mp (decision_factors a p)

end Arm

end RGen
