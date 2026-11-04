import RGen.Basic

/-!
# Shared model types

URIs and parties are `Id`s in this model. A height window is half-open:
`inWindow h start stop` holds when `start ≤ h < stop`.
-/

namespace RGen

abbrev Uri := Id
abbrev Party := Id

def inWindow (h start stop : Height) : Bool := decide (start ≤ h ∧ h < stop)

theorem inWindow_true {h start stop : Height} :
    inWindow h start stop = true ↔ start ≤ h ∧ h < stop := by
  simp [inWindow]

theorem inWindow_end_false {start stop : Height} :
    inWindow stop start stop = false := by
  simp [inWindow]

end RGen
