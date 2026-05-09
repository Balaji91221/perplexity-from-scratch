// Sticky top header — sidebar toggle + logo + focus tabs + new-thread button.

import { BRAND } from "../lib/constants";
import FocusTabs from "./FocusTabs";
import { BrandMark, MenuIcon, RobotIcon } from "./icons";

export default function Header({
  hasActivity,
  onToggleSidebar,
  sidebarOpen,
  onNewThread,
  focus,
  setFocus,
  assistantOpen,
  onToggleAssistant,
}) {
  return (
    <header className="header">
      <button
        className="sidebar-toggle"
        onClick={onToggleSidebar}
        aria-label="Toggle sidebar"
        title={sidebarOpen ? "Hide sidebar" : "Show sidebar"}
      >
        <MenuIcon />
      </button>
      <button className="logo" onClick={onNewThread} aria-label="Home">
        <BrandMark size={22} />
        <span className="logo-name">{BRAND.name}</span>
      </button>
      <FocusTabs focus={focus} setFocus={setFocus} />
      <div className="header-spacer" />
      <button
        className={`assistant-toggle ${assistantOpen ? "is-open" : ""}`}
        onClick={onToggleAssistant}
        title="Assistant — autonomous crawler"
        aria-label="Toggle assistant panel"
        aria-pressed={assistantOpen}
      >
        <RobotIcon />
        <span>Assistant</span>
      </button>
      {hasActivity && (
        <button className="new-thread" onClick={onNewThread}>
          New thread
        </button>
      )}
    </header>
  );
}
