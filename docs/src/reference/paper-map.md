# Paper map

| Quote | Primitive |
|---|---|
| "The fundamental problem is that the value of engineering is invisible…" (2017) | The whole repository: a ledger-native record of engineering work. |
| "The claim serves as the quantity (definition) and the validation serves as the quality (characteristics)." (IMECE2020) | `WorkBook.claim` quantity `{unit, value}`; `KAssetBook.validate` quality dimensions. |
| "Each pairing forms a single node with two branches constituting a knowledge asset… memorialized by the creation of an electronic token awarded to each participant." (IMECE2020) | `KAssetBook` + `TokenBook.mintForKAsset` pays claimant and validator. |
| "'Claim' and 'Validation' represent a key mechanism i.e. the 'handshake'." (Bridge) | Work Element → Claim → Validation → Approval state machine. |
| "Validation of credentials should be in place before validation of events." (Bridge) | `CredentialBook` gates `validate`, `approve`, `assess`, `empanel` and `vote`. |
| "An oracle contract is an adjudicated contract with the added requirement that the adjudicator is deemed the most appropriate person…" (NSPE 2016) | `OracleBook` qualification-gated panels and sole-adjudicator `decide`. |
| "Tokens issuance marks points where risk is transferred from one party to another." (Bridge) | Mint only on approval, not on claim or validation. |
| Risk = S × P × E (IMECE2020) | `RiskBook.assess`, `RiskMath.riskScore`. |
| The three insurability questions: exposure, probability, consequence (NAIC 2016) | `RiskMath.triTest`, `RiskBook.attest/link`. |
| "The asset becomes the keeper of its own information." (NSPE, quoting Cahan) | `ProvenanceBook` seals and anchors. |
| "Reputation now is a currency." (BIM+Blockchain) | `TokenBook.earned` and reputation-weighted validation weight. |
| "Blocks are nested." (Bridge) | `KAssetBook.nest`; no mint on composition. |

## Deliberate departures

- The papers' risk table lists S/P 0–5 and E 0–4; RGen clamps each factor to at least 1 so
  a zero cannot erase the others, and the score is 1–100.
- KAT is transferable; the **earned** record is not. Buying KAT does not buy standing.
- Metcalfe/CAPM valuation is deferred; it is a metric, not a primitive.
