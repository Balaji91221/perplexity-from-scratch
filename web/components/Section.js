// Labeled section ("Sources", "Answer", "Steps", "Browser actions", "Agents")
// with an icon, optional suffix (status badge), and a body.

export default function Section({ label, icon, suffix, children }) {
  return (
    <section className="section">
      <div className="section-head">
        <span className="section-icon">{icon}</span>
        <span className="section-label">{label}</span>
        {suffix && <span className="section-suffix">{suffix}</span>}
      </div>
      <div className="section-body">{children}</div>
    </section>
  );
}

export function StageBadge({ stage }) {
  if (stage === "searching") return <span className="badge badge--pulse">Searching…</span>;
  if (stage === "reading") return <span className="badge badge--pulse">Reading sources…</span>;
  if (stage === "thinking") return <span className="badge badge--pulse">Researching…</span>;
  if (stage === "answering") return <span className="badge badge--pulse">Generating…</span>;
  if (stage === "done") return <span className="badge badge--ok">Done</span>;
  if (stage === "error") return <span className="badge badge--err">Error</span>;
  return null;
}
