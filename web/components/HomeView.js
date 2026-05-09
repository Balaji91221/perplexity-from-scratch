// Empty-state landing view: hero + search box + suggestion cards.

import { BRAND, SUGGESTIONS } from "../lib/constants";
import {
  ArrowIcon,
  CompareIcon,
  HistoryIcon,
  NewsIcon,
  ScienceIcon,
} from "./icons";
import { ModeDropdown, AgentDropdown } from "./dropdowns";
import { ActiveSkillChip, SkillsAutocomplete } from "./skills";
import { AttachmentStrip, UploadButton } from "./inputs";

const KIND_ICON = {
  science: ScienceIcon,
  compare: CompareIcon,
  news: NewsIcon,
  history: HistoryIcon,
};

export default function HomeView({
  query, setQuery, onSubmit, inputRef,
  mode, setMode,
  docs, uploading, uploadError, onUpload, onRemoveDoc,
  skill, setSkill,
  agentKey, setAgentKey, agents,
}) {
  const [titleA, titleB] = BRAND.hero.title;

  return (
    <div className="home">
      <div className="brand-glow" aria-hidden="true" />

      <div className="hero-block">
        <h1 className="hero">
          {titleA} <span className="hero-accent">{titleB}</span>
        </h1>
        <p className="hero-sub">{BRAND.hero.sub}</p>
      </div>

      <AttachmentStrip
        docs={docs}
        uploading={uploading}
        uploadError={uploadError}
        onRemove={onRemoveDoc}
      />

      <div className="search-wrap">
        <form className="search-box" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
          <UploadButton uploading={uploading} onUpload={onUpload} />
          <ActiveSkillChip skill={skill} onClear={() => setSkill(null)} />
          <input
            ref={inputRef}
            className="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={
              skill ? `${skill.label} — type your question…` :
              docs.length > 0
                ? "Ask about the attached document, or type / for skills"
                : mode === "deep" ? "Ask a hard question, or type / for skills" : "Ask anything, or type / for skills"
            }
          />
          <AgentDropdown agentKey={agentKey} setAgentKey={setAgentKey} agents={agents} />
          <ModeDropdown mode={mode} setMode={setMode} />
          <button type="submit" className="search-submit" disabled={!query.trim()} aria-label="Ask">
            <ArrowIcon />
          </button>
        </form>
        <SkillsAutocomplete
          query={query}
          setQuery={setQuery}
          skill={skill}
          setSkill={setSkill}
          onSubmit={onSubmit}
          inputRef={inputRef}
        />
      </div>

      <ul className="feature-pills" aria-label="Capabilities">
        {BRAND.features.map((f) => (
          <li key={f} className="feature-pill">
            <span className="feature-dot" aria-hidden="true" />
            {f}
          </li>
        ))}
      </ul>

      <div className="suggestion-cards">
        {SUGGESTIONS.map((s) => {
          const Icon = KIND_ICON[s.kind];
          return (
            <button
              key={s.cmd}
              className="suggestion-card"
              onClick={() => {
                setQuery(s.text);
                setTimeout(onSubmit, 0);
              }}
            >
              <span className="suggestion-head">
                {Icon && (
                  <span className="suggestion-icon" aria-hidden="true"><Icon /></span>
                )}
                <span className="suggestion-cmd">/{s.cmd}</span>
              </span>
              <span className="suggestion-text">{s.text}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
