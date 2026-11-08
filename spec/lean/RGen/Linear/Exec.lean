import RGen.Linear.Versioned

/-!
# Execution semantics over versioned cells

An `Event` is one arm transition on one cell: it names the cell, the generation the arm
observed, and the pure step (which returns `none` when its guard fails). `apply` either
accepts (value changes), rejects (value re-posted unchanged), or is stale (the generation
no longer matches). Both accepted and rejected events advance the generation.

`Run` is the proof-facing semantics; `runExec` is the executable fold. The central result
is `runExec_no_same_expected`: in any run, no two events on the same cell share an
expected generation. That is the model-level statement that a same-generation race is not
representable.
-/

namespace RGen

structure Event (α : Type) where
  cell : CellId
  expected : Nat
  step : α → Option α

namespace Event

variable {α : Type}

def apply (e : Event α) (w : VWorld α) : CommitOutcome α :=
  match w.cell e.cell with
  | none => .stale
  | some vc =>
      if vc.gen = e.expected then
        match e.step vc.val with
        | none => .rejected (w.set e.cell vc.val (e.expected + 1))
        | some v' => .accepted (w.set e.cell v' (e.expected + 1))
      else .stale

/-- The guard an event presents to `VWorld.commit`. -/
def guard (e : Event α) : α → Bool := fun s => (e.step s).isSome

/-- The effect of an accepted event; the value is ignored when the guard is false. -/
def effect (e : Event α) : α → α := fun s => (e.step s).getD s

/-- `Event.apply` is the versioned commit with the event's guard and effect. -/
theorem apply_eq_commit (e : Event α) (w : VWorld α) :
    e.apply w = w.commit e.cell e.expected e.guard e.effect := by
  unfold apply VWorld.commit guard effect
  cases hc : w.cell e.cell with
  | none => rfl
  | some vc =>
      by_cases hgen : vc.gen = e.expected
      · cases hs : e.step vc.val <;> simp [hc, hgen, hs]
      · simp [hc, hgen]

/-- Apply an event after another outcome; a stale outcome stays stale. -/
def applyThen (e : Event α) (o : CommitOutcome α) : CommitOutcome α :=
  match o with
  | .stale => .stale
  | .rejected w => e.apply w
  | .accepted w => e.apply w

theorem applyThen_eq_commitThen (e : Event α) (o : CommitOutcome α) :
    e.applyThen o = VWorld.commitThen o e.cell e.expected e.guard e.effect := by
  cases o <;> simp [applyThen, VWorld.commitThen, apply_eq_commit]

/-- Events on distinct cells reach the same final world in either order. -/
theorem apply_commute_distinct {e1 e2 : Event α} (h : e1.cell ≠ e2.cell)
    (w : VWorld α) :
    (e2.applyThen (e1.apply w)).world = (e1.applyThen (e2.apply w)).world := by
  rw [applyThen_eq_commitThen, applyThen_eq_commitThen]
  simp only [apply_eq_commit]
  exact VWorld.commit_commute h e1.expected e2.expected e1.guard e2.guard e1.effect e2.effect

