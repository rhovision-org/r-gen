import RGen.Basic

/-!
# Issuer

The genesis issuer is immutable. There is no transition construct at all:
`IssuerStep` has no constructors. Credential issuance is therefore a monotone
read of the issuer scope, and there is no issuer-revocation arm to race with
issuance. Rotation or revocation is a governance extension, not core.
-/

namespace RGen

structure Issuer where
  scope : IssuerScope
  deriving DecidableEq, Repr

namespace Issuer

def authorize (i : Issuer) (r : Requirement) : Bool := issuerCovers i.scope r

/-- No issuer transition exists. -/
inductive IssuerStep : Issuer → Issuer → Prop

theorem issuer_step_empty {i j : Issuer} : ¬ IssuerStep i j := by
  intro h
  cases h

theorem issuer_immutable {i j : Issuer} (h : IssuerStep i j) : False :=
  issuer_step_empty h

theorem authorize_stable {i j : Issuer} (h : IssuerStep i j) (r : Requirement) :
    i.authorize r = j.authorize r :=
  False.elim (issuer_step_empty h)

/-- Authorization depends only on the scope. -/
theorem authorize_congr {i j : Issuer} (h : i.scope = j.scope) (r : Requirement) :
    i.authorize r = j.authorize r := by
  simp [authorize, h]

end Issuer

end RGen
