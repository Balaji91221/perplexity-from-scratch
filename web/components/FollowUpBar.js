// Sticky follow-up input rendered below the thread once a turn exists.

import { ArrowIcon } from "./icons";
import { ModeDropdown, AgentDropdown } from "./dropdowns";
import { ActiveSkillChip, SkillsAutocomplete } from "./skills";
import { AttachmentStrip, UploadButton } from "./inputs";

export default function FollowUpBar({
  sidebarOpen,
  query, setQuery, onSubmit, disabled, inputRef,
  mode, setMode,
  docs, uploading, uploadError, onUpload, onRemoveDoc,
  skill, setSkill,
  agentKey, setAgentKey, agents,
}) {
  return (
    <div className={`followup ${sidebarOpen ? "followup--with-sidebar" : ""}`}>
      <div className="followup-inner">
        <AttachmentStrip
          docs={docs}
          uploading={uploading}
          uploadError={uploadError}
          onRemove={onRemoveDoc}
        />
        <div className="search-wrap search-wrap--followup">
          <form className="followup-form" onSubmit={(e) => { e.preventDefault(); onSubmit(); }}>
            <UploadButton uploading={uploading} onUpload={onUpload} />
            <ActiveSkillChip skill={skill} onClear={() => setSkill(null)} />
            <input
              ref={inputRef}
              className="followup-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={
                skill ? `${skill.label} — type your question…` :
                docs.length > 0 ? "Ask about the document, or type / for skills" : "Ask a follow-up, or type / for skills"
              }
              disabled={disabled}
            />
            <AgentDropdown agentKey={agentKey} setAgentKey={setAgentKey} agents={agents} />
            <ModeDropdown mode={mode} setMode={setMode} />
            <button
              type="submit"
              className="followup-submit"
              disabled={disabled || !query.trim()}
              aria-label="Send"
            >
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
      </div>
    </div>
  );
}
