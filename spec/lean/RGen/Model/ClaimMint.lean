import RGen.Basic

/-!
# Claim validation and K-Asset mint

The deployed `Claim.validate` writes a `validating` receipt, releases the claim
cell, mints the K-Asset, and then commits the receipt. This module models the
claim side:

* `beginValidation` posts the receipt and refuses a second begin;
* `mint` records the minted K-Asset under the receipt, once;
* `commit` finalizes the claim from the receipt;
* `resume` performs the same commit and never mints.

The safety property is `at_most_one_reachable_kasset_per_claim`: the claim has a
single `kassetRef`, and no reachable step changes it once set. A minted K-Asset
that never commits is not reachable through the claim. `exactly_one_eventually`
is stated only under an explicit liveness assumption on `resume`.
-/

namespace RGen

inductive MintPhase where
  | open
  | validating
  | validated
  | rejected
  | withdrawn
  | expired
  deriving DecidableEq, Repr

def isFinalStatus : MintPhase → Bool
  | .validated => true
  | .rejected => true
  | _ => false

structure ValidationReceipt where
  claimStatus : MintPhase
  credentialUri : Id
  validator : Id
  height : Height
  kassetRef : Option Id
  deriving DecidableEq, Repr

structure ClaimMintState where
  uri : Id
  claimant : Id
  deadline : Height
  phase : MintPhase
  validator : Option Id
  kassetRef : Option Id
  receipt : Option ValidationReceipt
  deriving DecidableEq, Repr

namespace ClaimMintState

def beginValidation (s : ClaimMintState) (validator : Id) (claimStatus : MintPhase)
    (credentialUri : Id) (now : Height) : Option ClaimMintState :=
  if s.phase = .open ∧ validator ≠ s.claimant ∧ now ≤ s.deadline ∧
      s.kassetRef = none ∧ s.receipt = none ∧ isFinalStatus claimStatus = true then
    some { s with
      phase := .validating
      validator := some validator
      receipt := some ⟨claimStatus, credentialUri, validator, now, none⟩ }
  else none

def mint (s : ClaimMintState) (kasset : Id) : Option ClaimMintState :=
  match s.receipt with
  | none => none
  | some r =>
      if s.phase = .validating ∧ s.kassetRef = none ∧ r.kassetRef = none then
        some { s with receipt := some { r with kassetRef := some kasset } }
      else none

def commit (s : ClaimMintState) : Option ClaimMintState :=
  match s.receipt with
  | none => none
  | some r =>
      match r.kassetRef with
      | none => none
      | some k =>
          if s.phase = .validating ∧ s.kassetRef = none then
            some { s with phase := r.claimStatus, kassetRef := some k, receipt := none }
          else none

/-- Recovery finalizes the receipt. It never mints. -/
def resume (s : ClaimMintState) : Option ClaimMintState := commit s

/-- The claim's reachable K-Asset is the one in its single `kassetRef`. -/
def ReachableKAsset (s : ClaimMintState) (k : Id) : Prop := s.kassetRef = some k

