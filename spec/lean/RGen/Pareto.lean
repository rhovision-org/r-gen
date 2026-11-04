import RGen.Invariants
import RGen.RaceFreedom
import RGen.ArmGuards

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
