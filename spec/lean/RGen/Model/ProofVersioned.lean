import RGen.Linear.Exec
import RGen.Model.Proof

/-!
# One-shot proof cells in the versioned model

The deployed proof cell is `{data, used}`. `proofStep` is the cell step: it marks `used`
once and rejects every later take. The versioned event form makes the consumption
generation explicit, so `runExec_no_same_expected` rules out two takes at one generation
and `proofStep_second` rules out a second take on the post-state.
-/

namespace RGen

variable {α : Type}

def proofStep (p : ProofState α) : Option (ProofState α) :=
  if p.used then none else some { p with used := true }

theorem proofStep_once (p : ProofState α) (h : p.used = false) :
    proofStep p = some { p with used := true } := by
  simp [proofStep, h]

theorem proofStep_second (p : ProofState α) (h : p.used = true) :
    proofStep p = none := by
  simp [proofStep, h]

theorem proofStep_marks_used {p p' : ProofState α} (h : proofStep p = some p') :
    p'.used = true := by
  unfold proofStep at h
  split at h
  · simp at h
  · simp at h
    rcases h with rfl
    rfl

theorem proofStep_snapshot {p p' : ProofState α} (h : proofStep p = some p') :
    p'.data = p.data := by
  unfold proofStep at h
  split at h
  · simp at h
  · simp at h
    rcases h with rfl
    rfl

theorem proofStep_second_rejected {p p' : ProofState α} (h : proofStep p = some p') :
    proofStep p' = none :=
  proofStep_second p' (proofStep_marks_used h)

def proofEvent (c : CellId) (expected : Nat) : Event (ProofState α) :=
  ⟨c, expected, proofStep⟩

theorem proofEvent_accepts {w : VWorld (ProofState α)} {c : CellId} {n : Nat}
    {p : ProofState α} (hcell : w.cell c = some ⟨p, n⟩) (hp : p.used = false) :
    (proofEvent c n).apply w = .accepted (w.set c { p with used := true } (n + 1)) := by
  simp [Event.apply, proofEvent, proofStep_once p hp, hcell]

theorem proofEvent_rejects_used {w : VWorld (ProofState α)} {c : CellId} {n : Nat}
    {p : ProofState α} (hcell : w.cell c = some ⟨p, n⟩) (hp : p.used = true) :
    (proofEvent c n).apply w = .rejected (w.set c p (n + 1)) := by
  simp [Event.apply, proofEvent, proofStep_second p hp, hcell]

/-- After an accepted take, the next take on the same cell rejects; the payload is not
reachable a second time. -/
theorem proof_no_second_payload {w : VWorld (ProofState α)} {c : CellId} {n : Nat}
    {p : ProofState α} (_hcell : w.cell c = some ⟨p, n⟩) (_hp : p.used = false) :
    (proofEvent c (n + 1)).apply (w.set c { p with used := true } (n + 1))
      = .rejected (w.set c { p with used := true } (n + 2)) := by
  simp [Event.apply, proofEvent, proofStep_second]

theorem proof_take_once_versioned {w : VWorld (ProofState α)} {c : CellId} {n : Nat}
    {p : ProofState α} (hcell : w.cell c = some ⟨p, n⟩) (hp : p.used = false) :
    ∃ w', (proofEvent c n).apply w = .accepted w' ∧
      CommitOutcome.isRejected ((proofEvent c (n + 1)).apply w') = true := by
  refine ⟨w.set c { p with used := true } (n + 1), proofEvent_accepts hcell hp, ?_⟩
  rw [proof_no_second_payload hcell hp]
  rfl

end RGen
