import RGen.Basic

/-!
# Identity reservation

The deployed `IdentityFactory.create` is a reservation followed by a mint and a
two-step finalize. This module models that protocol:

* `reserve` refuses a claimed address, an active/minted pending entry, and an
  unexpired reservation; it replaces an expired reservation.
* `recordMinted` records the identity URI under a live reservation.
* `commit` requires a minted reservation, the same URI, and an unclaimed address.
* `resume` completes a minted reservation without minting; it refuses a claimed
  address.
* `reclaim` removes an expired reservation.

The safety property is `reach_byAddress_stable`: once the directory maps an
address to a URI, no reachable step changes that mapping. Combined with
`reserve_refuses_claimed`, a second identity cannot be committed for the same
address. A minted URI that never commits is not reachable through the directory.
-/

namespace RGen

inductive PendingStatus where
  | reserving
  | minted
  | active
  deriving DecidableEq, Repr

structure PendingEntry where
  status : PendingStatus
  uri : Option Id
  expiresAt : Height
  deriving DecidableEq, Repr

structure ReservedDirectory where
  byAddress : Id → Option Id
  pending : Id → Option PendingEntry

namespace ReservedDirectory

def setBy (d : ReservedDirectory) (a u : Id) : ReservedDirectory :=
  { d with byAddress := fun x => if x = a then some u else d.byAddress x }

def setPending (d : ReservedDirectory) (a : Id) (p : Option PendingEntry) :
    ReservedDirectory :=
  { d with pending := fun x => if x = a then p else d.pending x }

@[simp] theorem setBy_same (d : ReservedDirectory) (a u : Id) :
    (d.setBy a u).byAddress a = some u := by
  simp [setBy]

theorem setBy_other (d : ReservedDirectory) (a b u : Id) (h : b ≠ a) :
    (d.setBy a u).byAddress b = d.byAddress b := by
  simp [setBy, h]

@[simp] theorem setPending_same (d : ReservedDirectory) (a : Id)
    (p : Option PendingEntry) : (d.setPending a p).pending a = p := by
  simp [setPending]

theorem setPending_other (d : ReservedDirectory) (a b : Id)
    (p : Option PendingEntry) (h : b ≠ a) :
    (d.setPending a p).pending b = d.pending b := by
  simp [setPending, h]

@[simp] theorem setPending_preserves_byAddress (d : ReservedDirectory) (a : Id)
    (p : Option PendingEntry) : (d.setPending a p).byAddress = d.byAddress :=
  rfl

/-- Reserve the address for this attempt. An expired reservation is replaced. -/
def reserve (d : ReservedDirectory) (a : Id) (now : Height) : Option ReservedDirectory :=
  match d.byAddress a with
  | some _ => none
  | none =>
      match d.pending a with
      | none =>
          some (d.setPending a (some ⟨.reserving, none, now + 100⟩))
      | some p =>
          match p.status with
          | .reserving =>
              if p.expiresAt > now then none
              else some (d.setPending a (some ⟨.reserving, none, now + 100⟩))
          | .minted => none
          | .active => none

/-- Record the freshly minted identity URI under a live reservation. -/
def recordMinted (d : ReservedDirectory) (a u : Id) : Option ReservedDirectory :=
  match d.pending a with
  | none => none
  | some p =>
      if p.status = .reserving then
        some (d.setPending a (some { p with status := .minted, uri := some u }))
      else none

/-- Commit a minted identity to the directory. The address must still be unclaimed. -/
def commit (d : ReservedDirectory) (a u : Id) : Option ReservedDirectory :=
  match d.pending a with
  | none => none
  | some p =>
      if p.status = .minted ∧ p.uri = some u ∧ d.byAddress a = none then
        some ((d.setBy a u).setPending a (some ⟨.active, some u, 0⟩))
      else none

/-- Complete a minted reservation without minting. Refuses a claimed address. -/
def resume (d : ReservedDirectory) (a : Id) : Option ReservedDirectory :=
  match d.byAddress a with
  | some _ => none
  | none =>
      match d.pending a with
      | none => none
      | some p =>
          match p.uri with
          | none => none
          | some u =>
              if p.status = .minted then
                some ((d.setBy a u).setPending a (some ⟨.active, some u, 0⟩))
              else none

/-- Read the URI of an active pending entry. -/
def resumeActive (d : ReservedDirectory) (a : Id) : Option Id :=
  match d.pending a with
  | some p => if p.status = .active then p.uri else none
  | none => none

