# Workflow HAZOP: multi-agent run 2026-11-07

> **Run:** 2026-11-07
> **Baseline:** `639d0f2`, with the HAZOP repair in the working tree
> **Artifacts:** `spec/hazop/runs/2026-11-07/{manifest,workflow,adjudication}.yaml`
> **Checker:** `make hazop-check`

## Method

The run is blind and independent:

- **Three analysts.** Identity/credentials/registries; claim/K-Asset/oracle;
  VP/provenance/deploy and the end-to-end workflow. Each received only its node scope, the
  contract source, the 15 guide words, and the row schema. The existing worksheet, findings
  ledger, flow manifests and the other analysts' rows were withheld.
- **One red-team operator.** The operator ran `harness/probe_deploy_semantics.py` and
  `harness/redteam_core.py` against the live devnet install. Exploit evidence is `RT-001+`.
- **Adjudication.** Every S1/S2 row needs two independent authors or a recorded adjudication
  decision. The owner reviewed the S2/S3 decisions in `adjudication.yaml`.
- **Evidence rule.** Every row names a file and line range, a concrete trigger, and a falsifier
  (a test or theorem). A row without evidence is rejected by `tools/check_hazop_runs.py`.

The existing 146-row `spec/hazop/worksheet.yaml` remains the contract-node register. This run
adds the workflow and cross-node register, because no single-node pass sees a hazard that spans
identity, credential, claim, K-Asset, oracle and provenance.

## Nodes

| Node | Scope |
|---|---|
| `wf-onboard` | identity create → credential issue → proof issue |
| `wf-propose-claim` | VP propose → claim create → `valuePropositionRef` binding |
| `wf-validate-mint` | validate → proof consume → K-Asset mint → approve |
| `wf-dispute-decide-execute` | dispute → oracle open → evidence → decide → execute → apply |
| `wf-closeout-provenance` | final K-Asset → provenance create → anchor → comment |
| `wf-recovery` | pending/resume, validating/resume, execute retry, proof burn |
| `xnode-authority` | subject/party/opener/adjudicator bindings |
| `xnode-registry` | state map vs factory registry consistency |
| `xnode-time` | claim/VP/oracle/comment deadline ordering |

Twenty-five rows cover all nine nodes. The highest-risk rows and their disposition:

| Row | Hazard | Disposition |
|---|---|---|
| WF-001 | identity create/resume two-phase window | fixed by the reservation protocol; `at_most_one_identity_per_address` |
| WF-006 | validation records a caller-supplied credential URI | fixed; the proved URI is passed into finalize |
| WF-007 | K-Asset mint before the claim write | fixed; write-ahead receipt, release, mint, commit, resume |
| WF-009 | VP validator cannot open a dispute (`*dId` vs `*dId2`) | fixed; RT-020 |
| WF-010 | oracle decide after the case deadline | fixed; RT-022 |
| WF-022 | identity update clears omitted fields | fixed; `patchOr` |
| WF-023 | credential issue with a missing level | fixed; `credentialReqOk` |
| WF-025 | public proof URI can be burned by a third party | fixed; private proof capability |

Accepted items are recorded with their reason in `adjudication.yaml`: the VP reference is not
resolved at claim create (approval gates on a VP proof), provenance is advisory, `verify` is
existence-only, the execute receipt undercounts attempts, and a fake oracle case can exist but
cannot touch a real subject.

## Cross-node hazards that matter

- **Credential revoke vs proof consumption.** A proof is a height snapshot. Every core consumer
  checks `atHeight == now`, so a proof cannot move to a later event. `prove-vs-revoke` is tested.
- **VP dispute vs claim validation.** A claim can be validated with a disputed VP reference and
  mint a K-Asset; approval then refuses because `checkApprovalVp` needs a validated VP proof.
- **Oracle decide vs expire.** Both consume the case cell; exactly one wins. `decide` now also
  refuses after the deadline.
- **Execute vs close.** `close` requires executed or expired; a decided case with a permanent
  apply failure is stuck in decided. Accepted.
- **Nest vs dispute.** The parent is peeked, child proofs are reserved privately, then the parent
  is consumed and rechecked. A failed final check leaves the parent unchanged; the attempt's
  private proofs are re-mintable.

## Verify

```bash
python3 tools/check_hazop_runs.py
```

The checker requires a manifest, at least three blind agents, input hashes, every workflow node,
all row fields, two independent authors or an adjudication decision for every S1/S2 row, existing
evidence paths, and adjudication entries that reference real rows.

## Limits

- This is a structured expert review, not a mechanized Rholang semantics.
- The contract-node worksheet was not re-authored in this run; its 146 rows remain the prior
  register and are cross-referenced by `finding`.
- The two-source rule is a process control, not a proof of independence. The owner adjudicated
  the S2/S3 decisions.
