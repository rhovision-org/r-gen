import RGen.Basic

/-!
# Protocol scaffold

Every primitive model in `RGen.Model.*` is a state type with a guarded `Step`
relation and reachability `Reach`. Guards are pure predicates; a transition is
an `Option`-returning function that fails when the guard is false, so a rejected
step is not a step.

`Reach` is either zero steps (`a = b`) or one or more (`Relation.TransGen`).
`reach_invariant` is the induction used by the per-primitive safety theorems;
`Terminal` marks a state with no outgoing step.
-/

namespace RGen

/-- A step relation on states of one primitive. -/
def Step (σ : Type) := σ → σ → Prop

/-- Zero or more steps. -/
def Reach {σ : Type} (r : Step σ) (a b : σ) : Prop :=
  a = b ∨ Relation.TransGen r a b

theorem reach_refl {σ : Type} (r : Step σ) (a : σ) : Reach r a a := Or.inl rfl

theorem reach_single {σ : Type} {r : Step σ} {a b : σ} (h : r a b) : Reach r a b :=
  Or.inr (Relation.TransGen.single h)

theorem reach_trans {σ : Type} {r : Step σ} {a b c : σ}
    (hab : Reach r a b) (hbc : Reach r b c) : Reach r a c := by
  rcases hab with rfl | hab
  · exact hbc
  · rcases hbc with rfl | hbc
    · exact Or.inr hab
    · exact Or.inr (Relation.TransGen.trans hab hbc)

/-- An invariant is preserved by one step. -/
theorem transGen_invariant {σ : Type} {r : Step σ} {P : σ → Prop}
    (hstep : ∀ a b, r a b → P a → P b) :
    ∀ a b, Relation.TransGen r a b → P a → P b := by
  intro a b ht
  induction ht with
  | single hab => exact hstep _ _ hab
  | tail _ hbc ih => intro hp; exact hstep _ _ hbc (ih hp)

/-- An invariant that holds initially holds in every reachable state. -/
theorem reach_invariant {σ : Type} {r : Step σ} {P : σ → Prop}
    (hstep : ∀ a b, r a b → P a → P b) :
    ∀ a b, Reach r a b → P a → P b := by
  intro a b hreach
  rcases hreach with rfl | ht
  · exact fun hp => hp
  · exact transGen_invariant hstep a b ht

/-- A state is terminal when no step leaves it. -/
def Terminal {σ : Type} (r : Step σ) (a : σ) : Prop := ∀ b, ¬ r a b

theorem terminal_no_step {σ : Type} {r : Step σ} {a b : σ}
    (h : Terminal r a) : ¬ r a b := h b

end RGen