theorem begin_blocks_second {s s' : ClaimMintState} {validator : Id}
    {claimStatus : MintPhase} {credentialUri : Id} {now : Height}
    (h : s.beginValidation validator claimStatus credentialUri now = some s') :
    s'.beginValidation validator claimStatus credentialUri now = none := by
  unfold beginValidation at h ⊢
  split at h
  · rename_i hg
    simp only [Option.some.injEq] at h
    rw [← h]
    simp [hg.2.2.2.2.1]
  · simp at h

theorem mint_once {s s' : ClaimMintState} {k k' : Id}
    (h : s.mint k = some s') : s'.mint k' = none := by
  unfold mint at h ⊢
  split at h
  · simp at h
  · rename_i r hr
    split at h
    · rename_i hg
      simp only [Option.some.injEq] at h
      rw [← h]
      simp [hr, hg.2]
    · simp at h

theorem mint_requires_receipt {s s' : ClaimMintState} {k : Id}
    (h : s.mint k = some s') : ∃ r, s.receipt = some r ∧ r.kassetRef = none := by
  unfold mint at h
  split at h
  · simp at h
  · rename_i r hr
    split at h
    · rename_i hg
      exact ⟨r, hr, hg.2.2⟩
    · simp at h

theorem commit_requires_intent {s s' : ClaimMintState}
    (h : s.commit = some s') :
    ∃ r k, s.receipt = some r ∧ r.kassetRef = some k ∧ s'.kassetRef = some k := by
  unfold commit at h
  split at h
  · simp at h
  · rename_i r hr
    split at h
    · simp at h
    · rename_i k hk
      split at h
      · rename_i hg
        simp only [Option.some.injEq] at h
        rw [← h]
        exact ⟨r, k, hr, hk, rfl⟩
      · simp at h

theorem commit_sets_kasset {s s' : ClaimMintState} {k : Id}
    (h : s.commit = some s') (hk : s'.kassetRef = some k) : s'.kassetRef = some k := hk

theorem resume_sets_from_receipt {s s' : ClaimMintState}
    (h : s.resume = some s') :
    ∃ r k, s.receipt = some r ∧ r.kassetRef = some k ∧ s'.kassetRef = some k := by
  unfold resume at h
  exact commit_requires_intent h

theorem resume_cannot_mint {s s' : ClaimMintState} {r : ValidationReceipt}
    (h : s.resume = some s') (hr : s.receipt = some r) (hk : r.kassetRef = none) :
    s'.kassetRef = none := by
  unfold resume at h
  unfold commit at h
  rw [hr] at h
  simp [hk] at h

theorem at_most_one_reachable_kasset_per_claim (s : ClaimMintState) {k1 k2 : Id}
    (h1 : s.ReachableKAsset k1) (h2 : s.ReachableKAsset k2) : k1 = k2 := by
  unfold ReachableKAsset at h1 h2
  rw [h1] at h2
  exact Option.some.inj h2

theorem orphan_kasset_unreachable (s : ClaimMintState) (h : s.kassetRef = none)
    (k : Id) : ¬ s.ReachableKAsset k := by
  unfold ReachableKAsset
  rw [h]
  simp

end ClaimMintState

/-- One claim-mint step. -/
inductive MintStep : ClaimMintState → ClaimMintState → Prop where
  | begin {s s' validator claimStatus credentialUri now}
      (h : s.beginValidation validator claimStatus credentialUri now = some s') :
      MintStep s s'
  | mint {s s' k} (h : s.mint k = some s') : MintStep s s'
  | commit {s s'} (h : s.commit = some s') : MintStep s s'
  | resume {s s'} (h : s.resume = some s') : MintStep s s'

inductive MintReach : ClaimMintState → ClaimMintState → Prop where
  | refl (s : ClaimMintState) : MintReach s s
  | step {s s' s''} (h : MintStep s s') (r : MintReach s' s'') : MintReach s s''

namespace ClaimMintState

/-- Once a claim names a K-Asset, no step changes it. -/
theorem step_kassetRef_stable {s s' : ClaimMintState} (h : MintStep s s')
    {k : Id} (hk : s.kassetRef = some k) : s'.kassetRef = some k := by
  cases h with
  | begin h =>
      unfold beginValidation at h
      split at h
      · rename_i hg
        rw [hk] at hg
        simp at hg
      · simp at h
  | mint h =>
      unfold mint at h
      split at h
      · simp at h
      · split at h
        · rename_i hg
          rw [hk] at hg
          simp at hg
        · simp at h
  | commit h =>
      unfold commit at h
      split at h
      · simp at h
      · split at h
        · simp at h
        · split at h
          · rename_i hg
            rw [hk] at hg
            simp at hg
          · simp at h
  | resume h =>
      unfold resume at h
      unfold commit at h
      split at h
      · simp at h
      · split at h
        · simp at h
        · split at h
          · rename_i hg
            rw [hk] at hg
            simp at hg
          · simp at h

theorem reach_kassetRef_stable {s s' : ClaimMintState} (h : MintReach s s')
    {k : Id} (hk : s.kassetRef = some k) : s'.kassetRef = some k := by
  induction h with
  | refl => exact hk
  | step hs _ ih => exact ih (step_kassetRef_stable hs hk)

/-- Every reachable K-Asset of a claim is the same one. -/
theorem at_most_one_reachable_kasset_across_reach {s s' : ClaimMintState}
    (h : MintReach s s') {k1 k2 : Id} (h1 : s.ReachableKAsset k1)
    (h2 : s'.ReachableKAsset k2) : k1 = k2 := by
  unfold ReachableKAsset at h1 h2
  have hs := reach_kassetRef_stable h h1
  rw [hs] at h2
  exact Option.some.inj h2

end ClaimMintState

/-- Liveness: a successful resume commits exactly the K-Asset named by the receipt. -/
theorem exactly_one_eventually {s s' : ClaimMintState}
    (h : s.resume = some s') :
    ∃ r k, s.receipt = some r ∧ r.kassetRef = some k ∧ s'.kassetRef = some k :=
  ClaimMintState.resume_sets_from_receipt h

end RGen
