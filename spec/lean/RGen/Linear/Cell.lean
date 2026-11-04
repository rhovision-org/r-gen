import RGen.Basic

/-!
# Linear cells and the commit primitive

A cell holds at most one value. `peek` reads without changing it; `take` empties
it and records it as held; `put` requires the cell empty and held; `call` is a
nested deployment step and may not touch a held cell. `commit` is one atomic
read-modify-write: it never exposes an empty cell.

The application model uses `World`/`commit`, not the lower-level
`Store`/`take`/`put` trajectory, for its entity concurrency proofs. `Store`/`run`
carries the D1–D3 rejection laws that the Rholang discipline mirrors, and the
trace-level independence result: two traces whose footprints are disjoint are
framed (`run_frame`) and commute (`disjoint_cells_commute`).

The key theorems:

* `run_frame` — a trace leaves every cell outside its footprint alone, both its
  value and its occurrence count in the held list.
* `disjoint_cells_commute` — traces over disjoint footprints commute on the store.
* `disjoint_cells_commute_wf` — from an empty held set, two well-formed traces
  commute exactly, held set included.
* `commit_commute` — commits on different cells commute (independent entities).
* `commit_same_cell` — a second commit on the same cell composes with the first;
  both cannot decide from the same pre-state.
* `commit_preserves_other` — a commit on one cell leaves every other cell alone.

`Store`/`run` is deliberately byte-level: the held list records a `take` by
consing, without deduplicating. Held agreement is therefore stated as
per-cell occurrence counts (`occ`), which `take`/`put` preserve; plain
membership is not preserved by `put` when the initial held list has duplicates.
-/

namespace RGen

/-! ## Trace model (D1–D3) -/

structure Store (α : Type) where
  cells : CellId → List α

namespace Store

variable {α : Type}

def empty : Store α := ⟨fun _ => []⟩

def set (s : Store α) (c : CellId) (v : List α) : Store α :=
  ⟨fun x => if x = c then v else s.cells x⟩

@[simp] theorem set_same (s : Store α) (c : CellId) (v : List α) :
    (s.set c v).cells c = v := by
  simp [set]

theorem set_other (s : Store α) (c d : CellId) (v : List α) (h : d ≠ c) :
    (s.set c v).cells d = s.cells d := by
  simp [set, h]

end Store

inductive Op (α : Type) where
  | peek (c : CellId)
  | take (c : CellId)
  | put (c : CellId) (v : α)
  | call (c : CellId)
  | commit (c : CellId) (f : α → Option α)

/-- Run a trace. A failure is `none`; a graceful stop returns the held set. -/
def run {α : Type} : Store α → List CellId → List (Op α) → Option (Store α × List CellId)
  | s, h, [] => some (s, h)
  | s, h, Op.peek c :: rest =>
      match s.cells c with
      | [] => none
      | _ => run s h rest
  | s, h, Op.take c :: rest =>
      match s.cells c with
      | [_] => run (s.set c []) (c :: h) rest
      | _ => none
  | s, h, Op.put c v :: rest =>
      match s.cells c with
      | [] => if c ∈ h then run (s.set c [v]) (h.erase c) rest else none
      | _ => none
  | s, h, Op.call c :: rest =>
      if c ∈ h then none else run s h rest
  | s, h, Op.commit c f :: rest =>
      match s.cells c with
      | [v] =>
          match f v with
          | some v' => run (s.set c [v']) h rest
          | none => none
      | _ => none

/-- A trace is well formed when it stops with nothing held. -/
def WF {α : Type} (s : Store α) (h : List CellId) (ops : List (Op α)) : Prop :=
  ∃ s' h', run s h ops = some (s', h') ∧ h' = []

/-- D1: peeking then posting the same cell is not a committed update. -/
theorem peek_then_put_rejected {α : Type} {s : Store α} {h : List CellId}
    {c : CellId} {v : α} (hne : s.cells c ≠ []) :
    run s h [Op.peek c, Op.put c v] = none := by
  cases hc : s.cells c with
  | nil => exact absurd hc hne
  | cons x xs => simp [run, hc]

/-- D1: a post with no take at all is rejected. -/
theorem put_without_take_rejected {α : Type} {s : Store α} {h : List CellId}
    {c : CellId} {v : α} (hempty : s.cells c = []) (hnot : c ∉ h) :
    run s h [Op.put c v] = none := by
  simp [run, hempty, hnot]

/-- D2: a graceful stop after a take leaves the cell held. -/
theorem take_without_put_not_wf {α : Type} {s : Store α} {h : List CellId}
    {c : CellId} {v : α} (hcell : s.cells c = [v]) : ¬ WF s h [Op.take c] := by
  intro hwf
  rcases hwf with ⟨s', h', hrun, hstop⟩
  simp [run, hcell] at hrun
  rcases hrun with ⟨rfl, rfl⟩
  simp at hstop

/-- D3: a nested call on a held cell is blocked. -/
theorem nested_call_rejected {α : Type} {s : Store α} {h : List CellId}
    {c : CellId} (hheld : c ∈ h) : run s h [Op.call c] = none := by
  simp [run, hheld]

/-- A take then a put is the committed update. -/
theorem take_put_commit {α : Type} {s : Store α} {h : List CellId}
    {c : CellId} {v : α} (hcell : s.cells c = [v]) (hnot : c ∉ h) :
    run s h [Op.take c, Op.put c v]
      = some ((s.set c []).set c [v], h.erase c) := by
  have hset : (s.set c []).cells c = [] := by simp
  simp [run, hcell, hnot, hset]
  rw [List.erase_of_not_mem hnot]

/-- I1: an empty trace is quiescent. -/
theorem wf_quiescent {α : Type} (s : Store α) : WF s [] [] :=
  ⟨s, [], rfl, rfl⟩

