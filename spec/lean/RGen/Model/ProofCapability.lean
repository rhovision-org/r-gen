import RGen.Basic

/-!
# Private proof capabilities

The deployed `prove`, `proveValidated` and `proveApproved` arms send
`bundle+{*Proof}` on a caller-supplied private channel and return `(true, Nil)`.
The proof is never inserted into the registry. This module models that protocol:

* `issue` creates a capability with a consumer and `published = false`;
* `take` requires the unused state and the named consumer;
* `reserve`/`release`/`consume` provide the two-phase nest discipline;
* no transition publishes the capability.

The limit is explicit: possession of the private channel is not modeled. The
consumer check and the absent publication are the model-level evidence that a
third party with only the public registry cannot take the proof.
-/

namespace RGen

inductive CapState where
  | unused
  | reserved (holder : Id)
  | used
  deriving DecidableEq, Repr

structure ProofCap (α : Type) where
  owner : Id
  consumer : Option Id
  payload : α
  published : Bool
  state : CapState

namespace ProofCap

variable {α : Type}

def issue (owner : Id) (consumer : Option Id) (payload : α) : ProofCap α :=
  ⟨owner, consumer, payload, false, .unused⟩

def allowed (p : ProofCap α) (caller : Id) : Bool :=
  match p.consumer with
  | none => true
  | some c => caller = c

/-- Take the payload once, if the caller is the named consumer. -/
def take (p : ProofCap α) (caller : Id) : Option (α × ProofCap α) :=
  match p.state with
  | .unused =>
      if p.allowed caller then
        some (p.payload, { p with state := .used })
      else none
  | _ => none

/-- Read the payload without consuming it. -/
def peek (p : ProofCap α) : α := p.payload

/-- Reserve the unused capability for a nest attempt. -/
def reserve (p : ProofCap α) (caller : Id) : Option (ProofCap α) :=
  match p.state with
  | .unused =>
      if p.allowed caller then some { p with state := .reserved caller } else none
  | _ => none

/-- Release a reservation made by the same caller. -/
def release (p : ProofCap α) (caller : Id) : Option (ProofCap α) :=
  match p.state with
  | .reserved holder => if holder = caller then some { p with state := .unused } else none
  | _ => none

/-- Consume a reservation made by the same caller. -/
def consume (p : ProofCap α) (caller : Id) : Option (ProofCap α) :=
  match p.state with
  | .reserved holder => if holder = caller then some { p with state := .used } else none
  | _ => none

theorem take_requires_consumer (p : ProofCap α) (caller c : Id)
    (hc : p.consumer = some c) (hne : caller ≠ c) : p.take caller = none := by
  unfold take
  split <;> simp [allowed, hc, hne]

theorem third_party_cannot_take (p : ProofCap α) (caller c : Id)
    (hc : p.consumer = some c) (hne : caller ≠ c) : p.take caller = none :=
  take_requires_consumer p caller c hc hne

theorem take_once {p : ProofCap α} {caller : Id} {d : α} {p' : ProofCap α}
    (h : p.take caller = some (d, p')) : p'.take caller = none := by
  unfold take at h
  split at h
  · split at h
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      rcases h with ⟨rfl, rfl⟩
      simp [take]
    · simp at h
  · simp at h

theorem take_marks_used {p : ProofCap α} {caller : Id} {d : α} {p' : ProofCap α}
    (h : p.take caller = some (d, p')) : p'.state = .used := by
  unfold take at h
  split at h
  · split at h
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      rcases h with ⟨rfl, rfl⟩
      rfl
    · simp at h
  · simp at h

theorem take_preserves_payload {p : ProofCap α} {caller : Id} {d : α} {p' : ProofCap α}
    (h : p.take caller = some (d, p')) : d = p.payload := by
  unfold take at h
  split at h
  · split at h
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      rcases h with ⟨rfl, rfl⟩
      rfl
    · simp at h
  · simp at h

theorem reserve_release_restores {p p' p'' : ProofCap α} {caller : Id}
    (h1 : p.reserve caller = some p') (h2 : p'.release caller = some p'') :
    p''.state = .unused ∧ p''.payload = p.payload := by
  unfold reserve at h1
  split at h1
  · split at h1
    · simp only [Option.some.injEq] at h1
      rw [← h1] at h2
      unfold release at h2
      simp at h2
      rcases h2 with rfl
      exact ⟨rfl, rfl⟩
    · simp at h1
  · simp at h1

theorem reserve_consume_once {p p' : ProofCap α} {caller : Id}
    (h : p.consume caller = some p') : p'.consume caller = none := by
  unfold consume at h ⊢
  split at h
  · split at h
    · simp only [Option.some.injEq] at h
      rw [← h]
    · simp at h
  · simp at h

theorem issue_not_published (owner : Id) (consumer : Option Id) (payload : α) :
    (issue owner consumer payload).published = false := rfl

theorem take_not_published {p : ProofCap α} {caller : Id} {d : α} {p' : ProofCap α}
    (h : p.take caller = some (d, p')) : p'.published = p.published := by
  unfold take at h
  split at h
  · split at h
    · simp only [Option.some.injEq, Prod.mk.injEq] at h
      rcases h with ⟨rfl, rfl⟩
      rfl
    · simp at h
  · simp at h

/-- Without the named consumer, no take transition exists. -/
theorem private_capability_no_bearer_dos (p : ProofCap α) (caller c : Id)
    (hc : p.consumer = some c) (hne : caller ≠ c) : p.take caller = none :=
  third_party_cannot_take p caller c hc hne

end ProofCap

end RGen
