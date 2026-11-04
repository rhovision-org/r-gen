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
