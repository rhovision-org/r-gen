import RGen.Linear.Lift

/-!
# Arm-pair vocabulary

`NeverAfter first second` means a successful `first` leaves a state on which `second`
refuses. `TwoWayExclusive` is both directions. `OrderedAfter` is the one-way case: the
second order is refused; the first order is the serialized/non-retroactive order.
-/

namespace RGen

def NeverAfter {σ : Type} (first second : σ → Option σ) : Prop :=
  ∀ s s1, first s = some s1 → second s1 = none

def TwoWayExclusive {σ : Type} (first second : σ → Option σ) : Prop :=
  NeverAfter first second ∧ NeverAfter second first

def OrderedAfter {σ : Type} (first second : σ → Option σ) : Prop :=
  NeverAfter second first

theorem never_after_no_two {σ : Type} {first second : σ → Option σ}
    (h : NeverAfter first second) {s s1 s2 : σ}
    (h1 : first s = some s1) (h2 : second s1 = some s2) : False := by
  have := h s s1 h1
  rw [this] at h2
  simp at h2

end RGen