/-- Remove an expired reservation. -/
def reclaim (d : ReservedDirectory) (a : Id) (now : Height) :
    Option ReservedDirectory :=
  match d.pending a with
  | none => none
  | some p =>
      if p.status = .reserving ∧ p.expiresAt ≤ now then
        some (d.setPending a none)
      else none

/-! ### Local safety -/

theorem reserve_refuses_claimed (d : ReservedDirectory) (a u : Id) (now : Height)
    (h : d.byAddress a = some u) : d.reserve a now = none := by
  simp [reserve, h]

theorem reserve_refuses_active (d : ReservedDirectory) (a : Id) (now : Height)
    (p : PendingEntry) (hp : d.pending a = some p) (hs : p.status = .active) :
    d.reserve a now = none := by
  unfold reserve
  split
  · rfl
  · simp [hp, hs]

theorem reserve_refuses_minted (d : ReservedDirectory) (a : Id) (now : Height)
    (p : PendingEntry) (hp : d.pending a = some p) (hs : p.status = .minted) :
    d.reserve a now = none := by
  unfold reserve
  split
  · rfl
  · simp [hp, hs]

theorem reserve_refuses_unexpired (d : ReservedDirectory) (a : Id) (now : Height)
    (p : PendingEntry) (hp : d.pending a = some p) (hs : p.status = .reserving)
    (hexp : p.expiresAt > now) : d.reserve a now = none := by
  unfold reserve
  split
  · rfl
  · simp [hp, hs, hexp]

