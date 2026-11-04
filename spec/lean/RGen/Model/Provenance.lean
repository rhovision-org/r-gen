import RGen.Basic

/-!
# Provenance

Per-asset provenance is append-only: anchors and comments are only added, never
removed or rewritten. A duplicate anchor is refused, and verification is
monotone: once an anchor verifies it keeps verifying. Only the writer may append.
-/

namespace RGen

structure ProvenanceState where
  asset : Id
  writers : List Id
  anchors : List (Id × Id)
  comments : List Id
  deriving DecidableEq, Repr

namespace ProvenanceState

def addAnchor (s : ProvenanceState) (caller : Id) (anchor : Id × Id) :
    Option ProvenanceState :=
  if caller ∈ s.writers ∧ anchor.1 ≠ 0 ∧ anchor ∉ s.anchors then
    some { s with anchors := anchor :: s.anchors }
  else none

def addComment (s : ProvenanceState) (caller : Id) (comment : Id) :
    Option ProvenanceState :=
  if caller ∈ s.writers then
    some { s with comments := comment :: s.comments }
  else none

def verify (s : ProvenanceState) (ref : Id) : Bool :=
  decide (∃ a, a ∈ s.anchors ∧ a.2 = ref)

/-! ### Append-only -/

theorem addAnchor_requires_writer {s s' : ProvenanceState} {caller : Id} {a : Id × Id}
    (h : s.addAnchor caller a = some s') : caller ∈ s.writers := by
  unfold addAnchor at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem addAnchor_nonempty_hash {s s' : ProvenanceState} {caller : Id} {a : Id × Id}
    (h : s.addAnchor caller a = some s') : a.1 ≠ 0 := by
  unfold addAnchor at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem addAnchor_appends {s s' : ProvenanceState} {caller : Id} {a : Id × Id}
    (h : s.addAnchor caller a = some s') : s'.anchors = a :: s.anchors := by
  unfold addAnchor at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem addComment_appends {s s' : ProvenanceState} {caller : Id} {c : Id}
    (h : s.addComment caller c = some s') : s'.comments = c :: s.comments := by
  unfold addComment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem anchors_append_only {s s' : ProvenanceState} {caller : Id} {a b : Id × Id}
    (h : s.addAnchor caller a = some s') (hb : b ∈ s.anchors) : b ∈ s'.anchors := by
  unfold addAnchor at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact List.mem_cons_of_mem a hb
  · simp at h

/-- A duplicate anchor is refused. -/
theorem addAnchor_refused_duplicate {s : ProvenanceState} {caller : Id} {a : Id × Id}
    (ha : a ∈ s.anchors) : s.addAnchor caller a = none := by
  unfold addAnchor
  simp [ha]

theorem anchor_unique {s s' : ProvenanceState} {caller : Id} {a : Id × Id}
    (h : s.addAnchor caller a = some s') : s'.addAnchor caller a = none := by
  apply addAnchor_refused_duplicate
  unfold addAnchor at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact List.mem_cons_self a s.anchors
  · simp at h

/-- Verification is monotone in anchors. -/
theorem verify_monotone {s s' : ProvenanceState} {caller : Id} {a : Id × Id}
    (h : s.addAnchor caller a = some s') {ref : Id} (hv : s.verify ref = true) :
    s'.verify ref = true := by
  unfold addAnchor at h
  split at h
  · rename_i hg
    simp only [Option.some.injEq] at h
    rcases h with rfl
    unfold verify at hv ⊢
    rw [decide_eq_true_eq] at hv ⊢
    rcases hv with ⟨x, hx, hr⟩
    exact ⟨x, List.mem_cons_of_mem a hx, hr⟩
  · simp at h

theorem addComment_requires_writer {s s' : ProvenanceState} {caller : Id} {c : Id}
    (h : s.addComment caller c = some s') : caller ∈ s.writers := by
  unfold addComment at h
  split at h
  · rename_i hg
    exact hg
  · simp at h

theorem comments_append_only {s s' : ProvenanceState} {caller : Id} {c d : Id}
    (h : s.addComment caller c = some s') (hd : d ∈ s.comments) : d ∈ s'.comments := by
  unfold addComment at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact List.mem_cons_of_mem c hd
  · simp at h

end ProvenanceState

end RGen
