import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { message, parseWrite } from "../lib/api";
import { useHeight } from "../lib/entity";
import * as journal from "../lib/journal";
import { commaList } from "../lib/format";
import { useWallet } from "../lib/store";
import { ErrorBox, Field, Panel } from "../components/ui";

export default function ValuePropositionNew() {
  const navigate = useNavigate();
  const client = useWallet((state) => state.client);
  const status = useWallet((state) => state.status);
  const height = useHeight();
  const [subjectRef, setSubjectRef] = useState("");
  const [statement, setStatement] = useState(
    "The bridge deck inspection is worth twelve validated bay inspections.",
  );
  const [terms, setTerms] = useState(
    "Payment on approval; liability follows the approver's share.",
  );
  const [valueModel, setValueModel] = useState(
    "One K-Asset per validated claim; value follows the validation quality.",
  );
  const [discipline, setDiscipline] = useState("structural");
  const [jurisdiction, setJurisdiction] = useState("US-TX");
  const [ctype, setCtype] = useState("Validator");
  const [role, setRole] = useState("validator");
  const [minLevel, setMinLevel] = useState("1");
  const [beneficiaries, setBeneficiaries] = useState("");
  const [deadline, setDeadline] = useState("");
  const [unit, setUnit] = useState("inspections");
  const [quantityMean, setQuantityMean] = useState("12");
  const [kind, setKind] = useState("bridge inspection");
  const [spec, setSpec] = useState("twelve-bay deck");
  const [qualityMean, setQualityMean] = useState("18");
  const [quantityBps, setQuantityBps] = useState("400");
  const [qualityBps, setQualityBps] = useState("1200");
  const [sampleN, setSampleN] = useState("30");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (height.data !== undefined && !deadline) setDeadline(String(height.data + 1000));
  }, [height.data, deadline]);

  const submit = async () => {
    if (!client) return;
    setBusy(true);
    setError(null);
    try {
      const criteria = {
        ctype,
        discipline,
        jurisdiction,
        role,
        minLevel: Number(minLevel),
      };
      const payload = {
        subjectRef: { uri: subjectRef.trim() },
        statementHash: client.hash_text(statement),
        valueModelHash: client.hash_text(valueModel),
        beneficiaries: commaList(beneficiaries),
        termsHash: client.hash_text(terms),
        selectionCriteria: criteria,
        deadlineHeight: Number(deadline),
        quantity: { unit: unit.trim(), mean: Number(quantityMean) },
        quality: {
          kind: kind.trim(),
          spec: spec.trim(),
          scale: { min: 4, max: 20 },
          mean: Number(qualityMean),
        },
        variance: {
          quantityBps: Number(quantityBps),
          qualityBps: Number(qualityBps),
          n: Number(sampleN),
        },
      };
      const envelope = parseWrite<{ id?: string; uri?: string }>(
        await client.vp_propose(JSON.stringify(payload)),
      );
      const uri = envelope.data.uri ?? envelope.data.id;
      await journal.fromReceipt("value", envelope.deploy, "value proposition proposed", uri);
      if (uri) navigate(`/value/${uri}`);
    } catch (cause) {
      setError(message(cause));
    } finally {
      setBusy(false);
    }
  };

  if (status !== "unlocked") {
    return (
      <Panel title={<h1>New value proposition</h1>}>
        <p className="muted">Unlock the proposer wallet.</p>
      </Panel>
    );
  }

  return (
    <div className="stack">
      <Panel title={<h1>New value proposition</h1>}>
        <p className="muted small">
          Free text is hashed locally. The subject reference can be a project URI or a
          registry name for the asset the proposition is about.
        </p>
        <div className="grid two">
          <div>
            <Field label="Subject reference" hint="URI">
              <input
                value={subjectRef}
                onChange={(event) => setSubjectRef(event.target.value)}
                placeholder="rho:id:… or project reference"
                className="mono"
              />
            </Field>
            <Field label="Statement" hint="hashed">
              <textarea
                rows={4}
                value={statement}
                onChange={(event) => setStatement(event.target.value)}
              />
            </Field>
            <Field label="Terms" hint="hashed">
              <textarea
                rows={3}
                value={terms}
                onChange={(event) => setTerms(event.target.value)}
              />
            </Field>
            <Field label="Value model" hint="hashed">
              <textarea
                rows={3}
                value={valueModel}
                onChange={(event) => setValueModel(event.target.value)}
              />
            </Field>
          </div>
          <div>
            <Field label="Validator credential type">
              <input value={ctype} onChange={(event) => setCtype(event.target.value)} />
            </Field>
            <Field label="Validator role">
              <input value={role} onChange={(event) => setRole(event.target.value)} />
            </Field>
            <Field label="Minimum level">
              <input
                type="number"
                min={1}
                value={minLevel}
                onChange={(event) => setMinLevel(event.target.value)}
              />
            </Field>
            <Field label="Discipline">
              <input value={discipline} onChange={(event) => setDiscipline(event.target.value)} />
            </Field>
            <Field label="Jurisdiction">
              <input
                value={jurisdiction}
                onChange={(event) => setJurisdiction(event.target.value)}
              />
            </Field>
            <Field label="Beneficiaries" hint="comma-separated REV addresses">
              <input
                value={beneficiaries}
                onChange={(event) => setBeneficiaries(event.target.value)}
                className="mono"
              />
            </Field>
            <Field label="Deadline height" hint={`current ${height.data ?? "…"}`}>
              <input
                type="number"
                value={deadline}
                onChange={(event) => setDeadline(event.target.value)}
              />
            </Field>
          </div>
        </div>
        <div className="grid two">
          <div>
            <Field label="Quantity unit" hint="m3, kg, inspections, …">
              <input value={unit} onChange={(event) => setUnit(event.target.value)} />
            </Field>
            <Field label="Quantity mean">
              <input
                type="number"
                min={1}
                value={quantityMean}
                onChange={(event) => setQuantityMean(event.target.value)}
              />
            </Field>
            <Field label="Quality kind" hint="what the thing is">
              <input value={kind} onChange={(event) => setKind(event.target.value)} />
            </Field>
            <Field label="Quality specification">
              <input value={spec} onChange={(event) => setSpec(event.target.value)} />
            </Field>
          </div>
          <div>
            <Field label="Quality mean" hint="4..20">
              <input
                type="number"
                min={4}
                max={20}
                value={qualityMean}
                onChange={(event) => setQualityMean(event.target.value)}
              />
            </Field>
            <Field label="Quantity variance" hint="basis points, σ²/mean²">
              <input
                type="number"
                min={0}
                max={10000}
                value={quantityBps}
                onChange={(event) => setQuantityBps(event.target.value)}
              />
            </Field>
            <Field label="Quality variance" hint="basis points, σ²/mean²">
              <input
                type="number"
                min={0}
                max={10000}
                value={qualityBps}
                onChange={(event) => setQualityBps(event.target.value)}
              />
            </Field>
            <Field label="Sample size" hint="n ≥ 1">
              <input
                type="number"
                min={1}
                value={sampleN}
                onChange={(event) => setSampleN(event.target.value)}
              />
            </Field>
          </div>
        </div>
        <ErrorBox error={error} />
        <button
          className="primary"
          onClick={submit}
          disabled={busy || !client || !subjectRef || !deadline || !unit.trim() || !kind.trim() || !spec.trim()}
        >
          {busy ? "signing and waiting for finality…" : "Propose value"}
        </button>
      </Panel>
    </div>
  );
}
