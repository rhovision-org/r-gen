import RGen.Basic

/-!
# One-shot proof cells

A proof capability is a private, single-use token. `ProofState α` holds a payload
`α` and a `used` flag. `take` returns the payload and marks the cell used; a
second take fails. The flag is observability, not the security boundary: the
capability itself is unforgeable, as in Rholang's linear names.

`ProofData` is the credential-proof payload: who proved, for which requirement,
at which height and level, under which credential.
-/

namespace RGen

structure ProofData where
  uri : Id
  subject : Id
  requirement : Requirement
  atHeight : Height
  level : Nat
  credentialUri : Id
  deriving DecidableEq, Repr

structure ProofState (α : Type) where
  data : α
  used : Bool
  deriving Repr

namespace ProofState

variable {α : Type}

/-- Take the payload and mark the cell used. A second take fails. -/
def take (p : ProofState α) : Option (α × ProofState α) :=
  if p.used then none else some (p.data, { p with used := true })

theorem take_once (p : ProofState α) (h : p.used = false) : p.take.isSome := by
  simp [take, h]

theorem take_second (p : ProofState α) (h : p.used = true) : p.take = none := by
  simp [take, h]

theorem take_marks_used {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p'.used = true := by
  unfold take at h
  split at h
  · simp at h
  · simp at h
    rcases h with ⟨rfl, rfl⟩
    rfl

/-- The payload is a snapshot: taking it does not change it. -/
theorem take_data {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p.data = d := by
  unfold take at h
  split at h
  · simp at h
  · simp at h
    rcases h with ⟨rfl, rfl⟩
    rfl

/-- A proof cannot be taken twice. -/
theorem take_take {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p'.take = none :=
  take_second p' (take_marks_used h)

end ProofState

theorem proof_take_once {α : Type} (p : ProofState α) (h : p.used = false) :
    p.take.isSome := ProofState.take_once p h

theorem proof_take_second {α : Type} (p : ProofState α) (h : p.used = true) :
    p.take = none := ProofState.take_second p h

theorem proof_take_marks_used {α : Type} {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p'.used = true := ProofState.take_marks_used h

theorem proof_take_data {α : Type} {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p.data = d := ProofState.take_data h

end RGen
