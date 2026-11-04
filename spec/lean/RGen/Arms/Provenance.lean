import RGen.Arms.Basic
import RGen.Model.Provenance

/-!
# Provenance arm pairs

Anchors and comments append; distinct anchors both succeed, the same anchor is refused,
and comments append without loss. Anchor and comment write different fields.
-/

namespace RGen

def provenanceAnchor (s : ProvenanceState) (writer : Id) (a : Id × Id) :
    Option ProvenanceState :=
  s.addAnchor writer a

def provenanceComment (s : ProvenanceState) (writer : Id) (c : Id) :
    Option ProvenanceState :=
  s.addComment writer c

theorem provenance_anchor_anchor_same_never_after {writer : Id} {a : Id × Id} :
    NeverAfter (fun s => provenanceAnchor s writer a)
      (fun s => provenanceAnchor s writer a) := by
  intro s s1 h
  exact ProvenanceState.anchor_unique h

theorem provenance_anchor_anchor_distinct_appends {s s1 s2 : ProvenanceState}
    {writer : Id} {a b : Id × Id}
    (h1 : s.addAnchor writer a = some s1) (h2 : s1.addAnchor writer b = some s2) :
    s2.anchors = b :: a :: s.anchors := by
  rw [ProvenanceState.addAnchor_appends h2, ProvenanceState.addAnchor_appends h1]

theorem provenance_comment_comment_appends {s s1 s2 : ProvenanceState}
    {writer : Id} {c1 c2 : Id}
    (h1 : s.addComment writer c1 = some s1) (h2 : s1.addComment writer c2 = some s2) :
    s2.comments = c2 :: c1 :: s.comments := by
  rw [ProvenanceState.addComment_appends h2, ProvenanceState.addComment_appends h1]

end RGen
