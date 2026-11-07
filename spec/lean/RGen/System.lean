import RGen.Model.IdentityReservation
import RGen.Model.ClaimMint
import RGen.Model.ProofCapability

/-!
# Composed system

The per-primitive models are composed into one world: the identity directory,
the claims, the K-Asset-to-claim links, and the private proof cells.

`LinkConsistent` says every link points at a claim whose final `kassetRef` names
that K-Asset. A link is created only by `kassetLink`, after the claim commit, so
a minted-but-uncommitted K-Asset is not reachable through the claim. From the
invariant follows `AtMostOneLinkedKAsset`: one claim cannot have two linked
K-Assets. Directory stability is the composed form of the identity-reservation
result.
-/

namespace RGen

structure System where
  directory : ReservedDirectory
  claims : Id → Option ClaimMintState
  kassetClaim : Id → Option Id
  proofs : Id → Option (ProofCap Unit)

def withDirectory (sys : System) (d : ReservedDirectory) : System :=
  { sys with directory := d }

def setClaim (sys : System) (c : Id) (s : ClaimMintState) : System :=
  { sys with claims := fun x => if x = c then some s else sys.claims x }

def setLink (sys : System) (k c : Id) : System :=
  { sys with kassetClaim := fun x => if x = k then some c else sys.kassetClaim x }

def setProof (sys : System) (p : Id) (cap : ProofCap Unit) : System :=
  { sys with proofs := fun x => if x = p then some cap else sys.proofs x }

def LinkConsistent (sys : System) : Prop :=
  ∀ k c, sys.kassetClaim k = some c →
    ∃ s, sys.claims c = some s ∧ s.kassetRef = some k

def AtMostOneLinkedKAsset (sys : System) : Prop :=
  ∀ c k1 k2, sys.kassetClaim k1 = some c → sys.kassetClaim k2 = some c → k1 = k2

theorem link_consistent_at_most_one (sys : System) (h : LinkConsistent sys) :
    AtMostOneLinkedKAsset sys := by
  unfold AtMostOneLinkedKAsset
  intro c k1 k2 h1 h2
  unfold LinkConsistent at h
  rcases h k1 c h1 with ⟨s1, hs1, hk1⟩
  rcases h k2 c h2 with ⟨s2, hs2, hk2⟩
  have hseq : s1 = s2 := by
    rw [hs1] at hs2
    exact Option.some.inj hs2
  subst s2
  rw [hk1] at hk2
  exact Option.some.inj hk2

