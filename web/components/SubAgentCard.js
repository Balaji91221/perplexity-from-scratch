// One sub-agent's progress card inside an Orchestrator turn.

import { useState } from "react";
import { CheckIcon, DotIcon, Spinner } from "./icons";
import StepRow from "./StepRow";

const LABELS = { researcher: "Researcher", coder: "Coder", analyst: "Analyst" };

export default function SubAgentCard({ sub, computer }) {
  const [open, setOpen] = useState(true);

  return (
    <div className={`sub-agent sub-agent--${sub.agent} sub-agent--${sub.status}`}>
      <button type="button" className="sub-agent-head" onClick={() => setOpen((o) => !o)}>
        <span className={`agent-color agent-color--${sub.agent}`} />
        <span className="sub-agent-label">{LABELS[sub.agent] || sub.agent}</span>
        <span className="sub-agent-task">{sub.subtask}</span>
        <span className="sub-agent-status">
          {sub.status === "running" && <Spinner />}
          {sub.status === "done" && <CheckIcon />}
          {sub.status === "pending" && <DotIcon />}
          {sub.status === "error" && "!"}
        </span>
      </button>
      {open && sub.steps && sub.steps.length > 0 && (
        <ol className="step-list step-list--nested">
          {sub.steps.map((s, i) => (
            <StepRow key={i} step={s} computer={computer} />
          ))}
        </ol>
      )}
      {sub.status === "error" && sub.error && (
        <div className="error-box" style={{ marginTop: 8 }}>{sub.error}</div>
      )}
    </div>
  );
}

export function PhaseBadge({ phase }) {
  if (phase === "planning") return <span className="badge badge--pulse">Planning…</span>;
  if (phase === "running") return <span className="badge badge--pulse">Running agents…</span>;
  if (phase === "synthesizing") return <span className="badge badge--pulse">Synthesizing…</span>;
  return null;
}
