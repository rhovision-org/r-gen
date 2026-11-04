import RGen.Basic

/-!
# Versioned linear cells

A `VCell` carries a value and a serialization **generation**. Every accepted
consume/re-post increments the generation, including identity-preserving arms such as
`credential.prove`; this is deliberately not the deployed JSON `version` field, which
increments only on logical mutation.

`VWorld.commit` is the atomic consume/guard/update/re-post step. `take` and `post` expose
the same step as the deployed `for (@s <- cell) { ...; cell!(s') }` pattern. The theorem
`take_post_commit_equiv` says the two presentations are equal; `take_take_blocks` says a
second take cannot succeed without a post.
-/

namespace RGen

structure VCell (α : Type) where
  val : α
  gen : Nat
  deriving Repr

structure VWorld (α : Type) where
  cell : CellId → Option (VCell α)

namespace VWorld

variable {α : Type}

def set (w : VWorld α) (c : CellId) (v : α) (n : Nat) : VWorld α :=
  ⟨fun x => if x = c then some ⟨v, n⟩ else w.cell x⟩

@[simp] theorem set_same (w : VWorld α) (c : CellId) (v : α) (n : Nat) :
    (w.set c v n).cell c = some ⟨v, n⟩ := by
  simp [set]

theorem set_other (w : VWorld α) (c d : CellId) (v : α) (n : Nat) (h : d ≠ c) :
    (w.set c v n).cell d = w.cell d := by
  simp [set, h]

def remove (w : VWorld α) (c : CellId) : VWorld α :=
  ⟨fun x => if x = c then none else w.cell x⟩

@[simp] theorem remove_same (w : VWorld α) (c : CellId) : (w.remove c).cell c = none := by
  simp [remove]

theorem remove_other (w : VWorld α) (c d : CellId) (h : d ≠ c) :
    (w.remove c).cell d = w.cell d := by
  simp [remove, h]

@[simp] theorem set_set_same (w : VWorld α) (c : CellId) (v1 : α) (n1 : Nat)
    (v2 : α) (n2 : Nat) : (w.set c v1 n1).set c v2 n2 = w.set c v2 n2 := by
  cases w with
  | mk cell =>
      simp only [set, VWorld.mk.injEq]
      funext x
      by_cases hx : x = c <;> simp [hx]

theorem remove_set_same (w : VWorld α) (c : CellId) (v : α) (n : Nat) :
    (w.remove c).set c v n = w.set c v n := by
  cases w with
  | mk cell =>
      simp only [remove, set, VWorld.mk.injEq]
      funext x
      by_cases hx : x = c <;> simp [hx]

end VWorld