/-! ## Footprints and framing -/

def opCell {α : Type} : Op α → CellId
  | .peek c => c
  | .take c => c
  | .put c _ => c
  | .call c => c
  | .commit c _ => c

def footprint {α : Type} (ops : List (Op α)) : List CellId := ops.map opCell

@[simp] theorem footprint_nil {α : Type} : footprint ([] : List (Op α)) = [] := rfl

@[simp] theorem footprint_cons {α : Type} (op : Op α) (ops : List (Op α)) :
    footprint (op :: ops) = opCell op :: footprint ops := rfl

@[simp] theorem opCell_peek {α : Type} (c : CellId) : opCell (Op.peek c : Op α) = c := rfl
@[simp] theorem opCell_take {α : Type} (c : CellId) : opCell (Op.take c : Op α) = c := rfl
@[simp] theorem opCell_put {α : Type} (c : CellId) (v : α) : opCell (Op.put c v : Op α) = c := rfl
@[simp] theorem opCell_call {α : Type} (c : CellId) : opCell (Op.call c : Op α) = c := rfl
@[simp] theorem opCell_commit {α : Type} (c : CellId) (f : α → Option α) :
    opCell (Op.commit c f : Op α) = c := rfl

def FootprintDisjoint {α : Type} (ops1 ops2 : List (Op α)) : Prop :=
  ∀ c, c ∈ footprint ops1 → c ∈ footprint ops2 → False

/-! ## Occurrence counts for the held set -/

def occ (d : CellId) : List CellId → Nat
  | [] => 0
  | x :: xs => (if x = d then 1 else 0) + occ d xs

@[simp] theorem occ_nil (d : CellId) : occ d [] = 0 := rfl

theorem occ_cons_same (d : CellId) (xs : List CellId) :
    occ d (d :: xs) = 1 + occ d xs := by
  simp [occ]

theorem occ_cons_other {x d : CellId} (h : x ≠ d) (xs : List CellId) :
    occ d (x :: xs) = occ d xs := by
  simp [occ, h]

theorem mem_iff_occ_pos {d : CellId} {h : List CellId} : d ∈ h ↔ 0 < occ d h := by
  induction h with
  | nil => simp [occ]
  | cons x xs ih =>
      by_cases hx : x = d
      · subst hx
        rw [occ_cons_same]
        simp
        omega
      · rw [List.mem_cons, occ_cons_other hx]
        have hxd : d ≠ x := fun h => hx h.symm
        simp [hxd, ih]

theorem occ_erase_self (d : CellId) (l : List CellId) :
    occ d (l.erase d) = occ d l - 1 := by
  induction l with
  | nil => simp [occ]
  | cons x xs ih =>
      by_cases hx : x = d
      · subst hx
        rw [List.erase_cons_head, occ_cons_same]
        omega
      · have hb : ¬(x == d) = true := by simpa [beq_iff_eq] using hx
        rw [List.erase_cons_tail hb, occ_cons_other hx, occ_cons_other hx, ih]

theorem occ_erase_other {d c : CellId} (h : d ≠ c) (l : List CellId) :
    occ d (l.erase c) = occ d l := by
  induction l with
  | nil => simp [occ]
  | cons x xs ih =>
      by_cases hx : x = c
      · subst hx
        rw [List.erase_cons_head]
        rw [occ_cons_other (x := x) (d := d) (Ne.symm h)]
      · have hb : ¬(x == c) = true := by simpa [beq_iff_eq] using hx
        rw [List.erase_cons_tail hb]
        by_cases hxd : x = d
        · subst hxd
          rw [occ_cons_same, occ_cons_same, ih]
        · rw [occ_cons_other hxd, occ_cons_other hxd, ih]

/-- Two held sets agree on the cells in `C` when every such cell occurs equally often. -/
def HeldAgree (C : List CellId) (h1 h2 : List CellId) : Prop :=
  ∀ d, d ∈ C → occ d h1 = occ d h2

/-- Agreement of two states on a set of cells. -/
def Agree {α : Type} (C : List CellId) (s1 s2 : Store α) (h1 h2 : List CellId) : Prop :=
  (∀ d, d ∈ C → s1.cells d = s2.cells d) ∧ HeldAgree C h1 h2