/-- A system step. `claimResume` is a derived `claimCommit` step (see below). -/
inductive SystemStep : System → System → Prop where
  | identity {sys d'} (h : ReservationStep sys.directory d') :
      SystemStep sys (withDirectory sys d')
  | claimBegin {sys c s s' v cs cu now} (hc : sys.claims c = some s)
      (h : s.beginValidation v cs cu now = some s') :
      SystemStep sys (setClaim sys c s')
  | claimMint {sys c s s' k} (hc : sys.claims c = some s)
      (h : s.mint k = some s') :
      SystemStep sys (setClaim sys c s')
  | claimCommit {sys c s s'} (hc : sys.claims c = some s)
      (h : s.commit = some s') :
      SystemStep sys (setClaim sys c s')
  | kassetLink {sys c s k} (hc : sys.claims c = some s)
      (hk : s.kassetRef = some k) :
      SystemStep sys (setLink sys k c)
  | proofTake {sys p caller d cap cap'} (hp : sys.proofs p = some cap)
      (h : cap.take caller = some (d, cap')) :
      SystemStep sys (setProof sys p cap')

/-- Resume is the commit arm on the claim side. -/
theorem claimResumeStep {sys c s s'} (hc : sys.claims c = some s)
    (h : s.resume = some s') : SystemStep sys (setClaim sys c s') := by
  unfold ClaimMintState.resume at h
  exact SystemStep.claimCommit hc h

inductive SystemReach : System → System → Prop where
  | refl (sys : System) : SystemReach sys sys
  | step {sys sys' sys''} (h : SystemStep sys sys') (r : SystemReach sys' sys'') :
      SystemReach sys sys''

namespace SystemStep

theorem link_consistent {sys sys' : System} (hstep : SystemStep sys sys')
    (h : LinkConsistent sys) : LinkConsistent sys' := by
  cases hstep with
  | identity hd =>
      simpa [withDirectory] using h
  | claimBegin hc hb =>
      rename_i c s s' v cs cu now
      unfold LinkConsistent at h ⊢
      intro k c' hk
      by_cases hceq : c' = c
      · subst c'
        rcases h k c hk with ⟨s_link, hs, hlink⟩
        rw [hc] at hs
        have hs_eq : s = s_link := Option.some.inj hs
        subst s_link
        unfold ClaimMintState.beginValidation at hb
        split at hb
        · rename_i hg
          rw [hg.2.2.2.1] at hlink
          simp at hlink
        · simp at hb
      · rcases h k c' hk with ⟨s_link, hs, hlink⟩
        exact ⟨s_link, by simp [setClaim, hceq, hs], hlink⟩
  | claimMint hc hm =>
      rename_i c s s' k
      unfold LinkConsistent at h ⊢
      intro k' c' hk'
      by_cases hceq : c' = c
      · subst c'
        rcases h k' c hk' with ⟨s_link, hs, hlink⟩
        rw [hc] at hs
        have hs_eq : s = s_link := Option.some.inj hs
        subst s_link
        unfold ClaimMintState.mint at hm
        split at hm
        · simp at hm
        · split at hm
          · rename_i hg
            rw [hg.2.1] at hlink
            simp at hlink
          · simp at hm
      · rcases h k' c' hk' with ⟨s_link, hs, hlink⟩
        exact ⟨s_link, by simp [setClaim, hceq, hs], hlink⟩
  | claimCommit hc hcom =>
      rename_i c s s'
      unfold LinkConsistent at h ⊢
      intro k c' hk
      by_cases hceq : c' = c
      · subst c'
        rcases h k c hk with ⟨s_link, hs, hlink⟩
        rw [hc] at hs
        have hs_eq : s = s_link := Option.some.inj hs
        subst s_link
        unfold ClaimMintState.commit at hcom
        split at hcom
        · simp at hcom
        · split at hcom
          · simp at hcom
          · split at hcom
            · rename_i hg
              rw [hg.2] at hlink
              simp at hlink
            · simp at hcom
      · rcases h k c' hk with ⟨s_link, hs, hlink⟩
        exact ⟨s_link, by simp [setClaim, hceq, hs], hlink⟩
  | kassetLink hc hk =>
      rename_i c s k
      unfold LinkConsistent at h ⊢
      intro k' c' hlink
      by_cases hceq : c' = c
      · subst c'
        by_cases hkeq : k' = k
        · subst k'
          exact ⟨s, by simp [setLink, hc], hk⟩
        · have hlink_old : sys.kassetClaim k' = some c := by
            simpa [setLink, hkeq] using hlink
          rcases h k' c hlink_old with ⟨s_link, hs, hlink_old'⟩
          rw [hc] at hs
          have hs_eq : s = s_link := Option.some.inj hs
          subst s_link
          rw [hk] at hlink_old'
          exact (hkeq (Option.some.inj hlink_old').symm).elim
      · by_cases hkeq : k' = k
        · subst k'
          simp [setLink] at hlink
          exact (hceq hlink.symm).elim
        · have hlink_old : sys.kassetClaim k' = some c' := by
            simpa [setLink, hkeq] using hlink
          rcases h k' c' hlink_old with ⟨s_link, hs, hlink_old'⟩
          exact ⟨s_link, by simpa [setLink] using hs, hlink_old'⟩
  | proofTake hp ht =>
      simpa [setProof] using h

end SystemStep

namespace SystemReach

theorem link_consistent {sys sys' : System} (h : SystemReach sys sys')
    (hc : LinkConsistent sys) : LinkConsistent sys' := by
  induction h with
  | refl => exact hc
  | step hs _ ih => exact ih (SystemStep.link_consistent hs hc)

theorem at_most_one_linked_kasset {sys sys' : System} (h : SystemReach sys sys')
    (hc : LinkConsistent sys) : AtMostOneLinkedKAsset sys' :=
  link_consistent_at_most_one sys' (link_consistent h hc)

end SystemReach

namespace SystemStep

theorem directory_stable {sys sys' : System} (hstep : SystemStep sys sys')
    {a u : Id} (hb : sys.directory.byAddress a = some u) :
    sys'.directory.byAddress a = some u := by
  cases hstep with
  | identity hd => exact ReservedDirectory.step_byAddress_stable hd hb
  | claimBegin _ _ => simpa [setClaim] using hb
  | claimMint _ _ => simpa [setClaim] using hb
  | claimCommit _ _ => simpa [setClaim] using hb
  | kassetLink _ _ => simpa [setLink] using hb
  | proofTake _ _ => simpa [setProof] using hb

end SystemStep

namespace SystemReach

theorem directory_stable {sys sys' : System} (h : SystemReach sys sys')
    {a u : Id} (hb : sys.directory.byAddress a = some u) :
    sys'.directory.byAddress a = some u := by
  induction h with
  | refl => exact hb
  | step hs _ ih => exact ih (SystemStep.directory_stable hs hb)

end SystemReach

/-- Composed safety: link consistency, one link per claim, and directory stability. -/
theorem system_safety {sys sys' : System} (h : SystemReach sys sys')
    (hc : LinkConsistent sys) {a u : Id} (hb : sys.directory.byAddress a = some u) :
    LinkConsistent sys' ∧ AtMostOneLinkedKAsset sys' ∧
      sys'.directory.byAddress a = some u := by
  exact ⟨SystemReach.link_consistent h hc,
         SystemReach.at_most_one_linked_kasset h hc,
         SystemReach.directory_stable h hb⟩

end RGen
