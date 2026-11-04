import RGen.Arms.Credential
import RGen.Arms.ValueProposition
import RGen.Arms.Claim
import RGen.Arms.KAsset
import RGen.Arms.Oracle
import RGen.Arms.Provenance
import RGen.Model.ProofVersioned
import RGen.Linear.Cell

/-!
# Race freedom: the model-level non-representability theorem

`core_races_not_representable` is quantified over **all** runs, not over a chosen
schedule: in every `Run`, no two events on one cell share an expected generation. Accepted
commits are a subset of events, so no two accepted commits share a generation.

`core_arm_authority` covers every arm built with `Arm`: its decision factors through its
consumed cell. Proof payloads are consumed through the one-shot proof cell
(`proof_take_once_versioned`); a peek is not authority (`cross_cell_read_not_authority`).

The pair files classify every mutating arm pair as `TwoWayExclusive` or one-way `NeverAfter`.
This is a model proof, not a refinement of the deployed Rholang; the flow manifest records
the hand encoding.
-/

namespace RGen

/-- Every arm's decision factors through its consumed cell. -/
theorem core_arm_authority {σ π : Type} (a : Arm σ π) (p : π) :
    DependsOnlyOn (fun w => a.decision w p) [a.cell] :=
  Arm.decision_authority a p

/-- Every arm's decision is a function of the consumed cell value. -/
theorem core_arm_factors {σ π : Type} (a : Arm σ π) (p : π) :
    FactorsThroughCell (fun w => a.decision w p) a.cell :=
  Arm.decision_factors a p

/-- No two events on one cell share an expected generation, in any run. -/
theorem core_no_two_commits_same_generation {σ : Type} {w : VWorld σ}
    {es : List (Event σ)} {w' : VWorld σ} (h : Run w es w') (c : CellId) :
    NoTwoSameExpected c es :=
  runExec_no_same_expected (runExec_complete h) c

/-- The headline non-representability theorem: a same-generation race is not a `Run`. -/
theorem core_races_not_representable {σ : Type} {w : VWorld σ}
    {es : List (Event σ)} {w' : VWorld σ} (h : Run w es w') (c : CellId) :
    NoTwoSameExpected c es :=
  core_no_two_commits_same_generation h c

/-- Same-cell events serialize: the no-same-generation statement is the ordering fact. -/
theorem core_same_cell_serialization {σ : Type} {w : VWorld σ}
    {es : List (Event σ)} {w' : VWorld σ} (h : Run w es w') (c : CellId) :
    NoTwoSameExpected c es :=
  core_races_not_representable h c

/-- Proof payloads are one-shot: after an accepted take the next take rejects. -/
theorem core_proof_payloads_consumed {α : Type} {w : VWorld (ProofState α)}
    {c : CellId} {n : Nat} {p : ProofState α}
    (hcell : w.cell c = some ⟨p, n⟩) (hp : p.used = false) :
    ∃ w', (proofEvent c n).apply w = .accepted w' ∧
      CommitOutcome.isRejected ((proofEvent c (n + 1)).apply w') = true :=
  proof_take_once_versioned hcell hp

/-- Independent traces over disjoint stores commute (the existing `L1` theorem). -/
theorem core_independent_cells_commute {α : Type} (s : Store α)
    (ops1 ops2 : List (Op α)) (hdisj : FootprintDisjoint ops1 ops2)
    {sA sB : Store α}
    (h1 : run s [] ops1 = some (sA, [])) (h2 : run s [] ops2 = some (sB, [])) :
    run s [] (ops1 ++ ops2) = run s [] (ops2 ++ ops1) :=
  disjoint_cells_commute_wf s ops1 ops2 hdisj h1 h2


/-- Events for arms on distinct cells reach the same final world in either order. This is
independence of disjoint footprints, not a global race-freedom claim. -/
theorem core_independent_arms_commute {σ π1 π2 : Type} (a1 : Arm σ π1) (a2 : Arm σ π2)
    (h : a1.cell ≠ a2.cell) (p1 : π1) (p2 : π2) (n1 n2 : Nat) (w : VWorld σ) :
    ((a2.event p2 n2).applyThen ((a1.event p1 n1).apply w)).world =
      ((a1.event p1 n1).applyThen ((a2.event p2 n2).apply w)).world :=
  Event.apply_commute_distinct h w

end RGen