theorem agree_of_subset {α : Type} {C C' : List CellId} {s1 s2 : Store α}
    {h1 h2 : List CellId} (h : Agree C' s1 s2 h1 h2)
    (hsub : ∀ d, d ∈ C → d ∈ C') : Agree C s1 s2 h1 h2 :=
  ⟨fun d hd => h.1 d (hsub d hd), fun d hd => h.2 d (hsub d hd)⟩

theorem run_frame {α : Type} :
    ∀ (ops : List (Op α)) (s : Store α) (h : List CellId) (s' : Store α) (h' : List CellId),
      run s h ops = some (s', h') →
      (∀ d, d ∉ footprint ops → s'.cells d = s.cells d) ∧
      (∀ d, d ∉ footprint ops → occ d h' = occ d h) := by
  intro ops
  induction ops with
  | nil =>
      intro s h s' h' hr
      simp [run] at hr
      obtain ⟨rfl, rfl⟩ := hr
      exact ⟨fun _ _ => rfl, fun _ _ => rfl⟩
  | cons op rest ih =>
      intro s h s' h' hr
      have key : ∀ d, d ∉ footprint (op :: rest) → d ≠ opCell op ∧ d ∉ footprint rest := by
        intro d hd
        simp only [footprint_cons, List.mem_cons, not_or] at hd
        exact ⟨hd.1, hd.2⟩
      cases op with
      | peek c =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              simp only [run, hc] at hr
              obtain ⟨hs, hh⟩ := ih s h s' h' hr
              refine ⟨?_, ?_⟩
              · intro d hd; exact hs d (key d hd).2
              · intro d hd; exact hh d (key d hd).2
      | take c =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              cases xs with
              | nil =>
                  simp only [run, hc] at hr
                  obtain ⟨hs, hh⟩ := ih (s.set c []) (c :: h) s' h' hr
                  refine ⟨?_, ?_⟩
                  · intro d hd
                    have hd' := (key d hd).2
                    have hdc : d ≠ c := (key d hd).1
                    rw [hs d hd']
                    exact Store.set_other s c d [] hdc
                  · intro d hd
                    have hd' := (key d hd).2
                    have hdc : d ≠ c := (key d hd).1
                    rw [hh d hd', occ_cons_other hdc.symm]
              | cons y ys => simp [run, hc] at hr
      | put c v =>
          cases hc : s.cells c with
          | cons x xs => simp [run, hc] at hr
          | nil =>
              by_cases hmem : c ∈ h
              · simp only [run, hc, hmem, ↓reduceIte] at hr
                obtain ⟨hs, hh⟩ := ih (s.set c [v]) (h.erase c) s' h' hr
                refine ⟨?_, ?_⟩
                · intro d hd
                  have hd' := (key d hd).2
                  have hdc : d ≠ c := (key d hd).1
                  rw [hs d hd']
                  exact Store.set_other s c d [v] hdc
                · intro d hd
                  have hd' := (key d hd).2
                  have hdc : d ≠ c := (key d hd).1
                  rw [hh d hd', occ_erase_other hdc]
              · simp [run, hc, hmem] at hr
      | call c =>
          by_cases hmem : c ∈ h
          · simp [run, hmem] at hr
          · simp only [run, hmem, ↓reduceIte] at hr
            obtain ⟨hs, hh⟩ := ih s h s' h' hr
            refine ⟨?_, ?_⟩
            · intro d hd; exact hs d (key d hd).2
            · intro d hd; exact hh d (key d hd).2
      | commit c f =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              cases xs with
              | cons y ys => simp [run, hc] at hr
              | nil =>
                  cases hf : f x with
                  | none => simp [run, hc, hf] at hr
                  | some v' =>
                      simp only [run, hc, hf] at hr
                      obtain ⟨hs, hh⟩ := ih (s.set c [v']) h s' h' hr
                      refine ⟨?_, ?_⟩
                      · intro d hd
                        have hd' := (key d hd).2
                        have hdc : d ≠ c := (key d hd).1
                        rw [hs d hd']
                        exact Store.set_other s c d [v'] hdc
                      · intro d hd
                        exact hh d (key d hd).2

theorem agree_of_rest {α : Type} (op : Op α) (rest : List (Op α)) (C : List CellId)
    {s1o s2o : Store α} {h1o h2o : List CellId}
    {s1' : Store α} {h1' : List CellId} {s2' : Store α} {h2' : List CellId}
    (hpost : Agree (C ++ footprint (op :: rest)) s1o s2o h1o h2o)
    (hr1 : run s1o h1o rest = some (s1', h1'))
    (hr2 : run s2o h2o rest = some (s2', h2'))
    (hres : Agree (C ++ footprint rest) s1' s2' h1' h2') :
    Agree (C ++ footprint (op :: rest)) s1' s2' h1' h2' := by
  have f1 := run_frame rest s1o h1o s1' h1' hr1
  have f2 := run_frame rest s2o h2o s2' h2' hr2
  have extra : ∀ d, d ∈ C ++ footprint (op :: rest) → d ∉ C ++ footprint rest →
      d ∉ footprint rest := by
    intro d hd hdr
    simp only [List.mem_append, footprint_cons, List.mem_cons] at hd hdr
    exact fun hm => hdr (Or.inr hm)
  constructor
  · intro d hd
    by_cases hdr : d ∈ C ++ footprint rest
    · exact hres.1 d hdr
    · have hdf := extra d hd hdr
      rw [f1.1 d hdf, f2.1 d hdf]
      exact hpost.1 d hd
  · intro d hd
    by_cases hdr : d ∈ C ++ footprint rest
    · exact hres.2 d hdr
    · have hdf := extra d hd hdr
      exact (f1.2 d hdf).trans ((hpost.2 d hd).trans (f2.2 d hdf).symm)

theorem run_agree {α : Type} :
    ∀ (ops : List (Op α)) (C : List CellId) (s1 s2 : Store α) (h1 h2 : List CellId),
      Agree (C ++ footprint ops) s1 s2 h1 h2 →
      (run s1 h1 ops = none ↔ run s2 h2 ops = none) ∧
      (∀ s1' h1' s2' h2', run s1 h1 ops = some (s1', h1') →
        run s2 h2 ops = some (s2', h2') →
        Agree (C ++ footprint ops) s1' s2' h1' h2') := by
  intro ops
  induction ops with
  | nil =>
      intro C s1 s2 h1 h2 hs
      constructor
      · simp [run]
      · intro s1' h1' s2' h2' hr1 hr2
        simp [run] at hr1 hr2
        obtain ⟨rfl, rfl⟩ := hr1
        obtain ⟨rfl, rfl⟩ := hr2
        simpa using hs
  | cons op rest ih =>
      intro C s1 s2 h1 h2 hs
      have hsub : ∀ d, d ∈ C ++ footprint rest → d ∈ C ++ footprint (op :: rest) := by
        intro d hd
        simp only [List.mem_append, footprint_cons, List.mem_cons] at hd ⊢
        rcases hd with h | h
        · exact Or.inl h
        · exact Or.inr (Or.inr h)
      cases op with
      | peek c =>
          have hcEq : s1.cells c = s2.cells c := hs.1 c (by simp)
          cases h1c : s1.cells c with
          | nil =>
              have h2c : s2.cells c = [] := by rw [← hcEq, h1c]
              constructor
              · simp [run, h1c, h2c]
              · intro s1' h1' s2' h2' hr1 _hr2
                simp [run, h1c] at hr1
          | cons x xs =>
              have h2c : s2.cells c = x :: xs := by rw [← hcEq, h1c]
              have hpos := ih C s1 s2 h1 h2 (agree_of_subset hs hsub)
              constructor
              · simp only [run, h1c, h2c]
                exact hpos.1
              · intro s1' h1' s2' h2' hr1 hr2
                simp only [run, h1c] at hr1
                simp only [run, h2c] at hr2
                exact agree_of_rest (Op.peek c) rest C hs hr1 hr2
                  (hpos.2 s1' h1' s2' h2' hr1 hr2)
      | take c =>
          have hcfull : c ∈ C ++ footprint (Op.take c :: rest) := by simp
          have hcEq : s1.cells c = s2.cells c := hs.1 c hcfull
          cases h1c : s1.cells c with
          | nil =>
              have h2c : s2.cells c = [] := by rw [← hcEq, h1c]
              constructor
              · simp [run, h1c, h2c]
              · intro s1' h1' s2' h2' hr1 _hr2
                simp [run, h1c] at hr1
          | cons x xs =>
              cases xs with
              | cons y ys =>
                  have h2c : s2.cells c = x :: y :: ys := by rw [← hcEq, h1c]
                  constructor
                  · simp [run, h1c, h2c]
                  · intro s1' h1' s2' h2' hr1 _hr2
                    simp [run, h1c] at hr1
              | nil =>
                  have h2c : s2.cells c = [x] := by rw [← hcEq, h1c]
                  have hpost : Agree (C ++ footprint (Op.take c :: rest))
                      (s1.set c []) (s2.set c []) (c :: h1) (c :: h2) := by
                    constructor
                    · intro d hd
                      by_cases hdc : d = c
                      · subst hdc; simp
                      · rw [Store.set_other s1 c d [] hdc, Store.set_other s2 c d [] hdc]
                        exact hs.1 d hd
                    · intro d hd
                      by_cases hdc : d = c
                      · subst hdc
                        rw [occ_cons_same, occ_cons_same, hs.2 d hd]
                      · have hcd : c ≠ d := fun h => hdc h.symm
                        rw [occ_cons_other hcd, occ_cons_other hcd]
                        exact hs.2 d hd
                  have hpos := ih C (s1.set c []) (s2.set c []) (c :: h1) (c :: h2)
                    (agree_of_subset hpost hsub)
                  constructor
                  · simp only [run, h1c, h2c]
                    exact hpos.1
                  · intro s1' h1' s2' h2' hr1 hr2
                    simp only [run, h1c] at hr1
                    simp only [run, h2c] at hr2
                    exact agree_of_rest (Op.take c) rest C hpost hr1 hr2
                      (hpos.2 s1' h1' s2' h2' hr1 hr2)
      | put c v =>
          have hcfull : c ∈ C ++ footprint (Op.put c v :: rest) := by simp
          have hcEq : s1.cells c = s2.cells c := hs.1 c hcfull
          have hmem : c ∈ h1 ↔ c ∈ h2 := by
            rw [mem_iff_occ_pos, mem_iff_occ_pos, hs.2 c hcfull]
          cases h1c : s1.cells c with
          | cons x xs =>
              have h2c : s2.cells c = x :: xs := by rw [← hcEq, h1c]
              constructor
              · simp [run, h1c, h2c]
              · intro s1' h1' s2' h2' hr1 _hr2
                simp [run, h1c] at hr1
          | nil =>
              have h2c : s2.cells c = [] := by rw [← hcEq, h1c]
              by_cases hmem1 : c ∈ h1
              · have hmem2 : c ∈ h2 := hmem.mp hmem1
                have hpost : Agree (C ++ footprint (Op.put c v :: rest))
                    (s1.set c [v]) (s2.set c [v]) (h1.erase c) (h2.erase c) := by
                  constructor
                  · intro d hd
                    by_cases hdc : d = c
                    · subst hdc; simp
                    · rw [Store.set_other s1 c d [v] hdc, Store.set_other s2 c d [v] hdc]
                      exact hs.1 d hd
                  · intro d hd
                    by_cases hdc : d = c
                    · subst hdc
                      rw [occ_erase_self, occ_erase_self, hs.2 d hd]
                    · rw [occ_erase_other hdc, occ_erase_other hdc]
                      exact hs.2 d hd
                have hpos := ih C (s1.set c [v]) (s2.set c [v]) (h1.erase c) (h2.erase c)
                  (agree_of_subset hpost hsub)
                constructor
                · simp only [run, h1c, h2c, hmem1, hmem2, ↓reduceIte]
                  exact hpos.1
                · intro s1' h1' s2' h2' hr1 hr2
                  simp only [run, h1c, hmem1, ↓reduceIte] at hr1
                  simp only [run, h2c, hmem2, ↓reduceIte] at hr2
                  exact agree_of_rest (Op.put c v) rest C hpost hr1 hr2
                    (hpos.2 s1' h1' s2' h2' hr1 hr2)
              · have hmem2 : ¬ c ∈ h2 := fun h => hmem1 (hmem.mpr h)
                constructor
                · simp [run, h1c, h2c, hmem1, hmem2]
                · intro s1' h1' s2' h2' hr1 _hr2
                  simp [run, h1c, hmem1] at hr1
      | call c =>
          have hcfull : c ∈ C ++ footprint (Op.call c :: rest) := by simp
          have hmem : c ∈ h1 ↔ c ∈ h2 := by
            rw [mem_iff_occ_pos, mem_iff_occ_pos, hs.2 c hcfull]
          by_cases hmem1 : c ∈ h1
          · have hmem2 : c ∈ h2 := hmem.mp hmem1
            constructor
            · simp [run, hmem1, hmem2]
            · intro s1' h1' s2' h2' hr1 _hr2
              simp [run, hmem1] at hr1
          · have hmem2 : ¬ c ∈ h2 := fun h => hmem1 (hmem.mpr h)
            have hpos := ih C s1 s2 h1 h2 (agree_of_subset hs hsub)
            constructor
            · simp only [run, hmem1, hmem2, ↓reduceIte]
              exact hpos.1
            · intro s1' h1' s2' h2' hr1 hr2
              simp only [run, hmem1, ↓reduceIte] at hr1
              simp only [run, hmem2, ↓reduceIte] at hr2
              exact agree_of_rest (Op.call c) rest C hs hr1 hr2
                (hpos.2 s1' h1' s2' h2' hr1 hr2)
      | commit c f =>
          have hcfull : c ∈ C ++ footprint (Op.commit c f :: rest) := by simp
          have hcEq : s1.cells c = s2.cells c := hs.1 c hcfull
          cases h1c : s1.cells c with
          | nil =>
              have h2c : s2.cells c = [] := by rw [← hcEq, h1c]
              constructor
              · simp [run, h1c, h2c]
              · intro s1' h1' s2' h2' hr1 _hr2
                simp [run, h1c] at hr1
          | cons x xs =>
              cases xs with
              | cons y ys =>
                  have h2c : s2.cells c = x :: y :: ys := by rw [← hcEq, h1c]
                  constructor
                  · simp [run, h1c, h2c]
                  · intro s1' h1' s2' h2' hr1 _hr2
                    simp [run, h1c] at hr1
              | nil =>
                  have h2c : s2.cells c = [x] := by rw [← hcEq, h1c]
                  cases hf : f x with
                  | none =>
                      constructor
                      · simp [run, h1c, h2c, hf]
                      · intro s1' h1' s2' h2' hr1 _hr2
                        simp [run, h1c, hf] at hr1
                  | some v' =>
                      have hpost : Agree (C ++ footprint (Op.commit c f :: rest))
                          (s1.set c [v']) (s2.set c [v']) h1 h2 := by
                        constructor
                        · intro d hd
                          by_cases hdc : d = c
                          · subst hdc; simp
                          · rw [Store.set_other s1 c d [v'] hdc, Store.set_other s2 c d [v'] hdc]
                            exact hs.1 d hd
                        · intro d hd
                          exact hs.2 d hd
                      have hpos := ih C (s1.set c [v']) (s2.set c [v']) h1 h2
                        (agree_of_subset hpost hsub)
                      constructor
                      · simp only [run, h1c, h2c, hf]
                        exact hpos.1
                      · intro s1' h1' s2' h2' hr1 hr2
                        simp only [run, h1c, hf] at hr1
                        simp only [run, h2c, hf] at hr2
                        exact agree_of_rest (Op.commit c f) rest C hpost hr1 hr2
                          (hpos.2 s1' h1' s2' h2' hr1 hr2)


theorem run_append {α : Type} (ops2 : List (Op α)) :
    ∀ (ops1 : List (Op α)) (s : Store α) (h : List CellId),
      run s h (ops1 ++ ops2) = (run s h ops1).bind (fun p => run p.1 p.2 ops2) := by
  intro ops1
  induction ops1 with
  | nil => intro s h; rfl
  | cons op rest ih =>
      intro s h
      cases op with
      | peek c =>
          cases hc : s.cells c with
          | nil => simp [run, hc]
          | cons x xs => simp only [run, hc, ↓reduceIte]; exact ih _ _
      | take c =>
          cases hc : s.cells c with
          | nil => simp [run, hc]
          | cons x xs =>
              cases xs with
              | nil => simp only [run, hc, ↓reduceIte]; exact ih _ _
              | cons y ys => simp [run, hc]
      | put c v =>
          cases hc : s.cells c with
          | cons x xs => simp [run, hc]
          | nil =>
              by_cases hmem : c ∈ h
              · simp only [run, hc, hmem, ↓reduceIte]; exact ih _ _
              · simp [run, hc, hmem]
      | call c =>
          by_cases hmem : c ∈ h
          · simp [run, hmem]
          · simp only [run, hmem, ↓reduceIte]; exact ih _ _
      | commit c f =>
          cases hc : s.cells c with
          | nil => simp [run, hc]
          | cons x xs =>
              cases xs with
              | cons y ys => simp [run, hc]
              | nil =>
                  cases hf : f x with
                  | none => simp [run, hc, hf]
                  | some v' => simp only [run, hc, hf, ↓reduceIte]; exact ih _ _

theorem run_held_subset {α : Type} :
    ∀ (ops : List (Op α)) (s : Store α) (h : List CellId) (s' : Store α) (h' : List CellId),
      run s h ops = some (s', h') → ∀ d, d ∈ h' → d ∈ h ∨ d ∈ footprint ops := by
  intro ops
  induction ops with
  | nil =>
      intro s h s' h' hr d hd
      simp [run] at hr
      obtain ⟨rfl, rfl⟩ := hr
      exact Or.inl hd
  | cons op rest ih =>
      intro s h s' h' hr d hd
      cases op with
      | peek c =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              simp only [run, hc] at hr
              rcases ih s h s' h' hr d hd with hd | hd
              · exact Or.inl hd
              · exact Or.inr (by simp [hd])
      | take c =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              cases xs with
              | nil =>
                  simp only [run, hc] at hr
                  rcases ih (s.set c []) (c :: h) s' h' hr d hd with hd | hd
                  · rcases List.mem_cons.mp hd with rfl | hd
                    · exact Or.inr (by simp)
                    · exact Or.inl hd
                  · exact Or.inr (by simp [hd])
              | cons y ys => simp [run, hc] at hr
      | put c v =>
          cases hc : s.cells c with
          | cons x xs => simp [run, hc] at hr
          | nil =>
              by_cases hmem : c ∈ h
              · simp only [run, hc, hmem, ↓reduceIte] at hr
                rcases ih (s.set c [v]) (h.erase c) s' h' hr d hd with hd | hd
                · exact Or.inl (List.mem_of_mem_erase hd)
                · exact Or.inr (by simp [hd])
              · simp [run, hc, hmem] at hr
      | call c =>
          by_cases hmem : c ∈ h
          · simp [run, hmem] at hr
          · simp only [run, hmem, ↓reduceIte] at hr
            rcases ih s h s' h' hr d hd with hd | hd
            · exact Or.inl hd
            · exact Or.inr (by simp [hd])
      | commit c f =>
          cases hc : s.cells c with
          | nil => simp [run, hc] at hr
          | cons x xs =>
              cases xs with
              | cons y ys => simp [run, hc] at hr
              | nil =>
                  cases hf : f x with
                  | none => simp [run, hc, hf] at hr
                  | some v' =>
                      simp only [run, hc, hf] at hr
                      rcases ih (s.set c [v']) h s' h' hr d hd with hd | hd
                      · exact Or.inl hd
                      · exact Or.inr (by simp [hd])

theorem FootprintDisjoint.symm {α : Type} {ops1 ops2 : List (Op α)}
    (h : FootprintDisjoint ops1 ops2) : FootprintDisjoint ops2 ops1 :=
  fun c h2 h1 => h c h1 h2

theorem agree_from_frame {α : Type} (ops1 : List (Op α)) (s : Store α) (h : List CellId)
    {sA : Store α} {hA : List CellId} (ops2 : List (Op α))
    (hS : run s h ops1 = some (sA, hA))
    (hdisj : FootprintDisjoint ops1 ops2) :
    Agree (footprint ops2) sA s hA h := by
  have f := run_frame ops1 s h sA hA hS
  exact ⟨fun d hd => f.1 d (fun hm => hdisj d hm hd),
         fun d hd => f.2 d (fun hm => hdisj d hm hd)⟩

/-- Two interleaved runs of independent traces agree on both the store and the
occurrence count of every held cell. -/
theorem interleave_agrees {α : Type} (s : Store α) (h : List CellId)
    (ops1 ops2 : List (Op α)) (hdisj : FootprintDisjoint ops1 ops2)
    {sA : Store α} {hA : List CellId} {sB : Store α} {hB : List CellId}
    (hS : run s h ops1 = some (sA, hA)) (hT : run s h ops2 = some (sB, hB))
    {sX : Store α} {hX : List CellId} {sY : Store α} {hY : List CellId}
    (hXrun : run sA hA ops2 = some (sX, hX)) (hYrun : run sB hB ops1 = some (sY, hY)) :
    sX = sY ∧ (∀ d, occ d hX = occ d hY) := by
  have hsA := agree_from_frame ops1 s h ops2 hS hdisj
  have hsB := agree_from_frame ops2 s h ops1 hT hdisj.symm
  have ra2 := run_agree ops2 [] sA s hA h (by simpa using hsA)
  have ra1 := run_agree ops1 [] sB s hB h (by simpa using hsB)
  have ag2 := ra2.2 sX hX sB hB hXrun hT
  have ag1 := ra1.2 sY hY sA hA hYrun hS
  have fS := run_frame ops1 s h sA hA hS
  have fT := run_frame ops2 s h sB hB hT
  have fX := run_frame ops2 sA hA sX hX hXrun
  have fY := run_frame ops1 sB hB sY hY hYrun
  have store : sX = sY := by
    cases sX with
    | mk cX =>
      cases sY with
      | mk cY =>
        simp only [Store.mk.injEq]
        funext d
        by_cases hd1 : d ∈ footprint ops1
        · have hd2 : d ∉ footprint ops2 := fun hm => hdisj d hd1 hm
          exact (fX.1 d hd2).trans (ag1.1 d hd1).symm
        · by_cases hd2 : d ∈ footprint ops2
          · have hd1' : d ∉ footprint ops1 := hd1
            exact (ag2.1 d hd2).trans (fY.1 d hd1').symm
          · exact ((fX.1 d hd2).trans (fS.1 d hd1)).trans
              (((fY.1 d hd1).trans (fT.1 d hd2)).symm)
  have held : ∀ d, occ d hX = occ d hY := by
    intro d
    by_cases hd1 : d ∈ footprint ops1
    · have hd2 : d ∉ footprint ops2 := fun hm => hdisj d hd1 hm
      exact (fX.2 d hd2).trans (ag1.2 d hd1).symm
    · by_cases hd2 : d ∈ footprint ops2
      · exact (ag2.2 d hd2).trans (fY.2 d hd1).symm
      · exact ((fX.2 d hd2).trans (fS.2 d hd1)).trans
          (((fY.2 d hd1).trans (fT.2 d hd2)).symm)
  exact ⟨store, held⟩

/-- Traces over disjoint cells commute on the store. -/
theorem disjoint_cells_commute {α : Type} (s : Store α) (h : List CellId)
    (ops1 ops2 : List (Op α)) (hdisj : FootprintDisjoint ops1 ops2) :
    (run s h (ops1 ++ ops2)).map Prod.fst = (run s h (ops2 ++ ops1)).map Prod.fst := by
  cases hS : run s h ops1 with
  | none =>
      cases hT : run s h ops2 with
      | none =>
          rw [run_append ops2 ops1 s h, run_append ops1 ops2 s h, hS, hT]
          simp
      | some pB =>
          obtain ⟨sB, hB⟩ := pB
          have hsB := agree_from_frame ops2 s h ops1 hT hdisj.symm
          have ra1 := run_agree ops1 [] sB s hB h (by simpa using hsB)
          have hnone : run sB hB ops1 = none := ra1.1.mpr hS
          simp only [run_append ops2 ops1 s h, run_append ops1 ops2 s h, hS, hT, hnone,
            Option.none_bind, Option.some_bind, Option.map_none, Option.map_some']
  | some pA =>
      obtain ⟨sA, hA⟩ := pA
      cases hT : run s h ops2 with
      | none =>
          have hsA := agree_from_frame ops1 s h ops2 hS hdisj
          have ra2 := run_agree ops2 [] sA s hA h (by simpa using hsA)
          have hnone : run sA hA ops2 = none := ra2.1.mpr hT
          simp only [run_append ops2 ops1 s h, run_append ops1 ops2 s h, hS, hT, hnone,
            Option.none_bind, Option.some_bind, Option.map_none, Option.map_some']
      | some pB =>
          obtain ⟨sB, hB⟩ := pB
          have hsA := agree_from_frame ops1 s h ops2 hS hdisj
          have ra2 := run_agree ops2 [] sA s hA h (by simpa using hsA)
          have hsB := agree_from_frame ops2 s h ops1 hT hdisj.symm
          have ra1 := run_agree ops1 [] sB s hB h (by simpa using hsB)
          cases hX : run sA hA ops2 with
          | none =>
              have : run s h ops2 = none := ra2.1.mp hX
              rw [hT] at this
              exact absurd this (by simp)
          | some pX =>
              obtain ⟨sX, hX'⟩ := pX
              cases hY : run sB hB ops1 with
              | none =>
                  have : run s h ops1 = none := ra1.1.mp hY
                  rw [hS] at this
                  exact absurd this (by simp)
              | some pY =>
                  obtain ⟨sY, hY'⟩ := pY
                  have hag := interleave_agrees s h ops1 ops2 hdisj hS hT hX hY
                  rw [run_append ops2 ops1 s h, run_append ops1 ops2 s h, hS, hT]
                  simp only [Option.none_bind, Option.some_bind, Option.map_none, Option.map_some']
                  rw [hX, hY]
                  simp [hag.1]

/-- When both traces are well formed from an empty held set, the two interleavings
agree exactly, including the (empty) held set. -/
theorem disjoint_cells_commute_wf {α : Type} (s : Store α)
    (ops1 ops2 : List (Op α)) (hdisj : FootprintDisjoint ops1 ops2)
    {sA : Store α} {sB : Store α}
    (hS : run s [] ops1 = some (sA, [])) (hT : run s [] ops2 = some (sB, [])) :
    run s [] (ops1 ++ ops2) = run s [] (ops2 ++ ops1) := by
  have hsA := agree_from_frame ops1 s [] ops2 hS hdisj
  have ra2 := run_agree ops2 [] sA s [] [] (by simpa using hsA)
  have hsB := agree_from_frame ops2 s [] ops1 hT hdisj.symm
  have ra1 := run_agree ops1 [] sB s [] [] (by simpa using hsB)
  cases hX : run sA [] ops2 with
  | none =>
      have : run s [] ops2 = none := ra2.1.mp hX
      rw [hT] at this
      exact absurd this (by simp)
  | some pX =>
      obtain ⟨sX, hX'⟩ := pX
      cases hY : run sB [] ops1 with
      | none =>
          have : run s [] ops1 = none := ra1.1.mp hY
          rw [hS] at this
          exact absurd this (by simp)
      | some pY =>
          obtain ⟨sY, hY'⟩ := pY
          have hag := interleave_agrees s [] ops1 ops2 hdisj hS hT hX hY
          have ag2 := ra2.2 sX hX' sB [] hX hT
          have ag1 := ra1.2 sY hY' sA [] hY hS
          have hXnil : hX' = [] := by
            apply List.eq_nil_iff_forall_not_mem.mpr
            intro d hd
            have hsub := run_held_subset ops2 sA [] sX hX' hX d hd
            rcases hsub with hsub | hsub
            · exact absurd hsub (by simp)
            · have hzero : occ d hX' = 0 := by
                rw [ag2.2 d hsub]
                rfl
              rw [mem_iff_occ_pos] at hd
              omega
          have hYnil : hY' = [] := by
            apply List.eq_nil_iff_forall_not_mem.mpr
            intro d hd
            have hsub := run_held_subset ops1 sB [] sY hY' hY d hd
            rcases hsub with hsub | hsub
            · exact absurd hsub (by simp)
            · have hzero : occ d hY' = 0 := by
                rw [ag1.2 d hsub]
                rfl
              rw [mem_iff_occ_pos] at hd
              omega
          rw [run_append ops2 ops1 s [], run_append ops1 ops2 s [], hS, hT]
          simp only [Option.none_bind, Option.some_bind, Option.map_none, Option.map_some']
          rw [hX, hY]
          simp [hag.1, hXnil, hYnil]

/-! ## Commit model (application concurrency) -/

structure World (α : Type) where
  cell : CellId → Option α

namespace World

variable {α : Type}

def set (w : World α) (c : CellId) (v : α) : World α :=
  ⟨fun x => if x = c then some v else w.cell x⟩

def commit (w : World α) (c : CellId) (f : α → Option α) : Option (World α) :=
  match w.cell c with
  | none => none
  | some v =>
      match f v with
      | none => none
      | some v' => some (w.set c v')

@[simp] theorem set_same (w : World α) (c : CellId) (v : α) :
    (w.set c v).cell c = some v := by
  simp [set]

theorem set_other (w : World α) (c d : CellId) (v : α) (h : d ≠ c) :
    (w.set c v).cell d = w.cell d := by
  simp [set, h]

theorem set_commute (w : World α) (c1 c2 : CellId) (v1 v2 : α) (h : c1 ≠ c2) :
    (w.set c1 v1).set c2 v2 = (w.set c2 v2).set c1 v1 := by
  cases w with
  | mk cell =>
      simp only [set, World.mk.injEq]
      funext x
      by_cases hx1 : x = c1
      · subst hx1
        simp [h]
      · by_cases hx2 : x = c2
        · subst hx2
          simp [hx1]
        · simp [hx1, hx2]

theorem set_set_same (w : World α) (c : CellId) (v1 v2 : α) :
    (w.set c v1).set c v2 = w.set c v2 := by
  cases w with
  | mk cell =>
      simp only [set, World.mk.injEq]
      funext x
      by_cases h : x = c
      · subst h
        simp
      · simp [h]

theorem commit_none (w : World α) (c : CellId) (f : α → Option α)
    (h : w.cell c = none) : w.commit c f = none := by
  simp [commit, h]

theorem commit_fail (w : World α) (c : CellId) (f : α → Option α) (v : α)
    (h : w.cell c = some v) (hf : f v = none) : w.commit c f = none := by
  simp [commit, h, hf]

theorem commit_some (w : World α) (c : CellId) (f : α → Option α) (v v' : α)
    (h : w.cell c = some v) (hf : f v = some v') :
    w.commit c f = some (w.set c v') := by
  simp [commit, h, hf]

/-- A commit on one cell leaves every other cell alone. -/
theorem commit_preserves_other (w : World α) (c1 c2 : CellId) (f : α → Option α)
    (h : c1 ≠ c2) {w' : World α} (hc : w.commit c1 f = some w') :
    w'.cell c2 = w.cell c2 := by
  cases hcell : w.cell c1 with
  | none => simp [commit, hcell] at hc
  | some v =>
      cases hf : f v with
      | none => simp [commit, hcell, hf] at hc
      | some v' =>
          simp [commit, hcell, hf] at hc
          rw [← hc]
          exact set_other w c1 c2 v' h.symm

/-- Commits on different cells commute: independent entities do not interact. -/
theorem commit_commute (w : World α) (c1 c2 : CellId) (f1 f2 : α → Option α)
    (h : c1 ≠ c2) :
    (w.commit c1 f1).bind (fun w' => w'.commit c2 f2)
      = (w.commit c2 f2).bind (fun w' => w'.commit c1 f1) := by
  cases h1 : w.cell c1 with
  | none =>
      cases h2 : w.cell c2 with
      | none => simp [commit, h1, h2]
      | some v2 =>
          cases hf2 : f2 v2 with
          | none => simp [commit, h1, h2, hf2]
          | some v2' =>
              have hs2 : (w.set c2 v2').cell c1 = none := by
                rw [set_other w c2 c1 v2' h]
                exact h1
              simp [commit, h1, h2, hf2, hs2]
  | some v1 =>
      cases hf1 : f1 v1 with
      | none =>
          cases h2 : w.cell c2 with
          | none => simp [commit, h1, h2, hf1]
          | some v2 =>
              cases hf2 : f2 v2 with
              | none => simp [commit, h1, h2, hf1, hf2]
              | some v2' =>
                  have hs2 : (w.set c2 v2').cell c1 = some v1 := by
                    rw [set_other w c2 c1 v2' h]
                    exact h1
                  simp [commit, h1, h2, hf1, hf2, hs2]
      | some v1' =>
          cases h2 : w.cell c2 with
          | none =>
              have hs1 : (w.set c1 v1').cell c2 = none := by
                rw [set_other w c1 c2 v1' h.symm]
                exact h2
              simp [commit, h1, h2, hf1, hs1]
          | some v2 =>
              cases hf2 : f2 v2 with
              | none =>
                  have hs1 : (w.set c1 v1').cell c2 = some v2 := by
                    rw [set_other w c1 c2 v1' h.symm]
                    exact h2
                  simp [commit, h1, h2, hf1, hf2, hs1]
              | some v2' =>
                  have hs1 : (w.set c1 v1').cell c2 = some v2 := by
                    rw [set_other w c1 c2 v1' h.symm]
                    exact h2
                  have hs2 : (w.set c2 v2').cell c1 = some v1 := by
                    rw [set_other w c2 c1 v2' h]
                    exact h1
                  simp [commit, h1, h2, hf1, hf2, hs1, hs2]
                  exact set_commute w c1 c2 v1' v2' h

/-- A second commit on the same cell sees the first commit's post-state; the
pair composes into the composed update function. -/
theorem commit_same_cell (w : World α) (c : CellId) (f1 f2 : α → Option α) :
    (w.commit c f1).bind (fun w' => w'.commit c f2)
      = w.commit c (fun v => (f1 v).bind f2) := by
  cases h : w.cell c with
  | none => simp [commit, h]
  | some v =>
      cases h1 : f1 v with
      | none => simp [commit, h, h1]
      | some v1 =>
          cases h2 : f2 v1 with
          | none => simp [commit, h, h1, h2]
          | some v2 => simp [commit, h, h1, h2, set_set_same]

/-- Two commits on the same cell cannot both read the same pre-state: the
first commit's post-state is the second's pre-state. -/
theorem same_cell_serializes (w : World α) (c : CellId) (f1 f2 : α → Option α)
    (v v1 v2 : α) (h : w.cell c = some v)
    (hf1 : f1 v = some v1) (hf2 : f2 v1 = some v2) :
    (w.commit c f1).bind (fun w' => w'.commit c f2)
      = some (w.set c v2) := by
  simp [commit_same_cell, commit, h, hf1, hf2, set_set_same]

end World

end RGen
