import RGen.Basic
import RGen.Model.Types
import RGen.Model.Proof
import RGen.Model.ValueProposition

/-!
# K-Asset

A K-Asset is created by exactly one validated claim. It is approved by a
non-claimant holding both a credential proof and a value-proposition proof, then
can be disputed and decided, or nested into a parent by the parent's claimant.

`nest` takes child *proofs*, not child states: the proof is authoritative and the
pre-pass in the deployed contract is only a hint. The model requires distinct
children, no self-reference, and a strictly rising `(approvedAt, id)` order.
Strict order makes the nesting graph acyclic, because a cycle would imply
`lexLt x x`.

`proveApproved` is a one-shot capability carrying the approval snapshot; it is
the input to `nest`.
-/

namespace RGen

instance lexLt_decidable (a b : Height × Id) : Decidable (lexLt a b) := by
  unfold lexLt
  infer_instance

inductive KAssetStatus where
  | validated
  | conditional
  | approved
  | rejected
  | disputed
  | upheld
  | revoked
  | partiallyRevoked
  deriving DecidableEq, Repr

structure ApprovedProofData where
  id : Id
  uri : Id
  approvedAt : Height
  discipline : String
  jurisdiction : String
  approver : Id
  deriving DecidableEq, Repr

structure KAssetState where
  id : Id
  uri : Id
  claimant : Id
  claimRef : Id
  status : KAssetStatus
  approvedAt : Height
  approver : Option Id
  validator : Option Id
  children : List Id
  discipline : String
  jurisdiction : String
  disputeCase : Option Id
  rejectedAt : Option Height
  deriving DecidableEq, Repr

namespace KAssetState

