import RGen.Basic

/-!
# Identity

An identity is an address with one owner. The directory is first-writer-wins:
`create` succeeds only when the address is unclaimed, and a second create at the
same address is refused. An owner may transfer the identity; the address is
never rewritten.
-/

namespace RGen

structure Directory where
  entries : List (Id × Id)
  deriving DecidableEq, Repr

namespace Directory

/-- First match wins. -/
def lookup : List (Id × Id) → Id → Option Id
  | [], _ => none
  | (a', o) :: rest, a => if a' = a then some o else lookup rest a

def create (d : Directory) (a o : Id) : Option Directory :=
  if (lookup d.entries a).isNone then some ⟨(a, o) :: d.entries⟩ else none

theorem lookup_create_same (d : Directory) (a o : Id) (d' : Directory)
    (h : d.create a o = some d') : lookup d'.entries a = some o := by
  unfold create at h
  split at h
  · simp at h
    rcases h with rfl
    simp [lookup]
  · simp at h

theorem lookup_create_other (d : Directory) (a o a' : Id) (hne : a' ≠ a)
    (d' : Directory) (h : d.create a o = some d') :
    lookup d'.entries a' = lookup d.entries a' := by
  have han : ¬ a = a' := fun h => hne h.symm
  unfold create at h
  split at h
  · simp at h
    rcases h with rfl
    simp [lookup, han]
  · simp at h

/-- First writer wins: an already claimed address cannot be created again. -/
theorem create_refused (d : Directory) (a o o' : Id) (h : lookup d.entries a = some o) :
    d.create a o' = none := by
  unfold create
  rw [h]
  simp

/-- A successful create blocks every later create at the same address. -/
theorem create_unique (d : Directory) (a o o' : Id) (d' : Directory)
    (h : d.create a o = some d') : d'.create a o' = none :=
  create_refused d' a o o' (lookup_create_same d a o d' h)

end Directory

structure IdentityState where
  address : Id
  owner : Id
  deriving DecidableEq, Repr

/-- Only the current owner may transfer the identity. -/
def updateOwner (s : IdentityState) (caller newOwner : Id) : Option IdentityState :=
  if caller = s.owner then some { s with owner := newOwner } else none

theorem update_owner_requires_owner {s : IdentityState} {caller newOwner : Id}
    {s' : IdentityState} (h : updateOwner s caller newOwner = some s') :
    caller = s.owner := by
  unfold updateOwner at h
  split at h
  · exact ‹caller = s.owner›
  · simp at h

theorem update_owner_preserves_address {s : IdentityState} {caller newOwner : Id}
    {s' : IdentityState} (h : updateOwner s caller newOwner = some s') :
    s'.address = s.address := by
  unfold updateOwner at h
  split at h
  · simp at h
    rcases h with rfl
    rfl
  · simp at h

theorem update_owner_sets_owner {s : IdentityState} {caller newOwner : Id}
    {s' : IdentityState} (h : updateOwner s caller newOwner = some s') :
    s'.owner = newOwner := by
  unfold updateOwner at h
  split at h
  · simp at h
    rcases h with rfl
    rfl
  · simp at h

theorem update_owner_refused {s : IdentityState} {caller newOwner : Id}
    (h : caller ≠ s.owner) : updateOwner s caller newOwner = none := by
  simp [updateOwner, h]

end RGen
