import RGen.Linear.Cell
import RGen.Linear.Protocol
import RGen.Model.Proof

/-!
# Concurrency: ranks, acquisition order, and commutation

Each entity kind has a rank. A holder may acquire a proof of a lower-ranked
kind, never its own kind. Every `MayAcquire` edge strictly decreases rank, so the
acquisition relation is acyclic and the wait-for graph cannot cycle under the
finite-cell/no-dynamic-locks hypothesis.

This is a lock-order theorem, not scheduler liveness. Rholo's Law 20 global
deadlock-freedom was deleted as unprovable without a finiteness hypothesis; the
same caution applies here.

K-Assets acquire child K-Assets by a different mechanism — the two-phase `nest`
holds no business cell while taking child proofs — so there is deliberately no
`KAsset → KAsset` edge.
-/

namespace RGen

inductive CellKind where
  | proof
  | credential
  | valueProposition
  | claim
  | kasset
  | oracle
  deriving DecidableEq, Repr

def CellKind.rank : CellKind → Nat
  | .proof => 0
  | .credential => 1
  | .valueProposition => 2
  | .oracle => 3
  | .claim => 3
  | .kasset => 4

/-- `MayAcquire a b` means a holder of an `a` cell may take a proof from a `b`
cell (or otherwise acquire `b`) while holding `a`. -/
def MayAcquire : CellKind → CellKind → Prop
  | .proof, _ => False
  | .claim, .credential => True
  | .valueProposition, .credential => True
  | .oracle, .credential => True
  | .kasset, .credential => True
  | .kasset, .valueProposition => True
  | _, .proof => True
  | _, _ => False

theorem mayAcquire_rank_strict {a b : CellKind} (h : MayAcquire a b) :
    b.rank < a.rank := by
  cases a <;> cases b <;> simp [MayAcquire, CellKind.rank] at h ⊢ <;> omega

theorem mayAcquire_transGen_rank {a b : CellKind}
    (h : Relation.TransGen MayAcquire a b) : b.rank < a.rank := by
  induction h with
  | single hab => exact mayAcquire_rank_strict hab
  | tail _ hbc ih => exact Nat.lt_trans (mayAcquire_rank_strict hbc) ih

/-- Acquisition cannot cycle. -/
theorem mayAcquire_acyclic {a : CellKind} (h : Relation.TransGen MayAcquire a a) : False :=
  Nat.lt_irrefl _ (mayAcquire_transGen_rank h)

/-- If every wait edge strictly decreases a rank on a finite cell set, no wait
cycle exists. This is the rank argument, not a global liveness claim. -/
theorem transGen_rank_desc {σ : Type} (rank : σ → Nat) (wait : σ → σ → Prop)
    (hdec : ∀ a b, wait a b → rank b < rank a) :
    ∀ {a b : σ}, Relation.TransGen wait a b → rank b < rank a := by
  intro a b h
  induction h with
  | single hab => exact hdec _ _ hab
  | tail _ hbc ih => exact Nat.lt_trans (hdec _ _ hbc) ih

theorem deadlock_free_of_rank {σ : Type} (rank : σ → Nat) (wait : σ → σ → Prop)
    (hdec : ∀ a b, wait a b → rank b < rank a) :
    ∀ a, ¬ Relation.TransGen wait a a := by
  intro a h
  exact Nat.lt_irrefl _ (transGen_rank_desc rank wait hdec h)

/-! ### The commit lemmas, specialised -/

/-- Commits on different cells commute: independent entities do not interact. -/
theorem independent_commute {α : Type} (w : World α) (c1 c2 : CellId)
    (f1 f2 : α → Option α) (h : c1 ≠ c2) :
    (w.commit c1 f1).bind (fun w' => w'.commit c2 f2)
      = (w.commit c2 f2).bind (fun w' => w'.commit c1 f1) :=
  World.commit_commute w c1 c2 f1 f2 h

/-- Two commits on the same cell compose: the second sees the first's post-state. -/
theorem shared_serializes {α : Type} (w : World α) (c : CellId)
    (f1 f2 : α → Option α) :
    (w.commit c f1).bind (fun w' => w'.commit c f2)
      = w.commit c (fun v => (f1 v).bind f2) :=
  World.commit_same_cell w c f1 f2

theorem proof_one_shot {α : Type} (p : ProofState α) (h : p.used = true) :
    p.take = none :=
  proof_take_second p h

theorem proof_snapshot {α : Type} {p : ProofState α} {d : α} {p' : ProofState α}
    (h : p.take = some (d, p')) : p.data = d :=
  proof_take_data h

end RGen
