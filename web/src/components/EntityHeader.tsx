import { useState, type ReactNode } from "react";
import { copy, shareUrl } from "../lib/api";
import { shortId } from "../lib/format";
import type { ReadMeta } from "../lib/types";
import { ReadBadge, StatusPill } from "./ui";

export default function EntityHeader({
  kind,
  uri,
  title,
  status,
  meta,
  actions,
}: {
  kind: string;
  uri: string;
  title?: string;
  status?: string;
  meta?: ReadMeta;
  actions?: ReactNode;
}) {
  const [shared, setShared] = useState(false);
  const share = () => {
    void copy(shareUrl(kind, uri)).then(() => {
      setShared(true);
      window.setTimeout(() => setShared(false), 1_500);
    });
  };
  return (
    <div className="panel-head">
      <div>
        <h1>{title ?? kind}</h1>
        <p className="muted mono small" title={uri}>
          {shortId(uri, 16)}
        </p>
        <div className="row gap wrap">
          <StatusPill status={status} />
          <ReadBadge meta={meta} />
          <button className="ghost small-button" onClick={share} type="button">
            {shared ? "link copied" : "share link"}
          </button>
        </div>
      </div>
      {actions && <div className="row gap wrap">{actions}</div>}
    </div>
  );
}
