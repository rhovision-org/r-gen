import RGen.Arms.Instances

/-!
# Guard extraction for the core arms

Each guard below is the accept/refuse predicate transcribed from the model step. The
`*_guard_eq` theorem says the step returns `some` exactly when the guard is true. These
guards are the model side of the deployed guard table; they are not a refinement of the
Rholang. `tools/check_arm_guards.py` checks that the manifest names them.

The divergences recorded in `spec/proofs/rigor.yaml` are visible here: for example the
model `credentialRevokeGuard` has no active-status conjunct, and `kassetNestGuard` admits
validated and conditional parents.
-/

namespace RGen

def credentialRevokeGuard (s : CredentialState) (caller : Id) : Bool :=
  decide (caller = s.subject ∨ caller = s.issuer)

theorem credentialRevoke_guard_eq (s : CredentialState) (caller : Id) :
    (credentialRevoke s caller).isSome = credentialRevokeGuard s caller := by
  unfold credentialRevoke CredentialState.revoke credentialRevokeGuard
  by_cases h : caller = s.subject ∨ caller = s.issuer <;> simp [h]

def credentialRenewGuard (s : CredentialState) (p : Id × Height) : Bool :=
  decide (s.status = CredStatus.active ∧ p.1 = s.issuer ∧ s.issuedAt ≤ p.2)

theorem credentialRenew_guard_eq (s : CredentialState) (p : Id × Height) :
    (credentialRenew s p.1 p.2).isSome = credentialRenewGuard s p := by
  unfold credentialRenew CredentialState.renew credentialRenewGuard
  by_cases h : s.status = CredStatus.active ∧ p.1 = s.issuer ∧ s.issuedAt ≤ p.2 <;>
    simp [h]

def vpValidateGuard (s : VPState) (a : VPValidateArgs) : Bool :=
  decide (s.status = VPStatus.proposed ∧ a.validator ≠ s.proposer ∧
    a.proof.subject = a.validator ∧ a.proof.requirement = s.requirement)

theorem vpValidate_guard_eq (s : VPState) (a : VPValidateArgs) :
    (vpValidate s a).isSome = vpValidateGuard s a := by
  unfold vpValidate VPState.validate vpValidateGuard
  by_cases h : s.status = VPStatus.proposed ∧ a.validator ≠ s.proposer ∧
      a.proof.subject = a.validator ∧ a.proof.requirement = s.requirement <;>
    simp [h]

def claimValidateGuard (s : ClaimState) (a : ClaimValidateArgs) : Bool :=
  decide ((s.status = ClaimStatus.open ∧ s.deadline < a.atHeight) ∨
    (s.status = ClaimStatus.open ∧ a.validator ≠ s.claimant ∧
      a.atHeight ≤ s.deadline ∧ a.proof.subject = a.validator ∧
      a.proof.requirement = s.requirement ∧ s.kassetRef = none))

theorem claimValidate_guard_eq (s : ClaimState) (a : ClaimValidateArgs) :
    (claimValidate s a).isSome = claimValidateGuard s a := by
  unfold claimValidate ClaimState.validate claimValidateGuard
  by_cases h1 : s.status = ClaimStatus.open ∧ s.deadline < a.atHeight
  · simp [h1]
  · by_cases h2 : s.status = ClaimStatus.open ∧ a.validator ≠ s.claimant ∧
        a.atHeight ≤ s.deadline ∧ a.proof.subject = a.validator ∧
        a.proof.requirement = s.requirement ∧ s.kassetRef = none
    · have hnot : ¬ s.deadline < a.atHeight := Nat.not_lt.mpr h2.2.2.1
      simp [h1, h2, hnot]
    · simp [h1, h2]

