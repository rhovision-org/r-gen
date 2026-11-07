import RGen.Invariants
import RGen.Linear.Consumption
import RGen.RaceFreedom
import RGen.Linear.Consumption
import RGen.ArmGuards
import RGen.Model.IdentityReservation
import RGen.Model.ClaimMint
import RGen.Model.ProofCapability
import RGen.Model.Capability
import RGen.Model.NestCrash
import RGen.Deadline
import RGen.System

/-!
# Pareto core theorem set

This file is the curated public vocabulary of the Lean core. It does not add new proofs;
it names the essential theorem per invariant so `tools/check_pareto.py` and the paper-linked
docs can refer to one stable set.

Auxiliary lemmas remain available as dependencies; duplicates are not part of this set.
-/

namespace RGen

-- Linear cells and the deployed consume/re-post pattern.
#check take_put_commit
#check VWorld.take_take_blocks
#check VWorld.take_post_commit_equiv
#check VWorld.set_commute
#check VWorld.commit_commute
#check D1_peek_put
#check D1_put_without_take
#check D2_take_without_put
#check D3_nested_call
#check run_frame
#check disjoint_cells_commute_wf

-- Versioned execution and race non-representability.
#check runExec_sound
#check runExec_complete
#check runExec_deterministic
#check runExec_projection
#check runExec_no_same_expected
#check core_races_not_representable

-- Authority and one-shot proof payloads.
#check Arm.decision_factors
#check core_arm_authority
#check cross_cell_read_not_authority
#check proof_take_once_versioned

-- Per-primitive invariants.
#check C1_prove_requires_active
#check C2_revoke_blocks_prove
#check C3_issuer_immutable
#check V1_validate_once
#check V2_dispute_blocks_prove
#check K1_approve_credential
#check K2_approve_status
#check K3_nest_acyclic
#check O1_execute_bound_once
#check O2_close_finished
#check P1_anchors_append_only
#check L1_disjoint_commute
#check L2_shared_serializes
#check L3_mayAcquire_acyclic
#check L4_deadlock_free

-- Composition.
#check claim_validation_exactly_one_kasset
#check approval_composes_credential_and_vp_proofs
#check nesting_is_a_forest_with_strict_order
#check oracle_execution_exactly_once_and_subject_bound
#check provenance_is_append_only

end RGen

#check RGen.credentialRevoke_guard_eq
#check RGen.credentialRenew_guard_eq
#check RGen.vpValidate_guard_eq
#check RGen.claimValidate_guard_eq
#check RGen.kassetApprove_guard_eq
#check RGen.oracleDecide_guard_eq
#check RGen.provenanceAnchor_guard_eq
#check RGen.identityUpdate_guard_eq
#check RGen.core_independent_arms_commute
#check RGen.Event.apply_commute_distinct
#check RGen.identityCreate_guard_eq
#check RGen.vpComment_guard_eq
#check RGen.claimComment_guard_eq
#check RGen.claimWithdraw_guard_eq
#check RGen.claimExpire_guard_eq
#check RGen.kassetReject_guard_eq
#check RGen.kassetOpenDispute_guard_eq
#check RGen.oracleExecute_guard_eq
#check RGen.oracleExpire_guard_eq
#check RGen.oracleClose_guard_eq
#check RGen.oracleEvidence_guard_eq
#check RGen.provenanceComment_guard_eq
#check RGen.credentialAttest_guard_eq
#check RGen.vpValidateArm_proof_cell
#check RGen.claimValidateArm_proof_cell
#check RGen.kassetApproveArm_proof_cells
#check RGen.kassetRejectArm_proof_cell
#check RGen.kassetNestArm_proof_cell
#check RGen.oracleDecideArm_proof_cell
#check RGen.claimRejectArm_proof_cell
#check RGen.runExec_append
#check RGen.vpWithdraw_guard_eq
#check RGen.vpOpenDispute_guard_eq
#check RGen.vpDecision_guard_eq
#check RGen.kassetDecision_guard_eq
#check RGen.kassetProveApproved_guard_eq
#check RGen.kassetNest_guard_eq
#check RGen.credentialProve_guard_eq
#check RGen.vpProveValidated_guard_eq
#check RGen.take_guard_eq
#check RGen.provenance_anchor_comment_independent
#check RGen.KAssetState.approve_requires_credential_type
#check RGen.OracleState.addEvidence_requires_party
#check RGen.core_proof_cells_consumed_before_commit
#check RGen.Action.proof_cell_not_reused

-- Identity reservation
#check RGen.ReservedDirectory.reserve_refuses_claimed
#check RGen.ReservedDirectory.commit_requires_minted
#check RGen.ReservedDirectory.commit_sets_byAddress
#check RGen.ReservedDirectory.resume_refuses_claimed
#check RGen.ReservedDirectory.reach_byAddress_stable
#check RGen.ReservedDirectory.at_most_one_identity_per_address
#check RGen.ReservedDirectory.stale_reservation_cannot_commit

-- Claim validation and mint
#check RGen.ClaimMintState.begin_blocks_second
#check RGen.ClaimMintState.mint_once
#check RGen.ClaimMintState.commit_requires_intent
#check RGen.ClaimMintState.resume_sets_from_receipt
#check RGen.ClaimMintState.resume_cannot_mint
#check RGen.ClaimMintState.at_most_one_reachable_kasset_per_claim
#check RGen.ClaimMintState.step_kassetRef_stable
#check RGen.ClaimMintState.reach_kassetRef_stable
#check RGen.ClaimMintState.at_most_one_reachable_kasset_across_reach
#check RGen.exactly_one_eventually

-- Private proof capabilities
#check RGen.ProofCap.third_party_cannot_take
#check RGen.ProofCap.take_once
#check RGen.ProofCap.reserve_release_restores
#check RGen.ProofCap.private_capability_no_bearer_dos

-- Object capabilities
#check RGen.Cap.no_holder_without_grant
#check RGen.Cap.bundle_excludes_private
#check RGen.Cap.apply_case_bound
#check RGen.Cap.forward_burns_but_cannot_forge
#check RGen.Cap.anchored_nest_requires_issued_child
#check RGen.Cap.issuer_authorize_requires_issuer

-- Nest reservation and crash safety
#check RGen.failed_check_no_reserve
#check RGen.commit_requires_all_reserved
#check RGen.commit_marks_used
#check RGen.crash_release_all
#check RGen.nest_proof_not_burned

-- Deadline boundaries
#check RGen.nil_comment_window_total
#check RGen.deadline_boundary_deterministic
#check RGen.oracle_open_requires_future
#check RGen.vp_validate_after_deadline_refused

-- Composed system
#check RGen.link_consistent_at_most_one
#check RGen.SystemReach.link_consistent
#check RGen.SystemReach.at_most_one_linked_kasset
#check RGen.system_safety

-- Cross-arm proof consumption and run framing
#check RGen.core_no_proof_reuse_across_arms
#check RGen.runExec_no_lost_update
#check RGen.runExec_unique_accepted_per_generation
