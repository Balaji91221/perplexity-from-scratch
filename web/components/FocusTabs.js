// Web / Academic / News / Reddit tabs in the header — pass `focus` to /ask.

import { FOCUS_TABS } from "../lib/constants";

export default function FocusTabs({ focus, setFocus }) {
  return (
    <nav className="focus-tabs" role="tablist" aria-label="Source focus">
      {FOCUS_TABS.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={focus === t.key}
          className={`focus-tab ${focus === t.key ? "focus-tab--active" : ""}`}
          onClick={() => setFocus(t.key)}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}