def kassetApproveGuard (s : KAssetState) (a : KApproveArgs) : Bool :=
  decide ((s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
    a.approver ≠ s.claimant ∧ a.credProof.subject = a.approver ∧
    a.vpProof.subject = a.approver ∧
    a.vpProof.requirement.ctype = "ValueProposition" ∧ s.validator ≠ some a.approver)

theorem kassetApprove_guard_eq (s : KAssetState) (a : KApproveArgs) :
    (kassetApprove s a).isSome = kassetApproveGuard s a := by
  unfold kassetApprove KAssetState.approve kassetApproveGuard
  by_cases h : (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
      a.approver ≠ s.claimant ∧ a.credProof.subject = a.approver ∧
      a.vpProof.subject = a.approver ∧
      a.vpProof.requirement.ctype = "ValueProposition" ∧ s.validator ≠ some a.approver <;>
    simp [h]

def oracleDecideGuard (s : OracleState) (a : OracleDecideArgs) : Bool :=
  decide (s.status = OracleStatus.open ∧ a.adjudicator = s.adjudicator ∧
    a.proof.subject = a.adjudicator ∧ a.proof.credentialUri = s.adjudicatorCredential ∧
    a.proof.requirement = s.requirement)

theorem oracleDecide_guard_eq (s : OracleState) (a : OracleDecideArgs) :
    (oracleDecide s a).isSome = oracleDecideGuard s a := by
  unfold oracleDecide OracleState.decide oracleDecideGuard
  by_cases h : s.status = OracleStatus.open ∧ a.adjudicator = s.adjudicator ∧
      a.proof.subject = a.adjudicator ∧
      a.proof.credentialUri = s.adjudicatorCredential ∧
      a.proof.requirement = s.requirement <;> simp [h]

def provenanceAnchorGuard (s : ProvenanceState) (p : Id × (Id × Id)) : Bool :=
  decide (p.1 ∈ s.writers ∧ p.2.1 ≠ 0 ∧ p.2 ∉ s.anchors)

theorem provenanceAnchor_guard_eq (s : ProvenanceState) (p : Id × (Id × Id)) :
    (provenanceAnchor s p.1 p.2).isSome = provenanceAnchorGuard s p := by
  unfold provenanceAnchor ProvenanceState.addAnchor provenanceAnchorGuard
  by_cases h : p.1 ∈ s.writers ∧ p.2.1 ≠ 0 ∧ p.2 ∉ s.anchors <;> simp [h]

def identityUpdateGuard (s : ProfileState) (p : Id × IdentityPatch) : Bool :=
  decide (p.1 = s.subject)

theorem identityUpdate_guard_eq (s : ProfileState) (p : Id × IdentityPatch) :
    (identityUpdateArm.step s p).isSome = identityUpdateGuard s p := by
  unfold identityUpdateArm updateProfile identityUpdateGuard
  by_cases h : p.1 = s.subject <;> simp [h]

end RGen

namespace RGen

def identityCreateGuard (d : Directory) (p : Id × Id) : Bool :=
  decide (Directory.lookup d.entries p.1 = none)

theorem identityCreate_guard_eq (d : Directory) (p : Id × Id) :
    (identityCreateArm.step d p).isSome = identityCreateGuard d p := by
  change (d.create p.1 p.2).isSome = identityCreateGuard d p
  unfold Directory.create identityCreateGuard
  by_cases h : Directory.lookup d.entries p.1 = none <;> simp [h]

def vpCommentGuard (s : VPState) (p : Id × Height) : Bool :=
  decide (s.status = VPStatus.proposed ∧ p.2 ≤ s.deadlineHeight)

theorem vpComment_guard_eq (s : VPState) (p : Id × Height) :
    (vpCommentArm.step s p).isSome = vpCommentGuard s p := by
  change (s.comment p.1 p.2).isSome = vpCommentGuard s p
  unfold VPState.comment vpCommentGuard
  by_cases h : s.status = VPStatus.proposed ∧ p.2 ≤ s.deadlineHeight <;> simp [h]

def claimCommentGuard (s : ClaimState) (p : Id × Height) : Bool :=
  decide (s.status = ClaimStatus.open ∧ p.2 ≤ s.commentUntilHeight)

theorem claimComment_guard_eq (s : ClaimState) (p : Id × Height) :
    (claimCommentArm.step s p).isSome = claimCommentGuard s p := by
  change (claimComment s p.1 p.2).isSome = claimCommentGuard s p
  unfold claimComment ClaimState.comment claimCommentGuard
  by_cases h : s.status = ClaimStatus.open ∧ p.2 ≤ s.commentUntilHeight <;> simp [h]

def claimWithdrawGuard (s : ClaimState) (p : Id) : Bool :=
  decide (p = s.claimant ∧ s.status = ClaimStatus.open)

theorem claimWithdraw_guard_eq (s : ClaimState) (p : Id) :
    (claimWithdrawArm.step s p).isSome = claimWithdrawGuard s p := by
  change (claimWithdraw s p).isSome = claimWithdrawGuard s p
  unfold claimWithdraw ClaimState.withdraw claimWithdrawGuard
  by_cases h : p = s.claimant ∧ s.status = ClaimStatus.open <;> simp [h]

def claimExpireGuard (s : ClaimState) (h : Height) : Bool :=
  decide (s.status = ClaimStatus.open ∧ s.deadline < h)

theorem claimExpire_guard_eq (s : ClaimState) (h : Height) :
    (claimExpireArm.step s h).isSome = claimExpireGuard s h := by
  change (claimExpire s h).isSome = claimExpireGuard s h
  unfold claimExpire ClaimState.expire claimExpireGuard
  by_cases hh : s.status = ClaimStatus.open ∧ s.deadline < h <;> simp [hh]

def kassetRejectGuard (s : KAssetState) (a : KRejectArgs) : Bool :=
  decide ((s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
    a.approver ≠ s.claimant ∧ a.credProof.subject = a.approver ∧
    s.validator ≠ some a.approver)

theorem kassetReject_guard_eq (s : KAssetState) (a : KRejectArgs) :
    (kassetRejectArm.step s a).isSome = kassetRejectGuard s a := by
  change (kassetReject s a).isSome = kassetRejectGuard s a
  unfold kassetReject KAssetState.reject kassetRejectGuard
  by_cases h : (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional) ∧
      a.approver ≠ s.claimant ∧ a.credProof.subject = a.approver ∧
      s.validator ≠ some a.approver <;> simp [h]

def kassetOpenDisputeGuard (s : KAssetState) (p : Id × Id) : Bool :=
  decide (s.status = KAssetStatus.approved ∧
    (p.1 = s.claimant ∨ s.validator = some p.1) ∧ s.disputeCase = none)

theorem kassetOpenDispute_guard_eq (s : KAssetState) (p : Id × Id) :
    (kassetOpenDisputeArm.step s p).isSome = kassetOpenDisputeGuard s p := by
  change (kassetOpenDispute s p.1 p.2).isSome = kassetOpenDisputeGuard s p
  unfold kassetOpenDispute KAssetState.openDispute kassetOpenDisputeGuard
  by_cases h : s.status = KAssetStatus.approved ∧
      (p.1 = s.claimant ∨ s.validator = some p.1) ∧ s.disputeCase = none <;> simp [h]

def oracleExecuteGuard (s : OracleState) (p : Id) : Bool :=
  decide (s.status = OracleStatus.decided ∧ p = s.subject)

theorem oracleExecute_guard_eq (s : OracleState) (p : Id) :
    (oracleExecuteArm.step s p).isSome = oracleExecuteGuard s p := by
  change (oracleExecute s p).isSome = oracleExecuteGuard s p
  unfold oracleExecute OracleState.execute oracleExecuteGuard
  by_cases h : s.status = OracleStatus.decided ∧ p = s.subject <;> simp [h]

def oracleExpireGuard (s : OracleState) (h : Height) : Bool :=
  decide (s.status = OracleStatus.open ∧ s.deadline < h)

theorem oracleExpire_guard_eq (s : OracleState) (h : Height) :
    (oracleExpireArm.step s h).isSome = oracleExpireGuard s h := by
  change (oracleExpire s h).isSome = oracleExpireGuard s h
  unfold oracleExpire OracleState.expire oracleExpireGuard
  by_cases hh : s.status = OracleStatus.open ∧ s.deadline < h <;> simp [hh]

def oracleCloseGuard (s : OracleState) (_ : Unit) : Bool :=
  decide (s.status = OracleStatus.executed ∨ s.status = OracleStatus.expired)

theorem oracleClose_guard_eq (s : OracleState) (p : Unit) :
    (oracleCloseArm.step s p).isSome = oracleCloseGuard s p := by
  change (oracleClose s).isSome = oracleCloseGuard s p
  unfold oracleClose OracleState.close oracleCloseGuard
  by_cases h : s.status = OracleStatus.executed ∨ s.status = OracleStatus.expired <;> simp [h]

def oracleEvidenceGuard (s : OracleState) (ref : Id) : Bool :=
  decide (s.status = OracleStatus.open ∧ ref ∉ s.evidence)

theorem oracleEvidence_guard_eq (s : OracleState) (ref : Id) :
    (oracleEvidenceArm.step s ref).isSome = oracleEvidenceGuard s ref := by
  change (oracleEvidence s ref).isSome = oracleEvidenceGuard s ref
  unfold oracleEvidence OracleState.addEvidence oracleEvidenceGuard
  by_cases h : s.status = OracleStatus.open ∧ ref ∉ s.evidence <;> simp [h]

def provenanceCommentGuard (s : ProvenanceState) (p : Id × Id) : Bool :=
  decide (p.1 ∈ s.writers)

theorem provenanceComment_guard_eq (s : ProvenanceState) (p : Id × Id) :
    (provenanceCommentArm.step s p).isSome = provenanceCommentGuard s p := by
  change (provenanceComment s p.1 p.2).isSome = provenanceCommentGuard s p
  unfold provenanceComment ProvenanceState.addComment provenanceCommentGuard
  by_cases h : p.1 ∈ s.writers <;> simp [h]

def credentialAttestGuard (s : CredentialState) (caller : Id) : Bool :=
  decide (caller ≠ s.subject ∧ caller ∉ s.attestations)

theorem credentialAttest_guard_eq (s : CredentialState) (caller : Id) :
    (credentialAttestArm.step s caller).isSome = credentialAttestGuard s caller := by
  change (credentialAttest s caller).isSome = credentialAttestGuard s caller
  unfold credentialAttest CredentialState.attest credentialAttestGuard
  by_cases h : caller ≠ s.subject ∧ caller ∉ s.attestations <;> simp [h]

end RGen

namespace RGen

/-! ### Declared proof cells

These are the metadata obligations: an arm that validates, approves, decides, or nests declares
the proof cell it must consume. The theorems are deliberately small; the trace-ordering theorem
(`proofCells_consumed_before_commit`) remains open.
-/

theorem vpValidateArm_proof_cell : credentialProofCell ∈ vpValidateArm.proofCells := by decide
theorem claimValidateArm_proof_cell : credentialProofCell ∈ claimValidateArm.proofCells := by decide
theorem kassetApproveArm_proof_cells :
    credentialProofCell ∈ kassetApproveArm.proofCells ∧
      vpProofCell ∈ kassetApproveArm.proofCells := by decide
theorem kassetRejectArm_proof_cell : credentialProofCell ∈ kassetRejectArm.proofCells := by decide
theorem kassetNestArm_proof_cell : kassetProofCell ∈ kassetNestArm.proofCells := by decide
theorem oracleDecideArm_proof_cell : credentialProofCell ∈ oracleDecideArm.proofCells := by decide
theorem claimRejectArm_proof_cell : credentialProofCell ∈ claimRejectArm.proofCells := by decide

end RGen

namespace RGen

def vpWithdrawGuard (s : VPState) (p : Id) : Bool :=
  decide (p = s.proposer ∧ s.status = VPStatus.proposed)

theorem vpWithdraw_guard_eq (s : VPState) (p : Id) :
    (vpWithdrawArm.step s p).isSome = vpWithdrawGuard s p := by
  change (vpWithdraw s p).isSome = vpWithdrawGuard s p
  unfold vpWithdraw VPState.withdraw vpWithdrawGuard
  by_cases h : p = s.proposer ∧ s.status = VPStatus.proposed <;> simp [h]

def vpOpenDisputeGuard (s : VPState) (p : Id × Id) : Bool :=
  decide ((s.status = VPStatus.proposed ∨ s.status = VPStatus.validated) ∧
    (p.1 = s.proposer ∨ s.validatedBy = some p.1) ∧ s.disputeCase = none)

theorem vpOpenDispute_guard_eq (s : VPState) (p : Id × Id) :
    (vpOpenDisputeArm.step s p).isSome = vpOpenDisputeGuard s p := by
  change (vpOpenDispute s p.1 p.2).isSome = vpOpenDisputeGuard s p
  unfold vpOpenDispute VPState.openDispute vpOpenDisputeGuard
  by_cases h : (s.status = VPStatus.proposed ∨ s.status = VPStatus.validated) ∧
      (p.1 = s.proposer ∨ s.validatedBy = some p.1) ∧ s.disputeCase = none <;> simp [h]

def vpDecisionGuard (s : VPState) (p : Id × VPDecision) : Bool :=
  decide (s.status = VPStatus.disputed ∧ s.disputeCase = some p.1)

theorem vpDecision_guard_eq (s : VPState) (p : Id × VPDecision) :
    (vpDecisionArm.step s p).isSome = vpDecisionGuard s p := by
  change (vpDecision s p.1 p.2).isSome = vpDecisionGuard s p
  unfold vpDecision VPState.applyDecision vpDecisionGuard
  by_cases h : s.status = VPStatus.disputed ∧ s.disputeCase = some p.1 <;> simp [h]

def kassetDecisionGuard (s : KAssetState) (p : Id × VPDecision) : Bool :=
  decide (s.status = KAssetStatus.disputed ∧ s.disputeCase = some p.1)

theorem kassetDecision_guard_eq (s : KAssetState) (p : Id × VPDecision) :
    (kassetDecisionArm.step s p).isSome = kassetDecisionGuard s p := by
  change (kassetDecision s p.1 p.2).isSome = kassetDecisionGuard s p
  unfold kassetDecision KAssetState.applyDecision kassetDecisionGuard
  by_cases h : s.status = KAssetStatus.disputed ∧ s.disputeCase = some p.1 <;> simp [h]

def kassetProveApprovedGuard (s : KAssetState) (_ : Id) : Bool :=
  decide (s.approver.isSome ∧ s.status = KAssetStatus.approved)

theorem kassetProveApproved_guard_eq (s : KAssetState) (uri : Id) :
    (kassetProveApprovedArm.step s uri).isSome = kassetProveApprovedGuard s uri := by
  change (kassetProveApproved s uri).isSome = kassetProveApprovedGuard s uri
  unfold kassetProveApproved KAssetState.proveApproved kassetProveApprovedGuard
  cases h : s.approver <;> by_cases hs : s.status = KAssetStatus.approved <;> simp [h, hs]

def vpProveValidatedGuard (s : VPState) (_ : Id × Height) : Bool :=
  decide (s.status = VPStatus.validated)

theorem vpProveValidated_guard_eq (s : VPState) (p : Id × Height) :
    (vpProveValidatedArm.step s p).isSome = vpProveValidatedGuard s p := by
  change (vpProveValidated s p.1 p.2).isSome = vpProveValidatedGuard s p
  unfold vpProveValidated VPState.proveValidated vpProveValidatedGuard
  by_cases h : s.status = VPStatus.validated <;> simp [h]

def credentialProveGuard (s : CredentialState) (a : ProveArgs) : Bool :=
  CredentialState.proveAllowed s a.issuerScope a.caller a.requirement a.height

theorem credentialProve_guard_eq (s : CredentialState) (a : ProveArgs) :
    (credentialProveArm.step s a).isSome = credentialProveGuard s a := by
  change (credentialProve s a).isSome = credentialProveGuard s a
  unfold credentialProve CredentialState.prove credentialProveGuard
  by_cases h : CredentialState.proveAllowed s a.issuerScope a.caller a.requirement a.height <;>
    simp [h]

def kassetNestGuard (s : KAssetState) (p : Id × List ApprovedProofData) : Bool :=
  if p.1 = s.claimant ∧
      (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional ∨
        s.status = KAssetStatus.approved) ∧
      KAssetState.nodupIds (p.2.map (fun c => c.id)) = true ∧
      (decide (s.id ∉ p.2.map (fun c => c.id))) = true ∧
      KAssetState.strictRising (p.2.map KAssetState.childKey) = true ∧
      KAssetState.idsNotIn s.children p.2 = true ∧
      KAssetState.allBelow s.approvedAt p.2 = true ∧
      KAssetState.allScope s.discipline s.jurisdiction p.2 = true
  then true else false

theorem kassetNest_guard_eq (s : KAssetState) (p : Id × List ApprovedProofData) :
    (kassetNestArm.step s p).isSome = kassetNestGuard s p := by
  change (kassetNest s p.1 p.2).isSome = kassetNestGuard s p
  unfold kassetNest KAssetState.nest kassetNestGuard
  by_cases h : p.1 = s.claimant ∧
      (s.status = KAssetStatus.validated ∨ s.status = KAssetStatus.conditional ∨
        s.status = KAssetStatus.approved) ∧
      KAssetState.nodupIds (p.2.map (fun c => c.id)) = true ∧
      (decide (s.id ∉ p.2.map (fun c => c.id))) = true ∧
      KAssetState.strictRising (p.2.map KAssetState.childKey) = true ∧
      KAssetState.idsNotIn s.children p.2 = true ∧
      KAssetState.allBelow s.approvedAt p.2 = true ∧
      KAssetState.allScope s.discipline s.jurisdiction p.2 = true
  · rw [if_pos h]; rw [if_pos h]; rfl
  · rw [if_neg h]; rw [if_neg h]; rfl

end RGen