inductive CommitOutcome (α : Type) where
  | stale
  | rejected (w : VWorld α)
  | accepted (w' : VWorld α)

namespace CommitOutcome

variable {α : Type}

def world : CommitOutcome α → Option (VWorld α)
  | .stale => none
  | .rejected w => some w
  | .accepted w => some w

def isAccepted : CommitOutcome α → Bool
  | .accepted _ => true
  | _ => false

def isRejected : CommitOutcome α → Bool
  | .rejected _ => true
  | _ => false

theorem world_some {o : CommitOutcome α} {w : VWorld α} (h : o.world = some w) :
    o = .accepted w ∨ o = .rejected w := by
  cases o with
  | stale => simp [world] at h
  | rejected w' => simp [world] at h; exact Or.inr (by rw [h])
  | accepted w' => simp [world] at h; exact Or.inl (by rw [h])

end CommitOutcome

namespace VWorld

variable {α : Type}

def commit (w : VWorld α) (c : CellId) (expected : Nat) (g : α → Bool) (f : α → α) :
    CommitOutcome α :=
  match w.cell c with
  | none => .stale
  | some vc =>
      if vc.gen = expected then
        if g vc.val then .accepted (w.set c (f vc.val) (expected + 1))
        else .rejected (w.set c vc.val (expected + 1))
      else .stale

theorem commit_accepted {w : VWorld α} {c : CellId} {n : Nat} {g : α → Bool}
    {f : α → α} {v : α} (h : w.cell c = some ⟨v, n⟩) (hg : g v = true) :
    w.commit c n g f = .accepted (w.set c (f v) (n + 1)) := by
  simp [commit, h, hg]

theorem commit_rejected {w : VWorld α} {c : CellId} {n : Nat} {g : α → Bool}
    {f : α → α} {v : α} (h : w.cell c = some ⟨v, n⟩) (hg : g v = false) :
    w.commit c n g f = .rejected (w.set c v (n + 1)) := by
  simp [commit, h, hg]

theorem commit_stale {w : VWorld α} {c : CellId} {n m : Nat} {g : α → Bool}
    {f : α → α} {v : α} (h : w.cell c = some ⟨v, m⟩) (hne : m ≠ n) :
    w.commit c n g f = .stale := by
  simp [commit, h, hne]

theorem commit_accepted_preserves_other {w : VWorld α} {c d : CellId} {n : Nat}
    {f : α → α} {v : α} (hcd : c ≠ d) :
    (w.set c (f v) (n + 1)).cell d = w.cell d :=
  set_other w c d (f v) (n + 1) hcd.symm

theorem commit_rejected_preserves_other {w : VWorld α} {c d : CellId} {n : Nat}
    {v : α} (hcd : c ≠ d) :
    (w.set c v (n + 1)).cell d = w.cell d :=
  set_other w c d v (n + 1) hcd.symm

def take (w : VWorld α) (c : CellId) (expected : Nat) :
    Option (VCell α × VWorld α) :=
  match w.cell c with
  | none => none
  | some vc => if vc.gen = expected then some (vc, w.remove c) else none

def post (w : VWorld α) (c : CellId) (vc : VCell α) : Option (VWorld α) :=
  match w.cell c with
  | none => some (w.set c vc.val vc.gen)
  | some _ => none

theorem take_removes {w : VWorld α} {c : CellId} {n : Nat} {vc : VCell α}
    {w' : VWorld α} (h : w.take c n = some (vc, w')) : w'.cell c = none := by
  unfold take at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      rcases h with ⟨rfl, rfl⟩
      simp
    · simp at h

theorem take_take_blocks {w : VWorld α} {c : CellId} {n : Nat} {vc : VCell α}
    {w' : VWorld α} (h : w.take c n = some (vc, w')) : w'.take c n = none := by
  unfold take
  rw [take_removes h]

theorem post_requires_empty {w : VWorld α} {c : CellId} {vc : VCell α}
    {w' : VWorld α} (h : w.post c vc = some w') : w.cell c = none := by
  unfold post at h
  split at h
  · assumption
  · simp at h

theorem consume_post_atomic_same_cell {w : VWorld α} {c : CellId} {n : Nat}
    {vc : VCell α} {w' : VWorld α} (h : w.take c n = some (vc, w')) :
    w'.take c n = none :=
  take_take_blocks h

/-- The deployed consume/guard/re-post pattern equals the atomic commit step. -/
theorem take_post_commit_equiv {w : VWorld α} {c : CellId} {n : Nat}
    {g : α → Bool} {f : α → α} :
    (match w.cell c with
     | none => (CommitOutcome.stale : CommitOutcome α)
     | some _ =>
         match w.take c n with
         | none => .stale
         | some (vc', w1) =>
             match w1.post c (if g vc'.val then ⟨f vc'.val, n + 1⟩ else ⟨vc'.val, n + 1⟩) with
             | none => .stale
             | some w2 => if g vc'.val then .accepted w2 else .rejected w2)
      = w.commit c n g f := by
  cases hcell : w.cell c with
  | none => simp [commit, take, hcell]
  | some vc =>
      by_cases hgen : vc.gen = n
      · by_cases hg : g vc.val
        · simp [commit, take, post, hcell, hgen, hg, remove_set_same]
        · simp [commit, take, post, hcell, hgen, hg, remove_set_same]
      · simp [commit, take, hcell, hgen]

end VWorld

end RGen
