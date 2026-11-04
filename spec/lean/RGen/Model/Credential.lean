import RGen.Basic
import RGen.Linear.Protocol
import RGen.Model.Types
import RGen.Model.Proof
import RGen.Model.Issuer

/-!
# Credential

A credential is a subject, issuer, scope, issue window, status, and attestation
list. `prove` is the linearization point for every credential-gated arm: it
requires the caller to be the subject, the credential to be active at the stated
height, and the credential scope plus issuer scope to cover the requirement. It
produces a one-shot proof and leaves the credential cell unchanged; the caller
re-posts the cell.

Revocation is non-retroactive. The proof is a snapshot (`ProofData`) taken from
the pre-revocation state, so a later revoke cannot change a proof already taken.
The one-shot flag is observability and testability; the capability is private
and unforgeable, so it is the security boundary.
-/

namespace RGen

inductive CredStatus where
  | active
  | revoked
  deriving DecidableEq, Repr

structure CredentialState where
  subject : Id
  issuer : Id
  scope : Scope
  issuedAt : Height
  expiresAt : Height
  status : CredStatus
  attestations : List Id
  deriving DecidableEq, Repr

namespace CredentialState

def isActive (c : CredentialState) : Bool := decide (c.status = CredStatus.active)

/-- Active at a height: not revoked and not past expiry. The deployed arm has no
issuedAt lower bound, so the model does not add one. -/
def activeAt (c : CredentialState) (h : Height) : Bool :=
  c.isActive && decide (h ≤ c.expiresAt)

/-- The credential and its issuer cover the requirement. -/
def attests (c : CredentialState) (issuerScope : IssuerScope) (r : Requirement) : Bool :=
  scopeMatches c.scope r && issuerCovers issuerScope r

/-- The proof guard. -/
def proveAllowed (c : CredentialState) (issuerScope : IssuerScope) (caller : Id)
    (r : Requirement) (h : Height) : Bool :=
  decide (caller = c.subject) && activeAt c h && attests c issuerScope r

theorem proveAllowed_iff {c : CredentialState} {issuerScope : IssuerScope}
    {caller : Id} {r : Requirement} {h : Height} :
    proveAllowed c issuerScope caller r h = true ↔
      caller = c.subject ∧ activeAt c h = true ∧ attests c issuerScope r = true := by
  simp [proveAllowed, Bool.and_eq_true, decide_eq_true_eq, and_assoc]

theorem activeAt_status {c : CredentialState} {h : Height}
    (hactive : activeAt c h = true) : c.status = CredStatus.active := by
  unfold activeAt isActive at hactive
  rw [Bool.and_eq_true] at hactive
  exact of_decide_eq_true hactive.1

/-- Issue a one-shot credential proof. -/
def prove (c : CredentialState) (proofUri credentialUri : Id)
    (issuerScope : IssuerScope) (caller : Id) (r : Requirement) (h : Height) :
    Option (ProofState ProofData) :=
  if proveAllowed c issuerScope caller r h then
    some ⟨{ uri := proofUri, subject := c.subject, requirement := r, atHeight := h,
            level := c.scope.level, credentialUri := credentialUri }, false⟩
  else none

/-- Only the subject or the issuer may revoke. -/
def revoke (c : CredentialState) (caller : Id) : Option CredentialState :=
  if c.status = CredStatus.active ∧ (caller = c.subject ∨ caller = c.issuer) then
    some { c with status := CredStatus.revoked }
  else none

/-- Only the subject or the issuer may renew, and only forward in time. -/
def renew (c : CredentialState) (caller : Id) (newExpiry : Height) :
    Option CredentialState :=
  if c.status = CredStatus.active ∧ caller = c.issuer ∧ c.issuedAt ≤ newExpiry then
    some { c with expiresAt := newExpiry }
  else none

