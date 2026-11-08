# Deploy semantics on the pinned devnet

Measured 2026-11-08T17:45:59.774223+00:00 against RChain Node 0.1.0 (e2d073dcd02f1e560ccb84749937138a1e184b0b) (testnet, shard /root, height 990).

| Probe | Observation | Meaning |
|---|---|---|
| write, then reduction error | value after error = 42 (pre-error value 42) | rollback |
| consume, then block without re-post | read after loss = [] | consumed cell lost |
| `Claim.comment` with `commentUntilHeight = Nil` | deploy verdict `processedwithsuccess` | see report |

## Verdict

The node rolls back a deploy that ends in a reduction error. The "crash after a partial write" reading of RGA-031/032/033 is not reachable through an erroring deploy on this build.
A deploy that consumes a linear cell and then blocks is reported as `processedWithSuccess` with an empty result, and the consumed cell is gone. This is the reachable partial-commit path: holding a consumed cell across a callee that may not reply loses the cell. HAZOP rows and the contract fixes must treat blocked continuations, not only reduction errors, as the failure mode.

Natural claim probe: reply before `(True, {'claimant': '11112VYAt8rUGNRRZX3eJdgagaAhtWTK8Js7F7X5iqddMVqyDTtYau', 'comments': [], 'createdAt': 1001, 'deadlineHeight': 1000000, 'definitionHash': 'twelve inspections', 'evidence': [{'hash': 'aa', 'kind': 'photo'}], 'quantity': {'unit': 'inspections', 'value': 12}, 'selectionCriteria': {'ctype': 'Validator', 'discipline': 'structural', 'jurisdiction': 'US-TX', 'minLevel': 1, 'role': 'validator'}, 'selectionCriteriaHash': 'sc', 'statementHash': 'deck inspected', 'status': 'open', 'updatedAt': 1001, 'uri': 'rho:id:dofr7wun5x8axqpncotai58y75m5yo7w8muyhyt5wh8o4o8murfo', 'version': 1, 'work': {'discipline': 'structural', 'jurisdiction': 'US-TX', 'projectRef': 'fixture', 'titleHash': 'bridge-deck'}})`, after `(True, {'claimant': '11112VYAt8rUGNRRZX3eJdgagaAhtWTK8Js7F7X5iqddMVqyDTtYau', 'comments': [{'at': 1004, 'by': '11112VYAt8rUGNRRZX3eJdgagaAhtWTK8Js7F7X5iqddMVqyDTtYau', 'hash': 'semantics-probe', 'id': 'cm:11112VYAt8rUGNRRZX3eJdgagaAhtWTK8Js7F7X5iqddMVqyDTtYau:1004'}], 'createdAt': 1001, 'deadlineHeight': 1000000, 'definitionHash': 'twelve inspections', 'evidence': [{'hash': 'aa', 'kind': 'photo'}], 'quantity': {'unit': 'inspections', 'value': 12}, 'selectionCriteria': {'ctype': 'Validator', 'discipline': 'structural', 'jurisdiction': 'US-TX', 'minLevel': 1, 'role': 'validator'}, 'selectionCriteriaHash': 'sc', 'statementHash': 'deck inspected', 'status': 'open', 'updatedAt': 1004, 'uri': 'rho:id:dofr7wun5x8axqpncotai58y75m5yo7w8muyhyt5wh8o4o8murfo', 'version': 2, 'work': {'discipline': 'structural', 'jurisdiction': 'US-TX', 'projectRef': 'fixture', 'titleHash': 'bridge-deck'}})`. A reduction error leaves the claim state intact; the defect is a bad refusal path, not state loss.

Raw report: `spec/audit/deploy-semantics.json`.