theorem commit_requires_minted (d : ReservedDirectory) (a u : Id) (d' : ReservedDirectory)
    (h : d.commit a u = some d') :
    ∃ p, d.pending a = some p ∧ p.status = .minted ∧ p.uri = some u ∧
      d.byAddress a = none := by
  unfold commit at h
  split at h
  · simp at h
  · rename_i p hp
    split at h
    · rename_i hg
      exact ⟨p, hp, hg.1, hg.2.1, hg.2.2⟩
    · simp at h

theorem commit_sets_byAddress (d : ReservedDirectory) (a u : Id) (d' : ReservedDirectory)
    (h : d.commit a u = some d') : d'.byAddress a = some u := by
  unfold commit at h
  split at h
  · simp at h
  · split at h
    · have hd : d' = (d.setBy a u).setPending a (some ⟨.active, some u, 0⟩) := by
        simpa using h.symm
      subst hd
      simp [setBy, setPending]
    · simp at h

theorem commit_preserves_other (d : ReservedDirectory) (a b u : Id) (d' : ReservedDirectory)
    (h : d.commit a u = some d') (hne : b ≠ a) : d'.byAddress b = d.byAddress b := by
  unfold commit at h
  split at h
  · simp at h
  · split at h
    · have hd : d' = (d.setBy a u).setPending a (some ⟨.active, some u, 0⟩) := by
        simpa using h.symm
      subst hd
      simp [setBy_other, setPending_preserves_byAddress, hne]
    · simp at h

theorem resume_refuses_claimed (d : ReservedDirectory) (a u : Id)
    (h : d.byAddress a = some u) : d.resume a = none := by
  simp [resume, h]

theorem resume_sets_byAddress (d : ReservedDirectory) (a u : Id) (d' : ReservedDirectory)
    (h : d.resume a = some d') (hu : d'.byAddress a = some u) :
    d'.byAddress a = some u := hu

theorem resume_preserves_other (d : ReservedDirectory) (a b : Id) (d' : ReservedDirectory)
    (h : d.resume a = some d') (hne : b ≠ a) : d'.byAddress b = d.byAddress b := by
  unfold resume at h
  split at h
  · simp at h
  · split at h
    · simp at h
    · split at h
      · simp at h
      · split at h
        · simp only [Option.some.injEq] at h
          rw [← h]
          simp [setBy_other, setPending_preserves_byAddress, hne]
        · simp at h

theorem reclaim_clears (d : ReservedDirectory) (a : Id) (now : Height)
    (d' : ReservedDirectory) (h : d.reclaim a now = some d') : d'.pending a = none := by
  unfold reclaim at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      simp [setPending]
    · simp at h

theorem stale_reservation_cannot_commit (d : ReservedDirectory) (a u : Id)
    (now : Height) (d' : ReservedDirectory) (h : d.reclaim a now = some d') :
    d'.commit a u = none := by
  unfold commit
  rw [reclaim_clears d a now d' h]

theorem commit_sets_uri (d : ReservedDirectory) (a u : Id) (d' : ReservedDirectory)
    (h : d.commit a u = some d') : d'.byAddress a = some u :=
  commit_sets_byAddress d a u d' h

/-- An identity URI not in the directory is not reachable through the directory. -/
def lookupBy (d : ReservedDirectory) (a : Id) : Option Id := d.byAddress a

theorem orphan_unreachable (d : ReservedDirectory) (a : Id) (h : d.byAddress a = none) :
    d.lookupBy a = none := h

end ReservedDirectory

/-- One protocol step. -/
inductive ReservationStep : ReservedDirectory → ReservedDirectory → Prop where
  | reserve {d d' a now} (h : d.reserve a now = some d') : ReservationStep d d'
  | recordMinted {d d' a u} (h : d.recordMinted a u = some d') : ReservationStep d d'
  | commit {d d' a u} (h : d.commit a u = some d') : ReservationStep d d'
  | resume {d d' a} (h : d.resume a = some d') : ReservationStep d d'
  | reclaim {d d' a now} (h : d.reclaim a now = some d') : ReservationStep d d'

/-- Reflexive-transitive closure of the protocol steps. -/
inductive ReservationReach : ReservedDirectory → ReservedDirectory → Prop where
  | refl (d : ReservedDirectory) : ReservationReach d d
  | step {d d' d''} (h : ReservationStep d d') (r : ReservationReach d' d'') :
      ReservationReach d d''

namespace ReservedDirectory

theorem reserve_byAddress (d : ReservedDirectory) (a : Id) (now : Height)
    (d' : ReservedDirectory) (h : d.reserve a now = some d') :
    d'.byAddress = d.byAddress := by
  unfold reserve at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      rfl
    · split at h
      · split at h
        · simp at h
        · simp only [Option.some.injEq] at h
          rw [← h]
          rfl
      · simp at h
      · simp at h

theorem recordMinted_byAddress (d : ReservedDirectory) (a u : Id)
    (d' : ReservedDirectory) (h : d.recordMinted a u = some d') :
    d'.byAddress = d.byAddress := by
  unfold recordMinted at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      rfl
    · simp at h

theorem reclaim_byAddress (d : ReservedDirectory) (a : Id) (now : Height)
    (d' : ReservedDirectory) (h : d.reclaim a now = some d') :
    d'.byAddress = d.byAddress := by
  unfold reclaim at h
  split at h
  · simp at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
      rfl
    · simp at h

/-- Once an address is claimed, every protocol step preserves its URI. -/
theorem step_byAddress_stable {d d' : ReservedDirectory} (h : ReservationStep d d')
    {a u : Id} (hb : d.byAddress a = some u) : d'.byAddress a = some u := by
  cases h with
  | reserve h =>
      rename_i a' now'
      by_cases heq : a' = a
      · subst a'
        have hnone := reserve_refuses_claimed d a u now' hb
        rw [hnone] at h
        simp at h
      · rw [reserve_byAddress d a' now' d' h]
        exact hb
  | recordMinted h =>
      rename_i a' u'
      rw [recordMinted_byAddress d a' u' d' h]
      exact hb
  | commit h =>
      rename_i a' u'
      by_cases heq : a' = a
      · subst a'
        have hnone := (commit_requires_minted d a u' d' h).choose_spec.2.2.2
        rw [hb] at hnone
        simp at hnone
      · rw [commit_preserves_other d a' a u' d' h (Ne.symm heq)]
        exact hb
  | resume h =>
      rename_i a'
      by_cases heq : a' = a
      · subst a'
        have hnone := resume_refuses_claimed d a u hb
        rw [hnone] at h
        simp at h
      · rw [resume_preserves_other d a' a d' h (Ne.symm heq)]
        exact hb
  | reclaim h =>
      rename_i a' now'
      rw [reclaim_byAddress d a' now' d' h]
      exact hb

/-- The directory mapping is stable along every reachable trace. -/
theorem reach_byAddress_stable {d d' : ReservedDirectory} (h : ReservationReach d d')
    {a u : Id} (hb : d.byAddress a = some u) : d'.byAddress a = some u := by
  induction h with
  | refl => exact hb
  | step hs _ ih => exact ih (step_byAddress_stable hs hb)

/-- At most one identity is reachable for an address: the mapping never changes. -/
theorem at_most_one_identity_per_address {d d' : ReservedDirectory}
    (h : ReservationReach d d') {a u v : Id} (hu : d.byAddress a = some u)
    (hv : d'.byAddress a = some v) : u = v := by
  have hs := reach_byAddress_stable h hu
  rw [hs] at hv
  exact Option.some.inj hv

end ReservedDirectory

end RGen
