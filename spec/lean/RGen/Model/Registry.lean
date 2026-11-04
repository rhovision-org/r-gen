import RGen.Basic

/-!
# Append-only registries

A registry maps a creation event to an `Id`. `register` refuses a duplicate and
otherwise prepends; `mem` is the only read. The registry is the serialization
point for creation, and `verify` is monotone: a registration never un-verifies an
existing entry.

The credential, claim, and value-proposition registries are instances of this
structure.
-/

namespace RGen

structure Registry where
  entries : List Id
  deriving DecidableEq, Repr

namespace Registry

def mem (r : Registry) (id : Id) : Bool := decide (id ∈ r.entries)

theorem mem_true {r : Registry} {id : Id} : r.mem id = true ↔ id ∈ r.entries := by
  simp [mem]

def register (r : Registry) (id : Id) : Option Registry :=
  if id ∈ r.entries then none else some ⟨id :: r.entries⟩

theorem register_none {r : Registry} {id : Id} (h : id ∈ r.entries) :
    r.register id = none := by
  simp [register, h]

theorem register_some_mem {r : Registry} {id : Id} {r' : Registry}
    (h : r.register id = some r') : id ∈ r'.entries := by
  unfold register at h
  split at h
  · simp at h
  · simp at h
    rcases h with rfl
    simp

/-- A successful registration verifies exactly the old entries and the new id. -/
theorem register_verify {r : Registry} {id : Id} {r' : Registry}
    (h : r.register id = some r') (x : Id) :
    r'.mem x = true ↔ x = id ∨ r.mem x = true := by
  unfold register at h
  split at h
  · simp at h
  · simp at h
    rcases h with rfl
    simp only [mem, decide_eq_true_eq, List.mem_cons, mem_true]

/-- Registration is monotone: it never un-verifies an existing entry. -/
theorem verify_monotone {r : Registry} {id : Id} {r' : Registry}
    (h : r.register id = some r') {x : Id} (hx : r.mem x = true) :
    r'.mem x = true := by
  rw [register_verify h]
  exact Or.inr hx

/-- A registry never registers the same id twice. -/
theorem register_twice {r : Registry} {id : Id} {r' : Registry}
    (h : r.register id = some r') : r'.register id = none := by
  apply register_none
  rw [← mem_true, register_verify h]
  exact Or.inl rfl

/-- Registration is unique: a second registration of a verified id fails. -/
theorem register_unique {r : Registry} {id : Id} (h : r.mem id = true) :
    r.register id = none :=
  register_none (mem_true.mp h)

end Registry

end RGen
