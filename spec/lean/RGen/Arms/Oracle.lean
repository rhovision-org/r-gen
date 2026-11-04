import RGen.Arms.Basic
import RGen.Model.Oracle

/-!
# Oracle arm pairs

Decide and expire both require `open`; whichever first leaves a terminal state, so they
are two-way exclusive. Execute is one-shot: the first leaves `executing`, the second
requires `decided` and refuses. Evidence is ordered before decide; decide-first refuses
evidence.
-/

namespace RGen

structure OracleDecideArgs where
  adjudicator : Id
  proof : ProofData
  decision : VPDecision

def oracleDecide (s : OracleState) (a : OracleDecideArgs) : Option OracleState :=
  s.decide a.adjudicator a.proof a.decision

def oracleExpire (s : OracleState) (h : Height) : Option OracleState :=
  s.expire h

def oracleExecute (s : OracleState) (caller : Id) : Option OracleState :=
  s.execute caller

def oracleFinish (s : OracleState) : Option OracleState :=
  s.finishExecute

def oracleClose (s : OracleState) : Option OracleState :=
  s.close

def oracleEvidence (s : OracleState) (ref : Id) : Option OracleState :=
  s.addEvidence ref

def oracleRollback (s : OracleState) : Option OracleState :=
  s.rollbackExecute

theorem oracle_decide_decide_never_after {a : OracleDecideArgs} :
    NeverAfter (fun s => oracleDecide s a) (fun s => oracleDecide s a) := by
  intro s s1 h
  exact OracleState.decide_once h

theorem oracle_decide_expire_never_after {a : OracleDecideArgs} {hgt : Height} :
    NeverAfter (fun s => oracleDecide s a) (fun s => oracleExpire s hgt) := by
  intro s s1 hd
  have hs := OracleState.decide_sets_status hd
  simp [oracleExpire, OracleState.expire, hs]

theorem oracle_expire_decide_never_after {hgt : Height} {a : OracleDecideArgs} :
    NeverAfter (fun s => oracleExpire s hgt) (fun s => oracleDecide s a) := by
  intro s s1 he
  have hs := OracleState.expire_sets_status he
  simp [oracleDecide, OracleState.decide, hs]

theorem oracle_decide_expire_two_way {a : OracleDecideArgs} {hgt : Height} :
    TwoWayExclusive (fun s => oracleDecide s a) (fun s => oracleExpire s hgt) :=
  ⟨oracle_decide_expire_never_after, oracle_expire_decide_never_after⟩

theorem oracle_execute_execute_never_after {caller caller' : Id} :
    NeverAfter (fun s => oracleExecute s caller) (fun s => oracleExecute s caller') := by
  intro s s1 h
  exact OracleState.execute_once h

theorem oracle_finish_execute_never_after {caller : Id} :
    NeverAfter (fun s => oracleFinish s) (fun s => oracleExecute s caller) := by
  intro s s1 h
  exact OracleState.finish_execute_once h

theorem oracle_close_close_never_after :
    NeverAfter (fun s => oracleClose s) (fun s => oracleClose s) := by
  intro s s1 h
  exact OracleState.close_once h

theorem oracle_decide_evidence_never_after {a : OracleDecideArgs} {ref : Id} :
    NeverAfter (fun s => oracleDecide s a) (fun s => oracleEvidence s ref) := by
  intro s s1 hd
  have hs := OracleState.decide_sets_status hd
  simp [oracleEvidence, OracleState.addEvidence, hs]

theorem oracle_expire_execute_never_after {hgt : Height} {caller : Id} :
    NeverAfter (fun s => oracleExpire s hgt) (fun s => oracleExecute s caller) := by
  intro s s1 he
  have hs := OracleState.expire_sets_status he
  simp [oracleExecute, OracleState.execute, hs]

/-- A failed execution can be rolled back; the retry is a new generation. -/
theorem oracle_rollback_execute_possible {s s1 s2 : OracleState} {caller : Id}
    (_hr : s.rollbackExecute = some s1) (he : s1.execute caller = some s2) :
    s2.status = OracleStatus.executing :=
  OracleState.execute_sets_status he

end RGen
