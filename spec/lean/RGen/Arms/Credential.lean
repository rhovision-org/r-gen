import RGen.Arms.Basic
import RGen.Model.Credential

/-!
# Credential arm pairs

`prove` consumes the credential cell and re-posts it unchanged; `revoke` consumes the same
cell. Revoke-then-prove is refused; prove-then-revoke is allowed and the proof is a
snapshot. `renew` and `attest` consume the same cell; renew is issuer-only and active-only.
-/

namespace RGen

structure ProveArgs where
  proofUri : Id
  credentialUri : Id
  issuerScope : IssuerScope
  caller : Id
  requirement : Requirement
  height : Height

def credentialProve (s : CredentialState) (a : ProveArgs) : Option CredentialState :=
  match s.prove a.proofUri a.credentialUri a.issuerScope a.caller a.requirement a.height with
  | none => none
  | some _ => some s

def credentialRevoke (s : CredentialState) (caller : Id) : Option CredentialState :=
  s.revoke caller

def credentialRenew (s : CredentialState) (caller : Id) (expiry : Height) :
    Option CredentialState :=
  s.renew caller expiry

def credentialAttest (s : CredentialState) (caller : Id) : Option CredentialState :=
  s.attest caller

theorem credential_prove_revoke_never_after {a : ProveArgs} {caller : Id} :
    NeverAfter (fun s => credentialRevoke s caller) (fun s => credentialProve s a) := by
  intro s s1 hrev
  simp only [credentialRevoke] at hrev
  dsimp only [credentialProve]
  rw [CredentialState.prove_after_revoke hrev]

theorem credential_revoke_renew_never_after {caller caller' : Id} {expiry : Height} :
    NeverAfter (fun s => credentialRevoke s caller) (fun s => credentialRenew s caller' expiry) := by
  intro s s1 hrev
  simp only [credentialRevoke] at hrev
  dsimp only [credentialRenew]
  rw [CredentialState.renew_after_revoke hrev]

theorem credential_attest_same_never_after {caller : Id} :
    NeverAfter (fun s => credentialAttest s caller) (fun s => credentialAttest s caller) := by
  intro s s1 h
  exact CredentialState.attest_twice h

/-- Prove-then-revoke is the allowed order; the proof is a snapshot of the pre-revoke
credential. -/
theorem credential_prove_revoke_snapshot {s : CredentialState} {a : ProveArgs}
    {p : ProofState ProofData}
    (hp : s.prove a.proofUri a.credentialUri a.issuerScope a.caller a.requirement a.height
      = some p) :
    p.data.subject = s.subject ∧ p.data.requirement = a.requirement ∧
      p.data.atHeight = a.height ∧ p.data.credentialUri = a.credentialUri :=
  CredentialState.prove_snapshot hp

end RGen
