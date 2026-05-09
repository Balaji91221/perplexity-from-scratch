// Right-side autonomous-crawl panel.
// User gives a start URL + plain-English goal; the agent drives a real
// browser through the site and streams events back: page visits, actions,
// findings, and a final synthesis.

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api } from "../lib/api";
import { PlayIcon, RobotIcon, StopIcon } from "./icons";

function shortHost(url) {
  try { return new URL(url).host.replace(/^www\./, ""); } catch { return url; }
}

function ActionChip({ action }) {
  return (
    <span className="ax-chip" title={action.rationale || ""}>
      <span className="ax-chip-kind">{action.kind}</span>
      {action.target && <span className="ax-chip-target">{String(action.target).slice(0, 40)}</span>}
    </span>
  );
}

function PageBlock({ page }) {
  return (
    <div className="ax-page">
      <div className="ax-page-head">
        <span className="ax-page-num">#{page.index}</span>
        <a className="ax-page-url" href={page.url} target="_blank" rel="noreferrer" title={page.url}>
          {shortHost(page.url)}
        </a>
        {page.title && <span className="ax-page-title">{page.title}</span>}
      </div>
      {page.screenshot && (
        <div className="ax-shot">
          <img src={page.screenshot} alt={page.title || page.url} />
        </div>
      )}
      {page.actions.length > 0 && (
        <div className="ax-action-list">
          {page.actions.map((a, i) => <ActionChip key={i} action={a} />)}
        </div>
      )}
      {page.findings.length > 0 && (
        <ul className="ax-findings">
          {page.findings.map((f, i) => (
            <li key={i} className="ax-finding">
              {f.summary && <div className="ax-finding-summary">{f.summary}</div>}
              {f.fields && Object.keys(f.fields).length > 0 && (
                <dl className="ax-fields">
                  {Object.entries(f.fields).map(([k, v]) => (
                    <div key={k} className="ax-field">
                      <dt>{k}</dt>
                      <dd>{String(v)}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function AssistantPanel({ open, onClose }) {
  const [startUrl, setStartUrl] = useState("");
  const [goal, setGoal] = useState("");
  const [sameDomain, setSameDomain] = useState(true);
  const [pages, setPages] = useState([]);     // [{ index, url, title, screenshot, actions, findings }]
  const [synthesis, setSynthesis] = useState("");
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState("");
  const [summary, setSummary] = useState(null);
  const abortRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!open) return;
    const onEsc = (e) => e.key === "Escape" && !running && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [open, running, onClose]);

  useEffect(() => {
    if (running) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [pages, synthesis, running]);

  function reset() {
    setPages([]);
    setSynthesis("");
    setSummary(null);
    setErr("");
  }

  function patchLastPage(patch) {
    setPages((ps) => {
      if (ps.length === 0) return ps;
      const next = [...ps];
      const last = next[next.length - 1];
      next[next.length - 1] = typeof patch === "function" ? patch(last) : { ...last, ...patch };
      return next;
    });
  }

  function handleEvent(event, data) {
    if (event === "crawl_start") {
      // no-op; UI already shows "running"
    } else if (event === "crawl_page") {
      try {
        const p = JSON.parse(data);
        setPages((ps) => [...ps, {
          index: ps.length + 1,
          url: p.url,
          title: p.title || "",
          screenshot: p.screenshot || null,
          actions: [],
          findings: [],
        }]);
      } catch {}
    } else if (event === "crawl_action") {
      try {
        const a = JSON.parse(data);
        patchLastPage((p) => ({ ...p, actions: [...p.actions, a] }));
      } catch {}
    } else if (event === "crawl_action_result") {
      try {
        const r = JSON.parse(data);
        if (r.screenshot) patchLastPage({ screenshot: r.screenshot });
        if (r.url) patchLastPage({ url: r.url });
        if (r.title) patchLastPage({ title: r.title });
      } catch {}
    } else if (event === "crawl_finding") {
      try {
        const f = JSON.parse(data);
        patchLastPage((p) => ({ ...p, findings: [...p.findings, f] }));
      } catch {}
    } else if (event === "crawl_link_plan") {
      // Could surface "Next: …", but kept silent to avoid clutter.
    } else if (event === "crawl_summary") {
      try { setSummary(JSON.parse(data)); } catch {}
    } else if (event === "crawl_synthesis") {
      setSynthesis((s) => s + data);
    } else if (event === "error") {
      setErr(data);
    } else if (event === "crawl_done") {
      setRunning(false);
    }
  }

  async function start() {
    if (!startUrl.trim() || !goal.trim() || running) return;
    reset();
    setRunning(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      const res = await api(`/assistant/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          start_url: startUrl.trim(),
          goal: goal.trim(),
          same_domain: sameDomain,
        }),
        signal: ctrl.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");

        let idx;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          if (!frame.trim()) continue;
          let event = "message";
          const dataLines = [];
          for (const line of frame.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
          }
          handleEvent(event, dataLines.join("\n"));
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") setErr(e.message || String(e));
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }

  function stop() {
    abortRef.current?.abort();
    setRunning(false);
  }

  if (!open) return null;

  return (
    <aside className="ax-panel" role="dialog" aria-label="Assistant — autonomous crawl">
      <header className="ax-head">
        <div className="ax-head-title">
          <RobotIcon />
          <span>Assistant</span>
          {running && <span className="ax-pill ax-pill--running">running</span>}
          {!running && summary && (
            <span className="ax-pill">
              {summary.pages_visited} {summary.pages_visited === 1 ? "page" : "pages"} · {summary.findings_count} {summary.findings_count === 1 ? "finding" : "findings"}
            </span>
          )}
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close" title="Close (Esc)">×</button>
      </header>

      <div className="ax-form">
        <input
          className="ax-input"
          placeholder="https://stripe.com"
          value={startUrl}
          onChange={(e) => setStartUrl(e.target.value)}
          disabled={running}
        />
        <textarea
          className="ax-textarea"
          placeholder="What should the assistant do? (e.g., find pricing for the Pro plan and any free-trial details)"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          rows={2}
          disabled={running}
        />
        <div className="ax-controls">
          <label className="ax-check">
            <input
              type="checkbox"
              checked={sameDomain}
              onChange={(e) => setSameDomain(e.target.checked)}
              disabled={running}
            />
            <span>Stay on the same site</span>
          </label>
          {running ? (
            <button className="ax-btn ax-btn--stop" onClick={stop}>
              <StopIcon /> Stop
            </button>
          ) : (
            <button
              className="ax-btn ax-btn--start"
              onClick={start}
              disabled={!startUrl.trim() || !goal.trim()}
            >
              <PlayIcon /> Start
            </button>
          )}
        </div>
      </div>

      <div className="ax-body">
        {err && <div className="ax-error">{err}</div>}
        {pages.length === 0 && !running && !err && (
          <div className="ax-empty">
            <div className="ax-empty-title">Autonomous web crawl</div>
            <div className="ax-empty-sub">
              Drop in a URL and tell the assistant what to find. It opens a real browser, walks through pages, and streams back what it learns.
            </div>
          </div>
        )}
        {pages.map((p) => <PageBlock key={p.index} page={p} />)}
        {synthesis && (
          <section className="ax-synthesis">
            <h3>Answer</h3>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{synthesis}</ReactMarkdown>
          </section>
        )}
        <div ref={bottomRef} />
      </div>
    </aside>
  );
}
