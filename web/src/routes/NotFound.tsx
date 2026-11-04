import { Link } from "react-router-dom";
import { Panel } from "../components/ui";

export default function NotFound() {
  return (
    <Panel title={<h1>Not found</h1>}>
      <p className="muted">That route does not exist.</p>
      <Link to="/">Back to the overview</Link>
    </Panel>
  );
}