def IsAccepted (e : Event α) (w : VWorld α) (w' : VWorld α) : Prop :=
  e.apply w = .accepted w'

def IsApplied (e : Event α) (w : VWorld α) (w' : VWorld α) : Prop :=
  e.apply w = .accepted w' ∨ e.apply w = .rejected w'

theorem apply_other {e : Event α} {w : VWorld α} {w' : VWorld α} {d : CellId}
    (h : (e.apply w).world = some w') (hd : d ≠ e.cell) : w'.cell d = w.cell d := by
  cases hc : w.cell e.cell with
  | none => simp [apply, hc, CommitOutcome.world] at h
  | some vc =>
      by_cases hgen : vc.gen = e.expected
      · cases hs : e.step vc.val with
        | none =>
            simp [apply, hc, hgen, hs, CommitOutcome.world] at h
            rcases h with rfl
            exact VWorld.set_other w e.cell d vc.val (e.expected + 1) hd
        | some v' =>
            simp [apply, hc, hgen, hs, CommitOutcome.world] at h
            rcases h with rfl
            exact VWorld.set_other w e.cell d v' (e.expected + 1) hd
      · simp [apply, hc, hgen, CommitOutcome.world] at h

end Event

inductive Run {α : Type} : VWorld α → List (Event α) → VWorld α → Prop where
  | nil (w : VWorld α) : Run w [] w
  | cons {w w1 es w'} (e : Event α) :
      (e.apply w).world = some w1 → Run w1 es w' → Run w (e :: es) w'

def runExec {α : Type} (w : VWorld α) : List (Event α) → Option (VWorld α)
  | [] => some w
  | e :: es =>
      match e.apply w with
      | .stale => none
      | .rejected w' => runExec w' es
      | .accepted w' => runExec w' es

/-! ### Soundness and completeness -/

theorem runExec_sound {α : Type} {w : VWorld α} :
    ∀ {es : List (Event α)} {w' : VWorld α}, runExec w es = some w' → Run w es w'
  | [], w', h => by
      simp [runExec] at h
      subst h
      exact Run.nil w
  | e :: es, w', h => by
      unfold runExec at h
      split at h
      · simp at h
      · rename_i w1 happlied
        exact Run.cons e (by rw [happlied]; rfl) (runExec_sound h)
      · rename_i w1 happlied
        exact Run.cons e (by rw [happlied]; rfl) (runExec_sound h)

theorem runExec_complete {α : Type} {w : VWorld α} {es : List (Event α)} {w' : VWorld α}
    (h : Run w es w') : runExec w es = some w' := by
  induction es generalizing w w' with
  | nil =>
      cases h with
      | nil => rfl
  | cons e es ih =>
      cases h with
      | cons _ happlied hr =>
          unfold runExec
          cases hcase : e.apply w with
          | stale =>
              simp [hcase, CommitOutcome.world] at happlied
          | rejected w1 =>
              simp [hcase, CommitOutcome.world] at happlied
              rcases happlied with rfl
              exact ih hr
          | accepted w1 =>
              simp [hcase, CommitOutcome.world] at happlied
              rcases happlied with rfl
              exact ih hr

theorem runExec_deterministic {α : Type} {w : VWorld α} {es : List (Event α)}
    {w1 w2 : VWorld α} (h1 : runExec w es = some w1) (h2 : runExec w es = some w2) :
    w1 = w2 := by
  rw [runExec_complete (runExec_sound h1)] at h2
  exact Option.some.inj h2

theorem run_deterministic {α : Type} {w : VWorld α} {es : List (Event α)}
    {w1 w2 : VWorld α} (h1 : Run w es w1) (h2 : Run w es w2) : w1 = w2 := by
  have e1 := runExec_complete h1
  have e2 := runExec_complete h2
  rw [e1] at e2
  exact Option.some.inj e2

/-! ### Framing -/

theorem runExec_frame {α : Type} {w : VWorld α} :
    ∀ {es : List (Event α)} {w' : VWorld α}, runExec w es = some w' →
      ∀ d, d ∉ es.map Event.cell → w'.cell d = w.cell d
  | [], w', h, d, _ => by
      simp [runExec] at h
      rw [h]
  | e :: es, w', h, d, hd => by
      unfold runExec at h
      have hde : d ≠ e.cell := by
        intro heq
        exact hd (by simp [heq])
      have hdrest : d ∉ es.map Event.cell := by
        intro hmem
        exact hd (by simp [hmem])
      split at h
      · simp at h
      · rename_i w1 happlied
        have hw : (e.apply w).world = some w1 := by rw [happlied]; rfl
        exact (runExec_frame h d hdrest).trans (Event.apply_other hw hde)
      · rename_i w1 happlied
        have hw : (e.apply w).world = some w1 := by rw [happlied]; rfl
        exact (runExec_frame h d hdrest).trans (Event.apply_other hw hde)

/-! ### Per-cell projection and no-same-generation -/

def runCell {α : Type} (c : CellId) : Option (VCell α) → List (Event α) →
    Option (Option (VCell α))
  | vc, [] => some vc
  | vc, e :: es =>
      if e.cell = c then
        match vc with
        | none => none
        | some v =>
            if v.gen = e.expected then
              match e.step v.val with
              | none => runCell c (some ⟨v.val, e.expected + 1⟩) es
              | some v' => runCell c (some ⟨v', e.expected + 1⟩) es
            else none
      else runCell c vc es

theorem runCell_apply {α : Type} {e : Event α} {w : VWorld α} {w1 : VWorld α}
    (h : (e.apply w).world = some w1) (c : CellId) (es : List (Event α)) :
    runCell c (w.cell c) (e :: es) = runCell c (w1.cell c) es := by
  cases hc : w.cell e.cell with
  | none => simp [Event.apply, hc, CommitOutcome.world] at h
  | some vc =>
      by_cases hgen : vc.gen = e.expected
      · cases hs : e.step vc.val with
        | none =>
            simp [Event.apply, hc, hgen, hs, CommitOutcome.world] at h
            rcases h with rfl
            by_cases hec : e.cell = c
            · subst hec
              simp [runCell, hc, hgen, hs]
            · have hce : c ≠ e.cell := fun h => hec h.symm
              have hother : (w.set e.cell vc.val (e.expected + 1)).cell c = w.cell c :=
                VWorld.set_other w e.cell c vc.val (e.expected + 1) hce
              rw [hother]
              simp [runCell, hec]
        | some v' =>
            simp [Event.apply, hc, hgen, hs, CommitOutcome.world] at h
            rcases h with rfl
            by_cases hec : e.cell = c
            · subst hec
              simp [runCell, hc, hgen, hs]
            · have hce : c ≠ e.cell := fun h => hec h.symm
              have hother : (w.set e.cell v' (e.expected + 1)).cell c = w.cell c :=
                VWorld.set_other w e.cell c v' (e.expected + 1) hce
              rw [hother]
              simp [runCell, hec]
      · simp [Event.apply, hc, hgen, CommitOutcome.world] at h

theorem runExec_projection {α : Type} {w : VWorld α} {es : List (Event α)}
    {w' : VWorld α} (h : runExec w es = some w') (c : CellId) :
    runCell c (w.cell c) es = some (w'.cell c) := by
  induction es generalizing w w' with
  | nil =>
      simp [runExec] at h
      subst h
      rfl
  | cons e es ih =>
      unfold runExec at h
      split at h
      · simp at h
      · rename_i w1 happlied
        have hw : (e.apply w).world = some w1 := by rw [happlied]; rfl
        rw [runCell_apply hw c es]
        exact ih h
      · rename_i w1 happlied
        have hw : (e.apply w).world = some w1 := by rw [happlied]; rfl
        rw [runCell_apply hw c es]
        exact ih h

def AppliedExpecteds {α : Type} (c : CellId) : Nat → List (Event α) → Prop
  | _, [] => True
  | n, e :: es =>
      if e.cell = c then e.expected = n ∧ AppliedExpecteds c (n + 1) es
      else AppliedExpecteds c n es

theorem runCell_applied {α : Type} {c : CellId} {vc : Option (VCell α)}
    {es : List (Event α)} {vc' : Option (VCell α)}
    (h : runCell c vc es = some vc') {n v} (hv : vc = some ⟨v, n⟩) :
    AppliedExpecteds c n es := by
  induction es generalizing vc n v with
  | nil => trivial
  | cons e es ih =>
      unfold runCell at h
      by_cases hec : e.cell = c
      · simp only [hec, if_true] at h
        rw [hv] at h
        by_cases hgen : (⟨v, n⟩ : VCell α).gen = e.expected
        · have hn : n = e.expected := hgen
          cases hs : e.step v with
          | none =>
              simp only [hn, hs, ↓reduceIte] at h
              have ih' := ih h rfl
              rw [← hn] at ih'
              simp only [AppliedExpecteds]
              rw [if_pos hec]
              exact ⟨hn.symm, ih'⟩
          | some v' =>
              simp only [hn, hs, ↓reduceIte] at h
              have ih' := ih h rfl
              rw [← hn] at ih'
              simp only [AppliedExpecteds]
              rw [if_pos hec]
              exact ⟨hn.symm, ih'⟩
        · simp [hgen] at h
      · simp only [hec, if_false] at h
        simpa only [AppliedExpecteds, hec, if_false] using ih h hv

def NoTwoSameExpected {α : Type} (c : CellId) : List (Event α) → Prop
  | [] => True
  | e :: es =>
      (e.cell = c → ∀ e' ∈ es, e'.cell = c → e'.expected ≠ e.expected) ∧
      NoTwoSameExpected c es

theorem appliedExpecteds_ge {α : Type} {c : CellId} {es : List (Event α)} {n : Nat}
    (h : AppliedExpecteds c n es) :
    ∀ e ∈ es, e.cell = c → n ≤ e.expected := by
  induction es generalizing n with
  | nil => simp
  | cons e es ih =>
      intro e0 hmem hc
      simp only [AppliedExpecteds] at h
      by_cases hec : e.cell = c
      · simp only [hec, if_true] at h
        rcases h with ⟨he, hrest⟩
        rcases List.mem_cons.mp hmem with rfl | hmem'
        · rw [he]
          omega
        · have := ih hrest e0 hmem' hc
          omega
      · simp [AppliedExpecteds, hec] at h
        rcases List.mem_cons.mp hmem with rfl | hmem'
        · exact absurd hc hec
        · have := ih h e0 hmem' hc
          omega

theorem appliedExpecteds_no_two {α : Type} {c : CellId} {es : List (Event α)} {n : Nat}
    (h : AppliedExpecteds c n es) : NoTwoSameExpected c es := by
  induction es generalizing n with
  | nil => trivial
  | cons e es ih =>
      simp only [NoTwoSameExpected]
      constructor
      · intro hec e' hmem hc' heq
        simp only [AppliedExpecteds] at h
        by_cases hec2 : e.cell = c
        · simp only [hec2, if_true] at h
          rcases h with ⟨he, hrest⟩
          have hge := appliedExpecteds_ge hrest e' hmem hc'
          rw [he] at heq
          omega
        · exact absurd hec hec2
      · simp only [AppliedExpecteds] at h
        by_cases hec2 : e.cell = c
        · simp only [hec2, if_true] at h
          exact ih h.2
        · simp [AppliedExpecteds, hec2] at h
          exact ih h

theorem runCell_none_no_events {α : Type} {c : CellId} {es : List (Event α)}
    {vc' : Option (VCell α)} (h : runCell c none es = some vc') :
    ∀ e ∈ es, e.cell ≠ c := by
  induction es with
  | nil => simp
  | cons e es ih =>
      intro e0 hmem
      unfold runCell at h
      by_cases hec : e.cell = c
      · simp [hec] at h
      · simp only [hec, if_false] at h
        rcases List.mem_cons.mp hmem with rfl | hmem'
        · exact hec
        · exact ih h e0 hmem'

theorem no_same_cell_events_no_two {α : Type} {c : CellId} {es : List (Event α)}
    (h : ∀ e ∈ es, e.cell ≠ c) : NoTwoSameExpected c es := by
  induction es with
  | nil => trivial
  | cons e es ih =>
      simp only [NoTwoSameExpected]
      constructor
      · intro hec
        exact absurd hec (h e (by simp))
      · exact ih (fun e' hm => h e' (by simp [hm]))

/-- In every run, no two events on one cell share an expected generation. -/
theorem runExec_no_same_expected {α : Type} {w : VWorld α} {es : List (Event α)}
    {w' : VWorld α} (h : runExec w es = some w') (c : CellId) :
    NoTwoSameExpected c es := by
  have hc := runExec_projection h c
  cases hvc : w.cell c with
  | none =>
      rw [hvc] at hc
      exact no_same_cell_events_no_two (runCell_none_no_events hc)
  | some vc =>
      have hv : w.cell c = some ⟨vc.val, vc.gen⟩ := by rw [hvc]
      exact appliedExpecteds_no_two (runCell_applied hc hv)

end RGen

namespace RGen

/-- Executing a concatenated trace is executing the first trace and then the second. -/
theorem runExec_append {α : Type} (w : VWorld α) (es1 es2 : List (Event α)) :
    runExec w (es1 ++ es2) =
      match runExec w es1 with
      | none => none
      | some w1 => runExec w1 es2 := by
  induction es1 generalizing w with
  | nil => simp [runExec]
  | cons e es ih =>
      simp only [List.cons_append]
      cases h : e.apply w with
      | stale => simp [runExec, h]
      | rejected w1 =>
          simp only [runExec, h]
          exact ih w1
      | accepted w1 =>
          simp only [runExec, h]
          exact ih w1

end RGen

namespace RGen

/-- An accepted or rejected event never changes a different cell (no lost update). -/
theorem runExec_no_lost_update {α : Type} {w : VWorld α} {es : List (Event α)}
    {w' : VWorld α} (h : runExec w es = some w') (d : CellId)
    (hd : d ∉ es.map Event.cell) : w'.cell d = w.cell d :=
  runExec_frame h d hd

/-- One accepted event per (cell, expected generation). -/
theorem runExec_unique_accepted_per_generation {α : Type} {w : VWorld α}
    {es : List (Event α)} {w' : VWorld α} (h : runExec w es = some w') (c : CellId) :
    NoTwoSameExpected c es :=
  runExec_no_same_expected h c

end RGen

namespace RGen

/-! ### Independence of disjoint traces -/

/-- Two event lists act on disjoint sets of cells. -/
def DisjointEvents {α : Type} (es1 es2 : List (Event α)) : Prop :=
  ∀ e1 ∈ es1, ∀ e2 ∈ es2, e1.cell ≠ e2.cell

theorem runCell_no_cell {α : Type} {c : CellId} {vc : Option (VCell α)}
    {es : List (Event α)} (h : ∀ e ∈ es, e.cell ≠ c) :
    runCell c vc es = some vc := by
  induction es generalizing vc with
  | nil => rfl
  | cons e es ih =>
      have he : e.cell ≠ c := h e (by simp)
      simp only [runCell, if_neg he]
      exact ih (fun e' hm => h e' (by simp [hm]))

theorem runCell_append_of_skip_left {α : Type} {c : CellId} {vc : Option (VCell α)}
    {es1 es2 : List (Event α)} (h : ∀ e ∈ es1, e.cell ≠ c) :
    runCell c vc (es1 ++ es2) = runCell c vc es2 := by
  induction es1 generalizing vc with
  | nil => simp
  | cons e es ih =>
      have he : e.cell ≠ c := h e (by simp)
      rw [List.cons_append]
      simp only [runCell, if_neg he]
      exact ih (fun e' hm => h e' (by simp [hm]))

theorem runCell_append_of_skip_right {α : Type} {c : CellId} {vc : Option (VCell α)}
    {es1 es2 : List (Event α)} (h : ∀ e ∈ es2, e.cell ≠ c) :
    runCell c vc (es1 ++ es2) = runCell c vc es1 := by
  induction es1 generalizing vc with
  | nil =>
      simp only [List.nil_append]
      exact runCell_no_cell h
  | cons e es ih =>
      rw [List.cons_append]
      by_cases hec : e.cell = c
      · cases vc with
        | none => simp [runCell, hec]
        | some v =>
            by_cases hgen : v.gen = e.expected
            · cases hs : e.step v.val <;> simp [runCell, hec, hgen, hs, ih]
            · simp [runCell, hec, hgen, ih]
      · simp [runCell, hec, ih]

end RGen

namespace RGen

/-- A run succeeds exactly when every cell's projection succeeds. -/
theorem runExec_some_iff_cells {α : Type} {w : VWorld α} {es : List (Event α)}
    {w' : VWorld α} :
    runExec w es = some w' ↔ ∀ c, runCell c (w.cell c) es = some (w'.cell c) := by
  constructor
  · intro h c
    exact runExec_projection h c
  · intro h
    induction es generalizing w with
    | nil =>
        have hw : w = w' := by
          cases w with
          | mk wc =>
            cases w' with
            | mk wc' =>
              simp only [VWorld.mk.injEq]
              funext c
              have hc := h c
              simpa [runCell] using hc
        subst hw
        rfl
    | cons e es ih =>
        have hc := h e.cell
        cases hcell : w.cell e.cell with
        | none => simp [runCell, hcell] at hc
        | some vc =>
            by_cases hgen : vc.gen = e.expected
            · cases hs : e.step vc.val with
              | none =>
                  let w1 := w.set e.cell vc.val (e.expected + 1)
                  have htail : ∀ c, runCell c (w1.cell c) es = some (w'.cell c) := by
                    intro c
                    by_cases hce : c = e.cell
                    · subst hce
                      simpa [runCell, hcell, hgen, hs, w1] using h e.cell
                    · have hother : w1.cell c = w.cell c :=
                        VWorld.set_other w e.cell c vc.val (e.expected + 1) hce
                      rw [hother]
                      have hne : e.cell ≠ c := fun h' => hce h'.symm
                      simpa [runCell, hne] using h c
                  have hrun := ih htail
                  simp [runExec, Event.apply, hcell, hgen, hs, w1, hrun]
              | some v' =>
                  let w1 := w.set e.cell v' (e.expected + 1)
                  have htail : ∀ c, runCell c (w1.cell c) es = some (w'.cell c) := by
                    intro c
                    by_cases hce : c = e.cell
                    · subst hce
                      simpa [runCell, hcell, hgen, hs, w1] using h e.cell
                    · have hother : w1.cell c = w.cell c :=
                        VWorld.set_other w e.cell c v' (e.expected + 1) hce
                      rw [hother]
                      have hne : e.cell ≠ c := fun h' => hce h'.symm
                      simpa [runCell, hne] using h c
                  have hrun := ih htail
                  simp [runExec, Event.apply, hcell, hgen, hs, w1, hrun]
            · simp [runCell, hcell, hgen] at hc

end RGen

namespace RGen

/-- A run fails exactly when some cell's projection fails. -/
theorem runExec_none_iff_cells {α : Type} {w : VWorld α} {es : List (Event α)} :
    runExec w es = none ↔ ∃ c, runCell c (w.cell c) es = none := by
  constructor
  · intro h
    by_cases hexists : ∃ c, runCell c (w.cell c) es = none
    · exact hexists
    · exfalso
      have hex : ∀ c, ∃ vc, runCell c (w.cell c) es = some vc := by
        intro c
        cases hcell : runCell c (w.cell c) es with
        | none => exact False.elim (hexists ⟨c, hcell⟩)
        | some vc => exact ⟨vc, rfl⟩
      let w' : VWorld α := ⟨fun c => Classical.choose (hex c)⟩
      have hv : ∀ c, runCell c (w.cell c) es = some (w'.cell c) := by
        intro c
        simpa [w'] using Classical.choose_spec (hex c)
      have hsome : runExec w es = some w' := by
        rw [runExec_some_iff_cells]
        exact hv
      rw [h] at hsome
      simp at hsome
  · intro hc
    obtain ⟨c, hc⟩ := hc
    by_cases hsome : runExec w es = none
    · exact hsome
    · exfalso
      cases hrun : runExec w es with
      | none => exact hsome hrun
      | some w' =>
          have hcell := (runExec_some_iff_cells).mp hrun c
          rw [hc] at hcell
          simp at hcell

/-- Traces on disjoint cells commute: the interleaving order does not change the outcome. -/
theorem runExec_commute_disjoint {α : Type} (w : VWorld α) (es1 es2 : List (Event α))
    (hdisj : DisjointEvents es1 es2) :
    runExec w (es1 ++ es2) = runExec w (es2 ++ es1) := by
  cases h12 : runExec w (es1 ++ es2) with
  | none =>
      rw [runExec_none_iff_cells] at h12
      obtain ⟨c, hc⟩ := h12
      symm
      rw [runExec_none_iff_cells]
      refine ⟨c, ?_⟩
      by_cases h1 : ∃ e ∈ es1, e.cell = c
      · obtain ⟨e, he, hec⟩ := h1
        have hskip : ∀ e' ∈ es2, e'.cell ≠ c := by
          intro e' he' hc'
          exact hdisj e he e' he' (hec.trans hc'.symm)
        rw [runCell_append_of_skip_right (es1 := es1) (es2 := es2) hskip] at hc
        rw [runCell_append_of_skip_left (es1 := es2) (es2 := es1) hskip]
        exact hc
      · have hskip1 : ∀ e ∈ es1, e.cell ≠ c := by
          intro e he hc'
          exact h1 ⟨e, he, hc'⟩
        by_cases h2 : ∃ e ∈ es2, e.cell = c
        · rw [runCell_append_of_skip_left (es1 := es1) (es2 := es2) hskip1] at hc
          rw [runCell_append_of_skip_right (es1 := es2) (es2 := es1) hskip1]
          exact hc
        · have hskip2 : ∀ e ∈ es2, e.cell ≠ c := by
            intro e he hc'
            exact h2 ⟨e, he, hc'⟩
          rw [runCell_append_of_skip_left (es1 := es1) (es2 := es2) hskip1] at hc
          rw [runCell_no_cell hskip2] at hc
          simp at hc
  | some w12 =>
      rw [runExec_some_iff_cells] at h12
      symm
      rw [runExec_some_iff_cells]
      intro c
      by_cases h1 : ∃ e ∈ es1, e.cell = c
      · obtain ⟨e, he, hec⟩ := h1
        have hskip : ∀ e' ∈ es2, e'.cell ≠ c := by
          intro e' he' hc'
          exact hdisj e he e' he' (hec.trans hc'.symm)
        have hc := h12 c
        rw [runCell_append_of_skip_right (es1 := es1) (es2 := es2) hskip] at hc
        rw [runCell_append_of_skip_left (es1 := es2) (es2 := es1) hskip]
        exact hc
      · have hskip1 : ∀ e ∈ es1, e.cell ≠ c := by
          intro e he hc'
          exact h1 ⟨e, he, hc'⟩
        by_cases h2 : ∃ e ∈ es2, e.cell = c
        · have hc := h12 c
          rw [runCell_append_of_skip_left (es1 := es1) (es2 := es2) hskip1] at hc
          rw [runCell_append_of_skip_right (es1 := es2) (es2 := es1) hskip1]
          exact hc
        · have hskip2 : ∀ e ∈ es2, e.cell ≠ c := by
            intro e he hc'
            exact h2 ⟨e, he, hc'⟩
          have hboth : runCell c (w.cell c) (es1 ++ es2) = some (w.cell c) := by
            rw [runCell_append_of_skip_left (es1 := es1) (es2 := es2) hskip1]
            rw [runCell_no_cell hskip2]
          have hboth2 : runCell c (w.cell c) (es2 ++ es1) = some (w.cell c) := by
            rw [runCell_append_of_skip_left (es1 := es2) (es2 := es1) hskip2]
            rw [runCell_no_cell hskip1]
          rw [hboth2]
          have hc := h12 c
          rw [hboth] at hc
          exact hc

end RGen
