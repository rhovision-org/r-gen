import RGen.Linear.Exec

/-!
# Decision authority

`FactorsThroughCell dec c` means `dec` has a linearization point at cell `c`: it is a
function of the value at `c` alone. `DependsOnlyOn dec C` is the general form.

`cross_cell_read_not_authority` is the formal rule that a peek of a mutable cell is not
authority: if a decision varies with `d` while every other cell is held equal, then it does
not factor through `c` and every authority set for it must contain `d`. A peek of `d` can be
a linearization point *at `d`*; the theorem says `d` must then be part of the authority,
not an ambient read.
-/

namespace RGen

variable {α β : Type}

/-- Two worlds agree on every cell in `C`. -/
def AgreeOn (w1 w2 : VWorld α) (C : List CellId) : Prop :=
  ∀ c, c ∈ C → w1.cell c = w2.cell c

/-- Two worlds agree everywhere except possibly at `d`. -/
def AgreeOff (d : CellId) (w1 w2 : VWorld α) : Prop :=
  ∀ c, c ≠ d → w1.cell c = w2.cell c

/-- The decision depends only on the cells in `C`. -/
def DependsOnlyOn (dec : VWorld α → β) (C : List CellId) : Prop :=
  ∀ w1 w2, AgreeOn w1 w2 C → dec w1 = dec w2

/-- The decision factors through the value of cell `c` (a linearization point at `c`). -/
def FactorsThroughCell (dec : VWorld α → β) (c : CellId) : Prop :=
  ∃ F : Option (VCell α) → β, ∀ w, dec w = F (w.cell c)

def single (c : CellId) (v : Option (VCell α)) : VWorld α :=
  ⟨fun x => if x = c then v else none⟩

@[simp] theorem single_same (c : CellId) (v : Option (VCell α)) :
    (single c v).cell c = v := by
  simp [single]

theorem agree_single (w : VWorld α) (c : CellId) :
    AgreeOn w (single c (w.cell c)) [c] := by
  intro d hd
  simp only [List.mem_singleton] at hd
  subst hd
  simp

theorem factors_iff_depends_only (dec : VWorld α → β) (c : CellId) :
    FactorsThroughCell dec c ↔ DependsOnlyOn dec [c] := by
  constructor
  · rintro ⟨F, hF⟩ w1 w2 hagree
    rw [hF w1, hF w2]
    have hc : w1.cell c = w2.cell c := hagree c (by simp)
    rw [hc]
  · intro h
    refine ⟨fun v => dec (single c v), fun w => ?_⟩
    exact h w (single c (w.cell c)) (agree_single w c)

theorem depends_only_on_subset {dec : VWorld α → β} {C C' : List CellId}
    (h : DependsOnlyOn dec C') (hsub : ∀ c, c ∈ C' → c ∈ C) : DependsOnlyOn dec C := by
  intro w1 w2 hagree
  exact h w1 w2 (fun c hc => hagree c (hsub c hc))

/-- If a decision varies with `d` while every other cell is equal, then `d` is authority:
it does not factor through `c`, and every set it depends only on must contain `d`. -/
theorem cross_cell_read_not_authority {dec : VWorld α → β} {c d : CellId} (hcd : c ≠ d)
    (hvar : ∃ w1 w2, AgreeOff d w1 w2 ∧ w1.cell d ≠ w2.cell d ∧ dec w1 ≠ dec w2) :
    ¬ FactorsThroughCell dec c ∧
      ∀ L : List CellId, DependsOnlyOn dec L → d ∈ L := by
  rcases hvar with ⟨w1, w2, hoff, _hdiff, hdec⟩
  constructor
  · intro hfac
    have hdep : DependsOnlyOn dec [c] := (factors_iff_depends_only dec c).mp hfac
    have hc : w1.cell c = w2.cell c := hoff c hcd
    exact hdec (hdep w1 w2 (fun e he => by
      simp only [List.mem_singleton] at he
      rw [he]
      exact hc))
  · intro L hdep
    by_cases hd : d ∈ L
    · exact hd
    · exfalso
      have hL : AgreeOn w1 w2 L := by
        intro e he
        exact hoff e (fun hed => hd (hed ▸ he))
      exact hdec (hdep w1 w2 hL)

/-- A decision that reads a cell and a second peeked cell has the second cell in its
authority whenever it varies with it. -/
theorem peek_not_authority {γ : Type} (f : Option (VCell α) → Option (VCell α) → γ)
    {c d : CellId} (hcd : c ≠ d)
    (hvar : ∃ a b1 b2, f a b1 ≠ f a b2) :
    ¬ DependsOnlyOn (fun w => f (w.cell c) (w.cell d)) [c] := by
  rcases hvar with ⟨a, b1, b2, hne⟩
  intro hdep
  let w1 : VWorld α := ⟨fun x => if x = c then a else if x = d then b1 else none⟩
  let w2 : VWorld α := ⟨fun x => if x = c then a else if x = d then b2 else none⟩
  have hagree : AgreeOn w1 w2 [c] := by
    intro e he
    simp only [List.mem_singleton] at he
    subst he
    simp [w1, w2]
  have := hdep w1 w2 hagree
  apply hne
  have hdc : d ≠ c := fun h => hcd h.symm
  simpa [w1, w2, hdc] using this

end RGen
