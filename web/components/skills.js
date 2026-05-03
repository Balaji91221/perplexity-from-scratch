// `/skill` autocomplete dropdown + the "active skill" chip rendered inside
// the input. The skill prepends a system-style instruction to the user's
// next message; the prompt expansion happens in the parent `ask()`.

import { SKILLS } from "../lib/constants";

export function SkillsAutocomplete({ query, setQuery, skill, setSkill, onSubmit, inputRef }) {
  const slashMatch = !skill && /^\/([a-z]*)$/i.exec(query);
  const items = slashMatch
    ? SKILLS.filter((s) => s.cmd.toLowerCase().startsWith(slashMatch[1].toLowerCase()))
    : [];
  if (!slashMatch || items.length === 0) return null;

  return (
    <div className="skills-menu" role="listbox">
      {items.map((s) => (
        <button
          key={s.cmd}
          type="button"
          role="option"
          className="skill-item"
          onMouseDown={(e) => {
            e.preventDefault();
            setSkill(s);
            setQuery("");
            setTimeout(() => inputRef.current?.focus(), 0);
          }}
        >
          <span className="skill-cmd">/{s.cmd}</span>
          <span className="skill-text">
            <span className="skill-label">{s.label}</span>
            <span className="skill-desc">{s.desc}</span>
          </span>
        </button>
      ))}
    </div>
  );
}

export function ActiveSkillChip({ skill, onClear }) {
  if (!skill) return null;
  return (
    <span className="skill-chip" title={skill.desc}>
      <span className="skill-chip-cmd">/{skill.cmd}</span>
      <span className="skill-chip-label">{skill.label}</span>
      <button type="button" className="skill-chip-x" onClick={onClear} aria-label="Clear skill">
        ×
      </button>
    </span>
  );
}
