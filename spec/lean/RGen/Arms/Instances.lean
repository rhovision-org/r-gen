import RGen.Arms.Credential
import RGen.Arms.ValueProposition
import RGen.Arms.Claim
import RGen.Arms.KAsset
import RGen.Arms.Oracle
import RGen.Arms.Provenance
import RGen.RaceFreedom

/-!
# Concrete core arm instances

Every core mutating arm has an `Arm` value: its consumed cell, its pure step (the existing
transition function), and the proof cells its decision consumes. `core_arm_authority`
instantiates to each arm, so the authority theorem is not just generic.
-/

namespace RGen

def credCell : CellId := 1
def vpCell : CellId := 2
def claimCell : CellId := 3
def kassetCell : CellId := 4
def oracleCell : CellId := 5
def provenanceCell : CellId := 6
def credentialProofCell : CellId := 7
def vpProofCell : CellId := 8
def kassetProofCell : CellId := 9

-- Credentials
def credentialProveArm : Arm CredentialState ProveArgs :=
  ⟨credCell, credentialProve, [], 1⟩

def credentialRevokeArm : Arm CredentialState Id :=
  ⟨credCell, credentialRevoke, [], 2⟩

def credentialRenewArm : Arm CredentialState (Id × Height) :=
  ⟨credCell, fun s p => credentialRenew s p.1 p.2, [], 3⟩

def credentialAttestArm : Arm CredentialState Id :=
  ⟨credCell, credentialAttest, [], 4⟩

-- Value propositions
def vpValidateArm : Arm VPState VPValidateArgs :=
  ⟨vpCell, vpValidate, [credentialProofCell], 5⟩

def vpWithdrawArm : Arm VPState Id :=
  ⟨vpCell, vpWithdraw, [], 6⟩

def vpOpenDisputeArm : Arm VPState (Id × Id) :=
  ⟨vpCell, fun s p => vpOpenDispute s p.1 p.2, [], 7⟩

def vpProveValidatedArm : Arm VPState (Id × Height) :=
  ⟨vpCell, fun s p => vpProveValidated s p.1 p.2, [], 8⟩

def vpDecisionArm : Arm VPState (Id × VPDecision) :=
  ⟨vpCell, fun s p => vpDecision s p.1 p.2, [], 9⟩

-- Claims
def claimValidateArm : Arm ClaimState ClaimValidateArgs :=
  ⟨claimCell, claimValidate, [credentialProofCell], 10⟩

def claimWithdrawArm : Arm ClaimState Id :=
  ⟨claimCell, claimWithdraw, [], 11⟩

def claimExpireArm : Arm ClaimState Height :=
  ⟨claimCell, claimExpire, [], 12⟩

def claimCommentArm : Arm ClaimState (Id × Height) :=
  ⟨claimCell, fun s p => claimComment s p.1 p.2, [], 13⟩

def claimRejectArm : Arm ClaimState ClaimValidateArgs :=
  ⟨claimCell, claimReject, [credentialProofCell], 14⟩

-- K-Assets
def kassetApproveArm : Arm KAssetState KApproveArgs :=
  ⟨kassetCell, kassetApprove, [credentialProofCell, vpProofCell], 15⟩

def kassetRejectArm : Arm KAssetState KRejectArgs :=
  ⟨kassetCell, kassetReject, [credentialProofCell], 16⟩

def kassetProveApprovedArm : Arm KAssetState Id :=
  ⟨kassetCell, kassetProveApproved, [], 17⟩

def kassetOpenDisputeArm : Arm KAssetState (Id × Id) :=
  ⟨kassetCell, fun s p => kassetOpenDispute s p.1 p.2, [], 18⟩

def kassetDecisionArm : Arm KAssetState (Id × VPDecision) :=
  ⟨kassetCell, fun s p => kassetDecision s p.1 p.2, [], 19⟩

def kassetNestArm : Arm KAssetState (Id × List ApprovedProofData) :=
  ⟨kassetCell, fun s p => kassetNest s p.1 p.2, [kassetProofCell], 20⟩

-- Oracle
def oracleDecideArm : Arm OracleState OracleDecideArgs :=
  ⟨oracleCell, oracleDecide, [credentialProofCell], 21⟩

def oracleExpireArm : Arm OracleState Height :=
  ⟨oracleCell, oracleExpire, [], 22⟩

def oracleExecuteArm : Arm OracleState Id :=
  ⟨oracleCell, oracleExecute, [], 23⟩

def oracleFinishArm : Arm OracleState Unit :=
  ⟨oracleCell, fun s _ => oracleFinish s, [], 24⟩

def oracleCloseArm : Arm OracleState Unit :=
  ⟨oracleCell, fun s _ => oracleClose s, [], 25⟩

def oracleEvidenceArm : Arm OracleState Id :=
  ⟨oracleCell, oracleEvidence, [], 26⟩

def oracleRollbackArm : Arm OracleState Unit :=
  ⟨oracleCell, fun s _ => oracleRollback s, [], 27⟩

-- Provenance
def provenanceAnchorArm : Arm ProvenanceState (Id × (Id × Id)) :=
  ⟨provenanceCell, fun s p => provenanceAnchor s p.1 p.2, [], 28⟩

def provenanceCommentArm : Arm ProvenanceState (Id × Id) :=
  ⟨provenanceCell, fun s p => provenanceComment s p.1 p.2, [], 29⟩

-- Authority instantiations
theorem credential_prove_arm_authority (p : ProveArgs) :
    DependsOnlyOn (fun w => credentialProveArm.decision w p) [credCell] :=
  core_arm_authority credentialProveArm p

theorem credential_revoke_arm_authority (p : Id) :
    DependsOnlyOn (fun w => credentialRevokeArm.decision w p) [credCell] :=
  core_arm_authority credentialRevokeArm p