/-- A third party may attest once: not the subject, and not already attested. -/
def attest (c : CredentialState) (caller : Id) : Option CredentialState :=
  if caller ≠ c.subject ∧ caller ∉ c.attestations then
    some { c with attestations := caller :: c.attestations }
  else none

/-! ### Proof guards -/

theorem prove_requires_subject {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {h : Height}
    {p : ProofState ProofData}
    (hp : c.prove proofUri credentialUri issuerScope caller r h = some p) :
    caller = c.subject := by
  unfold prove at hp
  split at hp
  · exact (proveAllowed_iff.mp ‹_›).1
  · simp at hp

theorem prove_requires_active {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {h : Height}
    {p : ProofState ProofData}
    (hp : c.prove proofUri credentialUri issuerScope caller r h = some p) :
    activeAt c h = true := by
  unfold prove at hp
  split at hp
  · exact (proveAllowed_iff.mp ‹_›).2.1
  · simp at hp

theorem prove_requires_scope {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {h : Height}
    {p : ProofState ProofData}
    (hp : c.prove proofUri credentialUri issuerScope caller r h = some p) :
    attests c issuerScope r = true := by
  unfold prove at hp
  split at hp
  · exact (proveAllowed_iff.mp ‹_›).2.2
  · simp at hp

/-- A non-subject caller cannot prove. -/
theorem prove_wrong_subject {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {hgt : Height}
    (h : caller ≠ c.subject) :
    c.prove proofUri credentialUri issuerScope caller r hgt = none := by
  unfold prove
  rw [if_neg]
  intro hg
  exact h (proveAllowed_iff.mp hg).1

/-- A proof taken from a credential is a snapshot of that pre-state. -/
theorem prove_snapshot {c : CredentialState} {issuerScope : IssuerScope}
    {proofUri credentialUri : Id} {caller : Id} {r : Requirement} {h : Height}
    {p : ProofState ProofData}
    (hp : c.prove proofUri credentialUri issuerScope caller r h = some p) :
    p.data.subject = c.subject ∧ p.data.requirement = r ∧ p.data.atHeight = h ∧
      p.data.credentialUri = credentialUri := by
  unfold prove at hp
  split at hp
  · simp at hp
    rcases hp with rfl
    exact ⟨rfl, rfl, rfl, rfl⟩
  · simp at hp

/-! ### Revocation and renewal -/

theorem revoke_requires_party {c c' : CredentialState} {caller : Id}
    (h : c.revoke caller = some c') : caller = c.subject ∨ caller = c.issuer := by
  unfold revoke at h
  split at h
  · rename_i hg
    exact hg.2
  · simp at h

theorem revoke_sets_revoked {c c' : CredentialState} {caller : Id}
    (h : c.revoke caller = some c') : c'.status = CredStatus.revoked := by
  unfold revoke at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-- A revoked credential cannot prove. -/
theorem prove_after_revoke {c c' : CredentialState} {caller caller' : Id}
    {issuerScope : IssuerScope} {proofUri credentialUri : Id}
    {r : Requirement} {h : Height}
    (hr : c.revoke caller = some c') :
    c'.prove proofUri credentialUri issuerScope caller' r h = none := by
  have hstatus := revoke_sets_revoked hr
  unfold prove
  rw [if_neg]
  intro hg
  have hactive := (proveAllowed_iff.mp hg).2.1
  have hst := activeAt_status hactive
  rw [hstatus] at hst
  exact absurd hst (by decide)

theorem renew_after_revoke {c c' : CredentialState} {caller caller' : Id} {expiry : Height}
    (hr : c.revoke caller = some c') : c'.renew caller' expiry = none := by
  have hstatus := revoke_sets_revoked hr
  unfold renew
  rw [if_neg]
  intro hg
  have : CredStatus.revoked = CredStatus.active := hstatus.symm.trans hg.1
  exact absurd this (by decide)

theorem renew_requires_active {c c' : CredentialState} {caller : Id} {newExpiry : Height}
    (h : c.renew caller newExpiry = some c') : c.status = CredStatus.active := by
  unfold renew at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem renew_requires_issuer {c c' : CredentialState} {caller : Id} {newExpiry : Height}
    (h : c.renew caller newExpiry = some c') : caller = c.issuer := by
  unfold renew at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem renew_identity {c c' : CredentialState} {caller : Id} {newExpiry : Height}
    (h : c.renew caller newExpiry = some c') :
    c'.subject = c.subject ∧ c'.issuer = c.issuer ∧ c'.scope = c.scope := by
  unfold renew at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact ⟨rfl, rfl, rfl⟩
  · simp at h

/-- Renewal extends the window and never shortens it. -/
theorem renew_extends {c c' : CredentialState} {caller : Id} {newExpiry : Height}
    (h : c.renew caller newExpiry = some c') : c.issuedAt ≤ c'.expiresAt := by
  unfold renew at h
  split at h
  · rename_i hg
    simp only [Option.some.injEq] at h
    rcases h with rfl
    exact hg.2.2
  · simp at h

/-! ### Attestation -/

theorem attest_twice {c c' : CredentialState} {caller : Id}
    (h : c.attest caller = some c') : c'.attest caller = none := by
  unfold attest at h
  split at h
  · rename_i hg
    simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [attest, List.mem_cons]
  · simp at h

/-- Attestation cannot come from the subject. -/
theorem attest_not_subject {c c' : CredentialState} {caller : Id}
    (h : c.attest caller = some c') : caller ≠ c.subject := by
  unfold attest at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem revoke_identity {c c' : CredentialState} {caller : Id}
    (h : c.revoke caller = some c') :
    c'.subject = c.subject ∧ c'.issuer = c.issuer ∧ c'.scope = c.scope := by
  unfold revoke at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact ⟨rfl, rfl, rfl⟩
  · simp at h

theorem attest_identity {c c' : CredentialState} {caller : Id}
    (h : c.attest caller = some c') :
    c'.subject = c.subject ∧ c'.issuer = c.issuer ∧ c'.scope = c.scope := by
  unfold attest at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    exact ⟨rfl, rfl, rfl⟩
  · simp at h

/-! ### Identity is invariant under every credential step -/

inductive CredEvent where
  | revoke (caller : Id)
  | renew (caller : Id) (newExpiry : Height)
  | attest (caller : Id)
  deriving DecidableEq, Repr

def applyEvent (e : CredEvent) (c : CredentialState) : Option CredentialState :=
  match e with
  | .revoke caller => c.revoke caller
  | .renew caller newExpiry => c.renew caller newExpiry
  | .attest caller => c.attest caller

def CredStep (c c' : CredentialState) : Prop := ∃ e, applyEvent e c = some c'

theorem credStep_preserves_identity {c c' : CredentialState} (h : CredStep c c') :
    c'.subject = c.subject ∧ c'.issuer = c.issuer ∧ c'.scope = c.scope := by
  rcases h with ⟨e, he⟩
  cases e with
  | revoke caller => exact revoke_identity he
  | renew caller newExpiry => exact renew_identity he
  | attest caller => exact attest_identity he

/-- Subject, issuer, and scope are stable along every reachable credential history. -/
theorem credReach_preserves_identity {c c' : CredentialState}
    (h : Reach CredStep c c') :
    c'.subject = c.subject ∧ c'.issuer = c.issuer ∧ c'.scope = c.scope :=
  reach_invariant
    (P := fun x => x.subject = c.subject ∧ x.issuer = c.issuer ∧ x.scope = c.scope)
    (fun _ _ hab hp =>
      let hb := credStep_preserves_identity hab
      ⟨hb.1.trans hp.1, hb.2.1.trans hp.2.1, hb.2.2.trans hp.2.2⟩)
    c c' h ⟨rfl, rfl, rfl⟩

end CredentialState

end RGen
