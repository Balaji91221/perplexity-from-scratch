// A single Q&A turn in the thread. Composes Sources / Steps / Answer (and for
// orchestrator turns, a stack of sub-agent cards).

import { AnswerIcon, BeakerIcon, DesktopIcon, SourceIcon, UsersIcon } from "./icons";
import Section, { StageBadge } from "./Section";
import { SourceCard, SourceSkeleton, AnswerSkeleton } from "./sources";
import StepRow from "./StepRow";
import SubAgentCard, { PhaseBadge } from "./SubAgentCard";
import Answer from "./Answer";

export default function Turn({ turn, isLast, onOpenPdf }) {
  const isAgentic = turn.mode === "deep" || turn.mode === "computer";
  const isComputer = turn.mode === "computer";
  const isOrchestrator = turn.agent === "orchestrator";
  const sourcesPending =
    turn.sources.length === 0 && (turn.stage === "searching" || turn.stage === "reading");
  const modeLabel = isComputer ? "Computer Use" : turn.mode === "deep" ? "Deep Research" : null;
  const agentLabel =
    turn.agent && turn.agent !== "generalist"
      ? turn.agent === "orchestrator"
        ? "Orchestrator"
        : turn.agent[0].toUpperCase() + turn.agent.slice(1)
      : null;

  return (
    <article className="turn">
      <div className="question-row">
        <h2 className="question">{turn.question}</h2>
        {agentLabel && <span className={`agent-tag agent-tag--${turn.agent}`}>{agentLabel}</span>}
        {modeLabel && <span className="mode-tag">{modeLabel}</span>}
        {turn.skill && <span className="skill-tag-inline">/{turn.skill.cmd}</span>}
      </div>

      {isOrchestrator && turn.subAgents && turn.subAgents.length > 0 && (
        <Section
          label="Agents"
          icon={<UsersIcon />}
          suffix={isLast ? <PhaseBadge phase={turn.phase} /> : null}
        >
          <div className="sub-agent-list">
            {turn.subAgents.map((sa, i) => (
              <SubAgentCard key={i} sub={sa} computer={isComputer} />
            ))}
          </div>
        </Section>
      )}

      {!isOrchestrator && isAgentic && turn.steps.length > 0 && (
        <Section
          label={isComputer ? "Browser actions" : "Steps"}
          icon={isComputer ? <DesktopIcon /> : <BeakerIcon />}
        >
          <ol className="step-list">
            {turn.steps.map((s, i) => (
              <StepRow key={i} step={s} computer={isComputer} />
            ))}
          </ol>
        </Section>
      )}

      {!isAgentic && !isOrchestrator && turn.subqueries && turn.subqueries.length > 1 && (
        <div className="subquery-strip" aria-label="Sub-queries">
          <span className="subquery-strip__label">Searched</span>
          {turn.subqueries.map((q, i) => (
            <span key={i} className="subquery-chip">{q}</span>
          ))}
        </div>
      )}

      <Section label="Sources" icon={<SourceIcon />}>
        {turn.sources.length === 0 ? (
          sourcesPending || (isAgentic && turn.stage === "thinking") ? (
            <SourceSkeleton />
          ) : (
            <div className="muted">No sources.</div>
          )
        ) : (
          <div className="source-grid">
            {turn.sources.map((s) => (
              <SourceCard key={s.n} source={s} onOpenPdf={onOpenPdf} />
            ))}
          </div>
        )}
      </Section>

      <Section
        label="Answer"
        icon={<AnswerIcon />}
        suffix={isLast ? <StageBadge stage={turn.stage} /> : null}
      >
        {turn.error && <div className="error-box">{turn.error}</div>}
        {!turn.answer && !turn.error && <AnswerSkeleton />}
        {turn.answer && <Answer text={turn.answer} sources={turn.sources} onOpenPdf={onOpenPdf} />}
      </Section>
    </article>
  );
}
