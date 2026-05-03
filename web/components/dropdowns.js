// Mode and Agent picker dropdowns. Both share the same close-on-outside-click
// pattern via a small shared hook.

import { useEffect, useRef, useState } from "react";

import { MODE_META } from "../lib/constants";
import { CheckIcon, ChevronDownIcon, UsersIcon } from "./icons";

function useClickAwayClose(open, ref, onClose) {
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    const esc = (e) => e.key === "Escape" && onClose();
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", esc);
    };
  }, [open, ref, onClose]);
}

export function ModeDropdown({ mode, setMode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useClickAwayClose(open, ref, () => setOpen(false));

  const meta = MODE_META[mode] || MODE_META.quick;
  const ActiveIcon = meta.Icon;

  return (
    <div className="mode-drop" ref={ref}>
      <button
        type="button"
        className={`mode-pill ${open ? "mode-pill--open" : ""}`}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <ActiveIcon />
        <span className="mode-pill-label">{meta.label}</span>
        <ChevronDownIcon />
      </button>
      {open && (
        <div className="mode-menu" role="menu">
          {Object.entries(MODE_META).map(([key, m]) => {
            const Ico = m.Icon;
            return (
              <button
                key={key}
                type="button"
                role="menuitemradio"
                aria-checked={mode === key}
                className={`mode-menu-item ${mode === key ? "mode-menu-item--active" : ""}`}
                onClick={() => {
                  setMode(key);
                  setOpen(false);
                }}
              >
                <span className="mode-menu-icon"><Ico /></span>
                <span className="mode-menu-text">
                  <span className="mode-menu-label">{m.label}</span>
                  <span className="mode-menu-sub">{m.sub}</span>
                </span>
                {mode === key && <span className="mode-menu-check"><CheckIcon /></span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function AgentDropdown({ agentKey, setAgentKey, agents }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  useClickAwayClose(open, ref, () => setOpen(false));
  const cur = agents.find((a) => a.key === agentKey) || agents[0];

  return (
    <div className="agent-drop" ref={ref}>
      <button
        type="button"
        className={`agent-pill ${open ? "agent-pill--open" : ""}`}
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={cur?.blurb}
      >
        <UsersIcon />
        <span className="agent-pill-label">{cur?.label || "Agent"}</span>
        <ChevronDownIcon />
      </button>
      {open && (
        <div className="agent-menu" role="menu">
          {agents.map((a) => (
            <button
              key={a.key}
              type="button"
              role="menuitemradio"
              aria-checked={a.key === agentKey}
              className={`agent-menu-item ${a.key === agentKey ? "agent-menu-item--active" : ""}`}
              onClick={() => {
                setAgentKey(a.key);
                setOpen(false);
              }}
            >
              <span className={`agent-color agent-color--${a.key}`} />
              <span className="agent-menu-text">
                <span className="agent-menu-label">
                  {a.label}
                  {a.is_orchestrator && <span className="orch-badge">multi</span>}
                </span>
                <span className="agent-menu-sub">{a.blurb}</span>
              </span>
              {a.key === agentKey && <span className="mode-menu-check"><CheckIcon /></span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