theorem credential_renew_arm_authority (p : Id × Height) :
    DependsOnlyOn (fun w => credentialRenewArm.decision w p) [credCell] :=
  core_arm_authority credentialRenewArm p

theorem credential_attest_arm_authority (p : Id) :
    DependsOnlyOn (fun w => credentialAttestArm.decision w p) [credCell] :=
  core_arm_authority credentialAttestArm p

theorem vp_validate_arm_authority (p : VPValidateArgs) :
    DependsOnlyOn (fun w => vpValidateArm.decision w p) [vpCell] :=
  core_arm_authority vpValidateArm p

theorem vp_prove_validated_arm_authority (p : Id × Height) :
    DependsOnlyOn (fun w => vpProveValidatedArm.decision w p) [vpCell] :=
  core_arm_authority vpProveValidatedArm p

theorem claim_validate_arm_authority (p : ClaimValidateArgs) :
    DependsOnlyOn (fun w => claimValidateArm.decision w p) [claimCell] :=
  core_arm_authority claimValidateArm p

theorem vp_withdraw_arm_authority (p : Id) :
    DependsOnlyOn (fun w => vpWithdrawArm.decision w p) [vpCell] :=
  core_arm_authority vpWithdrawArm p

theorem vp_open_dispute_arm_authority (p : Id × Id) :
    DependsOnlyOn (fun w => vpOpenDisputeArm.decision w p) [vpCell] :=
  core_arm_authority vpOpenDisputeArm p

theorem vp_decision_arm_authority (p : Id × VPDecision) :
    DependsOnlyOn (fun w => vpDecisionArm.decision w p) [vpCell] :=
  core_arm_authority vpDecisionArm p

theorem claim_withdraw_arm_authority (p : Id) :
    DependsOnlyOn (fun w => claimWithdrawArm.decision w p) [claimCell] :=
  core_arm_authority claimWithdrawArm p

theorem claim_expire_arm_authority (p : Height) :
    DependsOnlyOn (fun w => claimExpireArm.decision w p) [claimCell] :=
  core_arm_authority claimExpireArm p

theorem claim_reject_arm_authority (p : ClaimValidateArgs) :
    DependsOnlyOn (fun w => claimRejectArm.decision w p) [claimCell] :=
  core_arm_authority claimRejectArm p

theorem claim_comment_arm_authority (p : Id × Height) :
    DependsOnlyOn (fun w => claimCommentArm.decision w p) [claimCell] :=
  core_arm_authority claimCommentArm p

theorem kasset_approve_arm_authority (p : KApproveArgs) :
    DependsOnlyOn (fun w => kassetApproveArm.decision w p) [kassetCell] :=
  core_arm_authority kassetApproveArm p

theorem kasset_reject_arm_authority (p : KRejectArgs) :
    DependsOnlyOn (fun w => kassetRejectArm.decision w p) [kassetCell] :=
  core_arm_authority kassetRejectArm p

theorem kasset_nest_arm_authority (p : Id × List ApprovedProofData) :
    DependsOnlyOn (fun w => kassetNestArm.decision w p) [kassetCell] :=
  core_arm_authority kassetNestArm p

theorem kasset_prove_approved_arm_authority (p : Id) :
    DependsOnlyOn (fun w => kassetProveApprovedArm.decision w p) [kassetCell] :=
  core_arm_authority kassetProveApprovedArm p

theorem kasset_open_dispute_arm_authority (p : Id × Id) :
    DependsOnlyOn (fun w => kassetOpenDisputeArm.decision w p) [kassetCell] :=
  core_arm_authority kassetOpenDisputeArm p

theorem kasset_decision_arm_authority (p : Id × VPDecision) :
    DependsOnlyOn (fun w => kassetDecisionArm.decision w p) [kassetCell] :=
  core_arm_authority kassetDecisionArm p

theorem oracle_decide_arm_authority (p : OracleDecideArgs) :
    DependsOnlyOn (fun w => oracleDecideArm.decision w p) [oracleCell] :=
  core_arm_authority oracleDecideArm p

theorem oracle_execute_arm_authority (p : Id) :
    DependsOnlyOn (fun w => oracleExecuteArm.decision w p) [oracleCell] :=
  core_arm_authority oracleExecuteArm p

theorem oracle_expire_arm_authority (p : Height) :
    DependsOnlyOn (fun w => oracleExpireArm.decision w p) [oracleCell] :=
  core_arm_authority oracleExpireArm p

theorem oracle_finish_arm_authority (p : Unit) :
    DependsOnlyOn (fun w => oracleFinishArm.decision w p) [oracleCell] :=
  core_arm_authority oracleFinishArm p

theorem oracle_close_arm_authority (p : Unit) :
    DependsOnlyOn (fun w => oracleCloseArm.decision w p) [oracleCell] :=
  core_arm_authority oracleCloseArm p

theorem oracle_evidence_arm_authority (p : Id) :
    DependsOnlyOn (fun w => oracleEvidenceArm.decision w p) [oracleCell] :=
  core_arm_authority oracleEvidenceArm p

theorem oracle_rollback_arm_authority (p : Unit) :
    DependsOnlyOn (fun w => oracleRollbackArm.decision w p) [oracleCell] :=
  core_arm_authority oracleRollbackArm p

theorem provenance_anchor_arm_authority (p : Id × (Id × Id)) :
    DependsOnlyOn (fun w => provenanceAnchorArm.decision w p) [provenanceCell] :=
  core_arm_authority provenanceAnchorArm p

theorem provenance_comment_arm_authority (p : Id × Id) :
    DependsOnlyOn (fun w => provenanceCommentArm.decision w p) [provenanceCell] :=
  core_arm_authority provenanceCommentArm p

end RGen
