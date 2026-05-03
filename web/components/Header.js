// Sticky top header — sidebar toggle + logo + focus tabs + new-thread button.

import FocusTabs from "./FocusTabs";
import { MenuIcon, SparkIcon } from "./icons";

export default function Header({
  hasActivity,
  onToggleSidebar,
  sidebarOpen,
  onNewThread,
  focus,
  setFocus,
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
        <SparkIcon />
        <span>perplexity-clone</span>
      </button>
      <FocusTabs focus={focus} setFocus={setFocus} />
      <div className="header-spacer" />
      {hasActivity && (
        <button className="new-thread" onClick={onNewThread}>
          New thread
        </button>
      )}
    </header>
  );
}