def approve (s : KAssetState) (approver : Id) (credProof vpProof : ProofData)
    (atHeight : Height) : Option KAssetState :=
  if (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
      approver ≠ s.claimant ∧ credProof.subject = approver ∧
      credProof.requirement.ctype = "Approver" ∧
      vpProof.subject = approver ∧
      vpProof.requirement.ctype = "ValueProposition" ∧ s.validator ≠ some approver then
    some { s with status := KAssetStatus.approved, approver := some approver, approvedAt := atHeight }
  else none

def reject (s : KAssetState) (approver : Id) (credProof : ProofData)
    (atHeight : Height) : Option KAssetState :=
  if (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
      approver ≠ s.claimant ∧ credProof.subject = approver ∧
      s.validator ≠ some approver then
    some { s with status := KAssetStatus.rejected, approver := some approver, rejectedAt := some atHeight }
  else none

/-- A one-shot approval proof, the authority for nesting this asset. -/
def proveApproved (s : KAssetState) (proofUri : Id) :
    Option (ProofState ApprovedProofData) :=
  match s.approver with
  | none => none
  | some a =>
      if s.status = KAssetStatus.approved then
        let d : ApprovedProofData := { id := s.id, uri := proofUri, approvedAt := s.approvedAt, discipline := s.discipline, jurisdiction := s.jurisdiction, approver := a }
        some ⟨d, false⟩
      else none

def openDispute (s : KAssetState) (caller : Id) (caseId : Id) : Option KAssetState :=
  if s.status = KAssetStatus.approved ∧ (caller = s.claimant ∨ s.validator = some caller) ∧
      s.disputeCase = none then
    some { s with status := KAssetStatus.disputed, disputeCase := some caseId }
  else none

def applyDecision (s : KAssetState) (caseId : Id) (d : VPDecision) : Option KAssetState :=
  if s.status = KAssetStatus.disputed ∧ s.disputeCase = some caseId then
    some { s with status :=
      match d with
      | VPDecision.uphold => KAssetStatus.upheld
      | VPDecision.revoke => KAssetStatus.revoked
      | VPDecision.partially => KAssetStatus.partiallyRevoked }
  else none

/-! ### Nesting order -/

def childKey (c : ApprovedProofData) : Height × Id := (c.approvedAt, c.id)

def strictRising : List (Height × Id) → Bool
  | [] => true
  | [_] => true
  | a :: b :: rest => decide (a.1 < b.1) && strictRising (b :: rest)

def nodupIds : List Id → Bool
  | [] => true
  | x :: xs => !(decide (x ∈ xs)) && nodupIds xs

def idsNotIn (existing : List Id) (children : List ApprovedProofData) : Bool :=
  children.all (fun c => decide (c.id ∉ existing))

def allBelow (parentAt : Height) (children : List ApprovedProofData) : Bool :=
  children.all (fun c => decide (c.approvedAt < parentAt))

def allScope (discipline jurisdiction : String) (children : List ApprovedProofData) : Bool :=
  children.all (fun c => decide (c.discipline = discipline ∧ c.jurisdiction = jurisdiction))

def nest (s : KAssetState) (caller : Id) (children : List ApprovedProofData) :
    Option KAssetState :=
  if caller = s.claimant ∧ s.status = KAssetStatus.approved ∧
      nodupIds (children.map (fun c => c.id)) ∧
      decide (s.id ∉ children.map (fun c => c.id)) ∧
      strictRising (children.map childKey) ∧
      idsNotIn s.children children ∧
      allBelow s.approvedAt children ∧
      allScope s.discipline s.jurisdiction children then
    some { s with children := s.children ++ children.map (fun c => c.id) }
  else none

/-! ### Approval guards -/

theorem approve_only_from_validated_or_conditional {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional := by
  unfold approve at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem approve_requires_non_claimant {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    approver ≠ s.claimant := by
  unfold approve at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem approve_requires_credential_proof {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    credProof.subject = approver := by
  unfold approve at h
  split at h
  · rename_i hg
    exact hg.2.2.1
  · simp at h

theorem approve_requires_vp_proof {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    vpProof.subject = approver ∧ vpProof.requirement.ctype = "ValueProposition" := by
  unfold approve at h
  split at h
  · rename_i hg
    exact ⟨hg.2.2.2.2.1, hg.2.2.2.2.2.1⟩
  · simp at h

theorem approve_requires_credential_type {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    credProof.requirement.ctype = "Approver" := by
  unfold approve at h
  split at h
  · rename_i hg
    exact hg.2.2.2.1
  · simp at h

theorem approve_requires_non_validator {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s.validator ≠ some approver := by
  unfold approve at h
  split at h
  · rename_i hg
    exact hg.2.2.2.2.2.2
  · simp at h

theorem approve_sets_status {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s'.status = KAssetStatus.approved := by
  unfold approve at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem approve_sets_approvedAt {s s' : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s'.approvedAt = atHeight := by
  unfold approve at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem approve_once {s s' : KAssetState} {approver : Id} {credProof vpProof : ProofData}
    {atHeight : Height} {approver' : Id} {credProof' vpProof' : ProofData} {atHeight' : Height}
    (h : s.approve approver credProof vpProof atHeight = some s') :
    s'.approve approver' credProof' vpProof' atHeight' = none := by
  unfold approve at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [approve]
  · simp at h

/-- The claimant cannot approve their own K-Asset. -/
theorem approve_by_claimant_refused {s : KAssetState} {approver : Id}
    {credProof vpProof : ProofData} {atHeight : Height}
    (h : approver = s.claimant) :
    s.approve approver credProof vpProof atHeight = none := by
  unfold approve
  rw [if_neg]
  intro hg
  exact hg.2.1 h

/-! ### Rejection guards -/

theorem reject_only_from_validated_or_conditional {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional := by
  unfold reject at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem reject_requires_non_claimant {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    approver ≠ s.claimant := by
  unfold reject at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem reject_requires_credential_proof {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    credProof.subject = approver := by
  unfold reject at h
  split at h
  · rename_i hg
    exact hg.2.2.1
  · simp at h

theorem reject_requires_non_validator {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    s.validator ≠ some approver := by
  unfold reject at h
  split at h
  · rename_i hg
    exact hg.2.2.2
  · simp at h

theorem reject_sets_status {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    s'.status = KAssetStatus.rejected := by
  unfold reject at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem reject_preserves_approvedAt {s s' : KAssetState} {approver : Id}
    {credProof : ProofData} {atHeight : Height}
    (h : s.reject approver credProof atHeight = some s') :
    s'.approvedAt = s.approvedAt := by
  unfold reject at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem reject_once {s s' : KAssetState} {approver : Id} {credProof : ProofData}
    {atHeight : Height} {approver' : Id} {credProof' : ProofData} {atHeight' : Height}
    (h : s.reject approver credProof atHeight = some s') :
    s'.reject approver' credProof' atHeight' = none := by
  unfold reject at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [reject]
  · simp at h

/-! ### The approval proof -/

theorem proveApproved_requires_approved {s : KAssetState} {uri : Id}
    {p : ProofState ApprovedProofData}
    (h : s.proveApproved uri = some p) :
    s.status = KAssetStatus.approved ∧ ∃ a, s.approver = some a := by
  cases ha : s.approver with
  | none => simp [proveApproved, ha] at h
  | some a =>
      by_cases hs : s.status = KAssetStatus.approved
      · exact ⟨hs, a, rfl⟩
      · simp [proveApproved, ha, hs] at h

theorem proveApproved_snapshot {s : KAssetState} {uri : Id}
    {p : ProofState ApprovedProofData}
    (h : s.proveApproved uri = some p) :
    p.data.id = s.id ∧ p.data.uri = uri ∧ p.data.approvedAt = s.approvedAt ∧
      p.data.discipline = s.discipline ∧ p.data.jurisdiction = s.jurisdiction := by
  cases ha : s.approver with
  | none => simp [proveApproved, ha] at h
  | some a =>
      by_cases hs : s.status = KAssetStatus.approved
      · simp [proveApproved, ha, hs] at h
        cases h
        exact ⟨rfl, rfl, rfl, rfl, rfl⟩
      · simp [proveApproved, ha, hs] at h

/-! ### Nesting guards -/

theorem nest_requires_claimant {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData}
    (h : s.nest caller children = some s') : caller = s.claimant := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem nest_requires_status {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    s.status = KAssetStatus.approved := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.1
  · simp at h

theorem nest_requires_distinct_children {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    nodupIds (children.map (fun c => c.id)) = true := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.2.1
  · simp at h

theorem nest_requires_no_self {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    s.id ∉ children.map (fun c => c.id) := by
  unfold nest at h
  split at h
  · rename_i hg
    exact of_decide_eq_true hg.2.2.2.1
  · simp at h

theorem nest_requires_order {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    strictRising (children.map childKey) = true := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.2.2.2.1
  · simp at h

theorem nest_requires_no_existing {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    idsNotIn s.children children = true := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.2.2.2.2.1
  · simp at h

theorem nest_requires_below_parent {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    allBelow s.approvedAt children = true := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.2.2.2.2.2.1
  · simp at h

theorem nest_requires_scope {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    allScope s.discipline s.jurisdiction children = true := by
  unfold nest at h
  split at h
  · rename_i hg
    exact hg.2.2.2.2.2.2.2
  · simp at h

theorem nest_child_below_parent {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s')
    {c : ApprovedProofData} (hc : c ∈ children) : c.approvedAt < s.approvedAt :=
  of_decide_eq_true (List.all_eq_true.mp (nest_requires_below_parent h) c hc)

theorem nest_child_scope {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s')
    {c : ApprovedProofData} (hc : c ∈ children) :
    c.discipline = s.discipline ∧ c.jurisdiction = s.jurisdiction :=
  of_decide_eq_true (List.all_eq_true.mp (nest_requires_scope h) c hc)

theorem nest_child_not_existing {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s')
    {c : ApprovedProofData} (hc : c ∈ children) : c.id ∉ s.children :=
  of_decide_eq_true (List.all_eq_true.mp (nest_requires_no_existing h) c hc)

/-- Children must arrive in strictly rising order. -/
theorem nest_refused_unsorted {s : KAssetState} {caller : Id}
    {children : List ApprovedProofData}
    (h : strictRising (children.map childKey) = false) :
    s.nest caller children = none := by
  unfold nest
  rw [if_neg]
  intro hg
  have htrue : strictRising (children.map childKey) = true := hg.2.2.2.2.1
  rw [h] at htrue
  exact Bool.noConfusion htrue

/-- Adjacent children are strictly ordered. -/
theorem strictRising_head {a b : Height × Id} {rest : List (Height × Id)}
    (h : strictRising (a :: b :: rest) = true) : a.1 < b.1 := by
  unfold strictRising at h
  rw [Bool.and_eq_true] at h
  exact of_decide_eq_true h.1

/-- Strict order is transitive through any number of proof steps. -/
theorem key_strict_trans {a b c : ApprovedProofData}
    (hab : lexLt (childKey a) (childKey b)) (hbc : lexLt (childKey b) (childKey c)) :
    lexLt (childKey a) (childKey c) :=
  lexLt_trans hab hbc

/-- The nesting order has no cycle: every step strictly increases the key. -/
def NestStep (a b : ApprovedProofData) : Prop := lexLt (childKey a) (childKey b)

theorem nestTransGen_strict {a b : ApprovedProofData}
    (h : Relation.TransGen NestStep a b) : lexLt (childKey a) (childKey b) := by
  induction h with
  | single hab => exact hab
  | tail _ hbc ih => exact lexLt_trans ih hbc

theorem nest_acyclic {a : ApprovedProofData} (h : Relation.TransGen NestStep a a) : False :=
  lexLt_irrefl (childKey a) (nestTransGen_strict h)

/-! ### Dispute and decision -/

theorem openDispute_requires_approved {s s' : KAssetState} {caller caseId : Id}
    (h : s.openDispute caller caseId = some s') : s.status = KAssetStatus.approved := by
  unfold openDispute at h
  split at h
  · rename_i hg
    exact hg.1
  · simp at h

theorem openDispute_sets_status {s s' : KAssetState} {caller caseId : Id}
    (h : s.openDispute caller caseId = some s') : s'.status = KAssetStatus.disputed := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem idsNotIn_append_self (existing : List Id) :
    ∀ children : List ApprovedProofData, children ≠ [] →
      idsNotIn (existing ++ children.map (fun c => c.id)) children = false
  | [], h => absurd rfl h
  | c :: cs, _ => by
      simp [idsNotIn, List.all]

theorem openDispute_once {s s' : KAssetState} {caller caseId caller' caseId' : Id}
    (h : s.openDispute caller caseId = some s') :
    s'.openDispute caller' caseId' = none := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    simp [openDispute]
  · simp at h

theorem decision_once {s s' : KAssetState} {caseId : Id} {d : VPDecision}
    {caseId' : Id} {d' : VPDecision}
    (h : s.applyDecision caseId d = some s') :
    s'.applyDecision caseId' d' = none := by
  unfold applyDecision at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    cases d <;> simp [applyDecision]
  · simp at h

/-! ### Approval height is stable -/

theorem openDispute_preserves_approvedAt {s s' : KAssetState} {caller caseId : Id}
    (h : s.openDispute caller caseId = some s') : s'.approvedAt = s.approvedAt := by
  unfold openDispute at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem applyDecision_preserves_approvedAt {s s' : KAssetState} {caseId : Id}
    {d : VPDecision} (h : s.applyDecision caseId d = some s') :
    s'.approvedAt = s.approvedAt := by
  unfold applyDecision at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

theorem nest_preserves_approvedAt {s s' : KAssetState} {caller : Id}
    {children : List ApprovedProofData} (h : s.nest caller children = some s') :
    s'.approvedAt = s.approvedAt := by
  unfold nest at h
  split at h
  · simp only [Option.some.injEq] at h
    rcases h with rfl
    rfl
  · simp at h

/-- Once approved, no admissible transition rewrites the approval height. -/
theorem approvedAt_stable {s s' : KAssetState} :
    (∀ (caller caseId : Id), s.openDispute caller caseId = some s' →
      s'.approvedAt = s.approvedAt) ∧
    (∀ (caseId : Id) (d : VPDecision), s.applyDecision caseId d = some s' →
      s'.approvedAt = s.approvedAt) ∧
    (∀ (caller : Id) (children : List ApprovedProofData), s.nest caller children = some s' →
      s'.approvedAt = s.approvedAt) :=
  ⟨fun _ _ h => openDispute_preserves_approvedAt h,
   fun _ _ h => applyDecision_preserves_approvedAt h,
   fun _ _ h => nest_preserves_approvedAt h⟩

end KAssetState

end RGen
