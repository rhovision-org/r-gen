import RGen.Basic

/-!
# Object capabilities: grants, bundles, and delegation

This module is a small abstract model of the capability discipline used by the core:

* every holder of a capability has a grant path from a creator (`no_holder_without_grant`);
* a published bundle exposes only its listed arms, not the private helpers
  (`bundle_excludes_private`);
* an `Apply` capability changes only the case it is bound to (`apply_case_bound`);
* a forwarded proof can be taken by another holder, but the consumer check still binds the
  subject, credential and height, so possession cannot forge an acceptance
  (`forward_burns_but_cannot_forge`);
* a decision that uses only a public reference and no held capability cannot commit
  (`public_reference_not_authority`);
* a nested child must be issued by the claim factory (`anchored_nest_requires_issued_child`);
* `Issuer.authorize` accepts only the issuer subject (`issuer_authorize_requires_issuer`);
* an approval is a durable state transition, not a credential capability
  (`approval_survives_revocation`).

The boundary is explicit: names are abstract `Nat` identifiers. The module does not prove
Rholang name unforgeability; that is an assumption recorded in `spec/proofs/rigor.yaml`.
It also does not model the registry's trust decision; `anchored_nest_requires_issued_child`
states the precondition the deployed anchor check enforces.
-/

namespace RGen

namespace Cap

inductive CapKind where
  | contract
  | proof
  | apply
  | issuer
  | deployer
  | registry
  deriving DecidableEq, Repr

structure Cap where
  kind : CapKind
  id : Nat
  deriving DecidableEq, Repr

/-- A grant edge for capability `cap` from `from_` to `to`. -/
structure Grant where
  cap : Nat
  from_ : Nat
  to_ : Nat
  deriving DecidableEq, Repr

/-- Reachability in a grant graph for one capability. -/
inductive GrantReach (grants : List Grant) (cap : Nat) : Nat → Nat → Prop
  | refl (a : Nat) : GrantReach grants cap a a
  | step {a b c : Nat}
      (h : ({ cap := cap, from_ := a, to_ := b } : Grant) ∈ grants)
      (r : GrantReach grants cap b c) : GrantReach grants cap a c

structure World where
  caps : List Cap
  grants : List Grant
  holders : List (Nat × Nat)
  created : List (Nat × Nat)

def Holds (w : World) (cap holder : Nat) : Prop :=
  (cap, holder) ∈ w.holders

def CreatedBy (w : World) (cap creator : Nat) : Prop :=
  (cap, creator) ∈ w.created

/-- Every holder was either the creator or received the capability through a grant path. -/
def WellFormed (w : World) : Prop :=
  ∀ cap holder, Holds w cap holder →
    ∃ creator, CreatedBy w cap creator ∧ GrantReach w.grants cap creator holder

theorem no_holder_without_grant (w : World) (hw : WellFormed w)
    {cap holder : Nat} (h : Holds w cap holder) :
    ∃ creator, CreatedBy w cap creator ∧ GrantReach w.grants cap creator holder :=
  hw cap holder h

structure Bundle where
  exposed : List String
  privateNames : List String
  deriving DecidableEq, Repr

def Disjoint (a b : List String) : Prop :=
  ∀ x, x ∈ a → x ∉ b

def Callable (b : Bundle) (name : String) : Prop :=
  name ∈ b.exposed

theorem bundle_excludes_private (b : Bundle) (h : Disjoint b.exposed b.privateNames)
    {name : String} (hp : name ∈ b.privateNames) : ¬ Callable b name := by
  intro hc
  exact h name hc hp

structure ApplyCap where
  caseId : Nat
  deriving DecidableEq, Repr

/-- An Apply capability changes state only for its bound case id. -/
def applyDecision (cap : ApplyCap) (caseId : Nat) (state : Nat) : Option Nat :=
  if caseId = cap.caseId then some (state + 1) else none

theorem apply_case_bound (cap : ApplyCap) {caseId : Nat}
    (h : caseId ≠ cap.caseId) : applyDecision cap caseId 0 = none := by
  simp [applyDecision, h]

structure ProofData where
  subject : Nat
  credential : Nat
  atHeight : Nat
  deriving DecidableEq, Repr

structure ForwardProof where
  data : ProofData
  used : Bool
  deriving DecidableEq, Repr

/-- Taking a proof is not caller-bound; a forwarded proof can be consumed by any holder. -/
def takeForward (p : ForwardProof) : Option (ProofData × ForwardProof) :=
  if p.used then none else some (p.data, { p with used := true })

/-- The consumer check binds the proof data to the caller and the current height. -/
def accepts (data : ProofData) (subject credential height : Nat) : Bool :=
  if data.subject = subject ∧ data.credential = credential ∧
      data.atHeight = height then true else false

theorem forward_burns_but_cannot_forge (p : ForwardProof) (subject : Nat)
    (h : p.data.subject ≠ subject) :
    accepts p.data subject p.data.credential p.data.atHeight = false := by
  simp [accepts, h]

structure RefDecision where
  reference : Nat
  usesHeldCap : Bool
  deriving DecidableEq, Repr

/-- A decision that does not use a held capability cannot commit. -/
def commit (d : RefDecision) (held : Bool) (state : Nat) : Option Nat :=
  if d.usesHeldCap then (if held then some (state + 1) else none) else none

theorem public_reference_not_authority (d : RefDecision)
    (h : d.usesHeldCap = false) (held : Bool) (state : Nat) :
    commit d held state = none := by
  simp [commit, h]

structure Issued where
  children : List Nat
  deriving DecidableEq, Repr

/-- A nested child must be one the claim factory issued. -/
def anchoredNest (issued : Issued) (child : Nat) : Option Nat :=
  if child ∈ issued.children then some child else none

theorem anchored_nest_requires_issued_child (issued : Issued) {child : Nat}
    (h : child ∉ issued.children) : anchoredNest issued child = none := by
  simp [anchoredNest, h]

structure IssuerState where
  subject : Nat
  deriving DecidableEq, Repr

def authorize (s : IssuerState) (caller : Nat) : Bool :=
  if caller = s.subject then true else false

theorem issuer_authorize_requires_issuer (s : IssuerState) {caller : Nat}
    (h : caller ≠ s.subject) : authorize s caller = false := by
  simp [authorize, h]

structure Approval where
  status : String
  deriving DecidableEq, Repr

structure SubjectState where
  approval : Approval
  credentialStatus : String
  deriving DecidableEq, Repr

def revokeCredential (s : SubjectState) : SubjectState :=
  { s with credentialStatus := "revoked" }

theorem approval_survives_revocation (s : SubjectState) :
    (revokeCredential s).approval = s.approval := rfl

end Cap

end RGen
