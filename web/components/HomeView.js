// Empty-state landing view: hero + search box + suggestion cards.

import { SUGGESTIONS } from "../lib/constants";
import { ArrowIcon } from "./icons";
import { ModeDropdown, AgentDropdown } from "./dropdowns";
import { ActiveSkillChip, SkillsAutocomplete } from "./skills";
import { AttachmentStrip, UploadButton } from "./inputs";

export default function HomeView({
  query, setQuery, onSubmit, inputRef,
  mode, setMode,
  docs, uploading, uploadError, onUpload, onRemoveDoc,
  skill, setSkill,
  agentKey, setAgentKey, agents,
}) {
  return (
    <div className="home">
      <h1 className="hero">
        Where knowledge <span className="hero-accent">begins</span>.
      </h1>

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

      <div className="suggestion-cards">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.cmd}
            className="suggestion-card"
            onClick={() => {
              setQuery(s.text);
              setTimeout(onSubmit, 0);
            }}
          >
            <span className="suggestion-cmd">/{s.cmd}</span>
            <span className="suggestion-text">{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
