import { useEffect } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Overview from "./routes/Overview";
import Claims from "./routes/Claims";
import ClaimNew from "./routes/ClaimNew";
import Claim from "./routes/Claim";
import KAssets from "./routes/KAssets";
import KAsset from "./routes/KAsset";
import Credentials from "./routes/Credentials";
import CredentialIssue from "./routes/CredentialIssue";
import Credential from "./routes/Credential";
import ValuePropositions from "./routes/ValuePropositions";
import ValuePropositionNew from "./routes/ValuePropositionNew";
import ValueProposition from "./routes/ValueProposition";
import Cases from "./routes/Cases";
import Case from "./routes/Case";
import Provenance from "./routes/Provenance";
import ProvenanceNew from "./routes/ProvenanceNew";
import ProvenanceDetail from "./routes/ProvenanceDetail";
import Identity from "./routes/Identity";
import Activity from "./routes/Activity";
import Settings from "./routes/Settings";
import NotFound from "./routes/NotFound";
import { useWallet } from "./lib/store";

export default function App() {
  const boot = useWallet((state) => state.boot);
  useEffect(() => {
    void boot();
  }, [boot]);

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="claims" element={<Claims />} />
        <Route path="claims/new" element={<ClaimNew />} />
        <Route path="claims/:uri" element={<Claim />} />
        <Route path="kassets" element={<KAssets />} />
        <Route path="kassets/:uri" element={<KAsset />} />
        <Route path="credentials" element={<Credentials />} />
        <Route path="credentials/issue" element={<CredentialIssue />} />
        <Route path="credentials/:uri" element={<Credential />} />
        <Route path="value" element={<ValuePropositions />} />
        <Route path="value/new" element={<ValuePropositionNew />} />
        <Route path="value/:uri" element={<ValueProposition />} />
        <Route path="cases" element={<Cases />} />
        <Route path="cases/:uri" element={<Case />} />
        <Route path="provenance" element={<Provenance />} />
        <Route path="provenance/new" element={<ProvenanceNew />} />
        <Route path="provenance/:uri" element={<ProvenanceDetail />} />
        <Route path="identity" element={<Identity />} />
        <Route path="identity/:address" element={<Identity />} />
        <Route path="activity" element={<Activity />} />
        <Route path="settings" element={<Settings />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
