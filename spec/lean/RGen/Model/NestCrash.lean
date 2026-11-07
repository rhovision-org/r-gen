import RGen.Basic

/-!
# Nest reservation and crash safety

The deployed `KAsset.nest` checks children, reserves their approval proofs, and
only then commits the parent's `childRefs`. This module models the reservation
discipline:

* `check` records a successful child check;
* `reserve` requires a prior successful check and an unused proof;
* `commit` requires every declared child to be reserved, marks those proofs
  used, and records the parent as committed;
* `release` returns one reservation to unused;
* `releaseAll` returns every reservation to unused.

The safety properties are: a reserve requires a check; a commit requires every
child reserved; a proof is not used twice; and a crash before commit leaves all
proofs releasable (`crash_release_all`).
-/

namespace RGen

structure NestState where
  checked : List Id
  reserved : List Id
  used : List Id
  committed : Bool
  deriving DecidableEq, Repr

def checkedResult (c : Id) (ok : Bool) (s : NestState) : NestState :=
  if ok then { s with checked := c :: s.checked } else s

def reserveProof (c : Id) (s : NestState) : Option NestState :=
  if c ∈ s.checked ∧ c ∉ s.reserved ∧ c ∉ s.used then
    some { s with reserved := c :: s.reserved }
  else none

def releaseProof (c : Id) (s : NestState) : Option NestState :=
  if c ∈ s.reserved then
    some { s with reserved := s.reserved.filter (fun x => x != c) }
  else none

def commitParent (children : List Id) (s : NestState) : Option NestState :=
  if s.committed then none
  else if ∀ c ∈ children, c ∈ s.reserved then
    some { s with
      reserved := s.reserved.filter (fun x => x ∉ children)
      used := children ++ s.used
      committed := true }
  else none

/-- A crash-recovery release returns every reservation to unused. -/
def releaseAll (s : NestState) : NestState :=
  { s with reserved := [] }

/-- Used proofs exist only after a commit. -/
def Consistent (s : NestState) : Prop := s.used = [] ∨ s.committed = true

theorem check_consistent (c : Id) (ok : Bool) (s : NestState) (h : Consistent s) :
    Consistent (checkedResult c ok s) := by
  unfold Consistent at h ⊢
  unfold checkedResult
  split
  · exact h
  · exact h

theorem reserve_consistent {c : Id} {s s' : NestState}
    (h : reserveProof c s = some s') (hc : Consistent s) : Consistent s' := by
  unfold reserveProof at h
  split at h
  · simp only [Option.some.injEq] at h
    rw [← h]
    exact hc
  · simp at h

theorem release_consistent {c : Id} {s s' : NestState}
    (h : releaseProof c s = some s') (hc : Consistent s) : Consistent s' := by
  unfold releaseProof at h
  split at h
  · simp only [Option.some.injEq] at h
    rw [← h]
    exact hc
  · simp at h

theorem commit_consistent {children : List Id} {s s' : NestState}
    (h : commitParent children s = some s') : Consistent s' := by
  unfold Consistent
  right
  unfold commitParent at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
    · simp at h

theorem reserve_requires_check {c : Id} {s s' : NestState}
    (h : reserveProof c s = some s') : c ∈ s.checked := by
  unfold reserveProof at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem reserve_requires_unused {c : Id} {s s' : NestState}
    (h : reserveProof c s = some s') : c ∉ s.reserved ∧ c ∉ s.used := by
  unfold reserveProof at h
  split at h
  · rename_i hg
    exact ⟨hg.2.1, hg.2.2⟩
  · simp at h

theorem failed_check_no_reserve {c : Id} {s : NestState} (h : c ∉ s.checked) :
    reserveProof c (checkedResult c false s) = none := by
  unfold reserveProof checkedResult
  simp [h]

theorem commit_requires_all_reserved {children : List Id} {s s' : NestState}
    (h : commitParent children s = some s') : ∀ c ∈ children, c ∈ s.reserved := by
  unfold commitParent at h
  split at h
  · simp at h
  · split at h
    · rename_i hg
      exact hg
    · simp at h

theorem commit_marks_used {children : List Id} {s s' : NestState}
    (h : commitParent children s = some s') : ∀ c ∈ children, c ∈ s'.used := by
  unfold commitParent at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      intro c hc
      simp [hc]
    · simp at h

theorem commit_once {children : List Id} {s s' : NestState}
    (h : commitParent children s = some s') :
    commitParent children s' = none := by
  unfold commitParent at h ⊢
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      simp
    · simp at h

theorem release_restores {c : Id} {s s' : NestState}
    (h : releaseProof c s = some s') : c ∉ s'.reserved := by
  unfold releaseProof at h
  split at h
  · simp only [Option.some.injEq] at h
    rw [← h]
    intro hmem
    rw [List.mem_filter] at hmem
    simp at hmem
  · simp at h

theorem release_all_unused (s : NestState) : (releaseAll s).reserved = [] := rfl

/-- A crash before commit leaves no used proof and no reservation. -/
theorem crash_release_all {s : NestState} (hc : Consistent s)
    (hcommit : s.committed = false) :
    (releaseAll s).used = [] ∧ (releaseAll s).reserved = [] := by
  unfold Consistent at hc
  rcases hc with hused | hcommitted
  · exact ⟨by simpa [releaseAll] using hused, rfl⟩
  · rw [hcommit] at hcommitted
    simp at hcommitted

theorem nest_proof_not_burned {s : NestState} (hc : Consistent s)
    (hcommit : s.committed = false) (c : Id) : c ∉ (releaseAll s).used := by
  have h := crash_release_all hc hcommit
  rw [h.1]
  simp

end RGen
