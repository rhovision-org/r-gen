/-!
# RGen basic types

The model is deliberately shallow: it does not formalise Rholang syntax, the
node scheduler, ERTP, phlo or cryptography. The flow manifest in `spec/flows`
ties each deployed arm to a declaration here; that is traceability plus a
conformance corpus, not a refinement proof.

The node's own formal layer supplies the ingredients RGen relies on:
single-use COMM (`Reduce.comm`), unforgeable names (`reduce_freeVars_subset`),
the matcher linearity predicate, append-only registry reasoning, and the
closure-disjointness commutation condition. RGen states its application
invariants itself.
-/

namespace RGen

abbrev Height := Nat
abbrev Id := Nat
abbrev CellId := Nat
abbrev Bps : Nat := 10000

structure Requirement where
  ctype : String
  discipline : String
  jurisdiction : String
  role : String
  minLevel : Nat
  deriving DecidableEq, Repr

structure Scope where
  ctype : String
  discipline : String
  jurisdiction : String
  role : String
  level : Nat
  deriving DecidableEq, Repr

structure IssuerScope where
  types : List String
  disciplines : List String
  jurisdictions : List String
  roles : List String
  maxLevel : Nat
  deriving DecidableEq, Repr

def scopeMatches (s : Scope) (r : Requirement) : Bool :=
  (s.ctype == r.ctype || s.ctype == "*") &&
  (s.discipline == r.discipline || s.discipline == "*") &&
  (s.jurisdiction == r.jurisdiction || s.jurisdiction == "global" ||
    s.jurisdiction == "*") &&
  (s.role == r.role || s.role == "*") &&
  decide (r.minLevel ≤ s.level)

def issuerCovers (i : IssuerScope) (r : Requirement) : Bool :=
  (i.types.contains r.ctype || i.types.contains "*") &&
  (i.disciplines.contains r.discipline || i.disciplines.contains "*") &&
  (i.jurisdictions.contains r.jurisdiction || i.jurisdictions.contains "global" ||
    i.jurisdictions.contains "*") &&
  (i.roles.contains r.role || i.roles.contains "*") &&
  decide (r.minLevel ≤ i.maxLevel)

/-- Strict lexicographic order on `(approvedAt, id)`. -/
def lexLt (a b : Height × Id) : Prop :=
  a.1 < b.1 ∨ (a.1 = b.1 ∧ a.2 < b.2)

theorem lexLt_irrefl (a : Height × Id) : ¬ lexLt a a := by
  intro h
  rcases h with h | ⟨_, h⟩
  · exact Nat.lt_irrefl _ h
  · exact Nat.lt_irrefl _ h

theorem lexLt_trans {a b c : Height × Id} (hab : lexLt a b) (hbc : lexLt b c) :
    lexLt a c := by
  rcases hab with hab | ⟨hab1, hab2⟩
  · rcases hbc with hbc | ⟨hbc1, _⟩
    · exact Or.inl (Nat.lt_trans hab hbc)
    · exact Or.inl (hbc1 ▸ hab)
  · rcases hbc with hbc | ⟨hbc1, hbc2⟩
    · exact Or.inl (hab1 ▸ hbc)
    · exact Or.inr ⟨hab1.trans hbc1, Nat.lt_trans hab2 hbc2⟩

end RGen
