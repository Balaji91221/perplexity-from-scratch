// Left rail. Top: New / Computer / History nav. Then MCP servers, Documents,
// Threads (grouped by date). Bottom: theme toggle + footer label.

import { useMemo, useRef, useState } from "react";

import {
  ChevronLeftIcon,
  ClockIcon,
  DesktopIcon,
  FileIcon,
  PlugIcon,
  PlusIcon,
  SparkIcon,
  TrashIcon,
} from "./icons";
import ThemeToggle from "./ThemeToggle";

function groupThreadsByDate(threads) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const yesterday = new Date(today.getTime() - 24 * 3600 * 1000);
  const last7 = new Date(today.getTime() - 7 * 24 * 3600 * 1000);

  const groups = { Today: [], Yesterday: [], "Last 7 days": [], Earlier: [] };
  for (const t of threads) {
    const d = new Date(t.updated_at);
    if (d >= today) groups.Today.push(t);
    else if (d >= yesterday) groups.Yesterday.push(t);
    else if (d >= last7) groups["Last 7 days"].push(t);
    else groups.Earlier.push(t);
  }
  return groups;
}

function McpServerRow({ server }) {
  const [open, setOpen] = useState(false);
  const ok = server.status === "ok";
  const tools = server.tools || [];
  return (
    <div className={`mcp-server ${ok ? "mcp-server--ok" : "mcp-server--err"}`}>
      <button
        type="button"
        className="mcp-server-head"
        onClick={() => setOpen((o) => !o)}
        title={server.description || server.name}
      >
        <span className={`mcp-dot ${ok ? "mcp-dot--ok" : "mcp-dot--err"}`} />
        <span className="mcp-server-name">{server.name}</span>
        <span className="mcp-server-count">{ok ? `${tools.length}` : "off"}</span>
      </button>
      {open && (
        <ul className="mcp-tools">
          {ok ? (
            tools.length === 0 ? (
              <li className="mcp-tool mcp-tool--muted">No tools exposed.</li>
            ) : (
              tools.map((t) => (
                <li key={t.name} className="mcp-tool" title={t.description || ""}>
                  <span className="mcp-tool-name">{t.name}</span>
                  {t.description && <span className="mcp-tool-desc">{t.description}</span>}
                </li>
              ))
            )
          ) : (
            <li className="mcp-tool mcp-tool--err">{server.error || "not connected"}</li>
          )}
        </ul>
      )}
    </div>
  );
}

export default function Sidebar({
  open,
  threads,
  currentThreadId,
  allDocs,
  attachedIds,
  mcpServers,
  mode,
  setMode,
  theme,
  setTheme,
  onToggle,
  onNewThread,
  onSelectThread,
  onDeleteThread,
  onAttachDoc,
  onDetachDoc,
  onDeleteDoc,
}) {
  const groups = useMemo(() => groupThreadsByDate(threads), [threads]);
  const historyRef = useRef(null);

  const goHistory = () => {
    historyRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const startComputerThread = () => {
    setMode("computer");
    onNewThread();
  };

  return (
    <aside className={`sidebar ${open ? "sidebar--open" : ""}`}>
      <div className="sidebar-head">
        <button className="sidebar-logo" onClick={onNewThread}>
          <SparkIcon />
          <span>perplexity-clone</span>
        </button>
        <button className="icon-btn" onClick={onToggle} title="Hide sidebar">
          <ChevronLeftIcon />
        </button>
      </div>

      <nav className="nav-list">
        <button className="nav-item nav-item--primary" onClick={onNewThread}>
          <PlusIcon /> <span>New</span>
        </button>
        <button
          className={`nav-item ${mode === "computer" ? "nav-item--active" : ""}`}
          onClick={startComputerThread}
          title="Computer Use — agent browses with screenshots"
        >
          <DesktopIcon /> <span>Computer</span>
        </button>
        <button className="nav-item" onClick={goHistory}>
          <ClockIcon /> <span>History</span>
        </button>
      </nav>

      <div className="sidebar-divider" />

      {mcpServers && mcpServers.length > 0 && (
        <div className="mcp-section">
          <div className="doc-section-head">
            <PlugIcon /> <span>MCP servers</span>
            <span className="doc-count">
              {mcpServers.filter((s) => s.status === "ok").length}/{mcpServers.length}
            </span>
          </div>
          <div className="mcp-list">
            {mcpServers.map((s) => (
              <McpServerRow key={s.name} server={s} />
            ))}
          </div>
          <div className="sidebar-divider" />
        </div>
      )}

      {allDocs && allDocs.length > 0 && (
        <div className="doc-section">
          <div className="doc-section-head">
            <FileIcon /> <span>Documents</span>
            <span className="doc-count">{allDocs.length}</span>
          </div>
          <div className="doc-list">
            {allDocs.slice(0, 12).map((d) => {
              const attached = attachedIds.includes(d.id);
              return (
                <div
                  key={d.id}
                  className={`doc-item ${attached ? "doc-item--attached" : ""}`}
                  title={`${d.pages} pages · ${d.chunks} chunks`}
                >
                  <button
                    type="button"
                    className="doc-item-main"
                    onClick={() => (attached ? onDetachDoc(d.id) : onAttachDoc(d))}
                  >
                    <span className="doc-item-name">{d.filename}</span>
                    <span className="doc-item-pages">{d.pages}p</span>
                  </button>
                  <button
                    type="button"
                    className="doc-item-delete"
                    onClick={() => onDeleteDoc(d.id)}
                    aria-label="Delete document"
                    title="Delete document"
                  >
                    <TrashIcon />
                  </button>
                </div>
              );
            })}
          </div>
          <div className="sidebar-divider" />
        </div>
      )}

      <nav className="thread-list" ref={historyRef}>
        {threads.length === 0 ? (
          <p className="empty">No threads yet. Ask anything to start.</p>
        ) : (
          Object.entries(groups).map(([label, list]) =>
            list.length === 0 ? null : (
              <div key={label} className="thread-group">
                <div className="thread-group-label">{label}</div>
                {list.map((t) => (
                  <div
                    key={t.id}
                    className={`thread-item ${t.id === currentThreadId ? "thread-item--active" : ""}`}
                    onClick={() => onSelectThread(t.id)}
                    role="button"
                    tabIndex={0}
                  >
                    <span className="thread-title">{t.title}</span>
                    <button
                      className="thread-delete"
                      onClick={(e) => onDeleteThread(t.id, e)}
                      title="Delete"
                      aria-label="Delete thread"
                    >
                      <TrashIcon />
                    </button>
                  </div>
                ))}
              </div>
            )
          )
        )}
      </nav>

      <div className="sidebar-foot">
        <ThemeToggle theme={theme} setTheme={setTheme} />
        <span className="foot-label">SearXNG · gpt-oss-120b</span>
      </div>
    </aside>
  );
}
