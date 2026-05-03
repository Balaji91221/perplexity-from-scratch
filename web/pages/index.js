// Top-level Home component. Owns app state and the SSE stream from /ask.
//
// Frontend file map:
//   lib/
//     api.js         — fetch wrapper + getDeviceUserId
//     constants.js   — SUGGESTIONS / MODE_META / FOCUS_TABS / SKILLS / DEFAULT_AGENTS
//     citations.js   — processCitations (markdown → [N] pills)
//   components/
//     icons.js          — every inline SVG icon
//     CitationPill.js   — clickable [N] pill
//     Answer.js         — markdown answer with citations
//     sources.js        — SourceCard / SourceSkeleton / AnswerSkeleton
//     Section.js        — labeled section + StageBadge
//     Lightbox.js       — full-size screenshot modal
//     StepRow.js        — one row in agent's "Steps" list
//     SubAgentCard.js   — orchestrator sub-agent card
//     Turn.js           — full Q&A turn (composes the above)
//     Sidebar.js        — left rail (nav + MCP + Documents + Threads)
//     Header.js         — top header (sidebar toggle + focus tabs)
//     PdfPanel.js       — right side panel rendering an uploaded PDF
//     dropdowns.js      — ModeDropdown + AgentDropdown
//     skills.js         — SkillsAutocomplete + ActiveSkillChip
//     inputs.js         — UploadButton + AttachmentStrip
//     HomeView.js       — empty-state landing
//     FollowUpBar.js    — sticky bottom input
//     FocusTabs.js      — Web/Academic/News/Reddit tabs
//     ThemeToggle.js    — dark/light pill in sidebar footer

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "../lib/api";
import { DEFAULT_AGENTS } from "../lib/constants";
import FollowUpBar from "../components/FollowUpBar";
import Header from "../components/Header";
import HomeView from "../components/HomeView";
import PdfPanel from "../components/PdfPanel";
import Sidebar from "../components/Sidebar";
import Turn from "../components/Turn";

// turn = { question, mode, agent, sources, answer, stage, error, steps, plan, subAgents, phase }
function newTurn(question, mode, agentKey) {
  return {
    question,
    mode: mode || "quick",
    agent: agentKey || "generalist",
    sources: [],
    answer: "",
    stage: "searching",
    error: "",
    steps: [],          // top-level steps (non-orchestrator)
    plan: null,         // orchestrator: [{agent, subtask}]
    subAgents: [],      // orchestrator: [{agent, subtask, status, steps:[], answer}]
    phase: null,        // orchestrator: planning | running | synthesizing | done
  };
}

export default function Home() {
  // ---------- State ----------
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("quick");           // quick | deep | computer
  const [focus, setFocus] = useState("web");           // web | academic | news | reddit
  const [theme, setTheme] = useState("dark");          // dark | light
  const [threadId, setThreadId] = useState(null);
  const [turns, setTurns] = useState([]);
  const [threads, setThreads] = useState([]);
  const [docs, setDocs] = useState([]);                // attached docs for the next /ask
  const [allDocs, setAllDocs] = useState([]);          // every doc this device has uploaded
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [skill, setSkill] = useState(null);            // active /skill (prepends prompt)
  const [pdfView, setPdfView] = useState(null);        // open the PDF panel
  const [agentKey, setAgentKey] = useState("generalist");
  const [agents, setAgents] = useState(DEFAULT_AGENTS);
  const [mcpServers, setMcpServers] = useState([]);
  const inputRef = useRef(null);
  const bottomRef = useRef(null);

  const lastTurn = turns[turns.length - 1];
  const busy = lastTurn && ["searching", "reading", "thinking", "answering"].includes(lastTurn.stage);

  // ---------- Theme persistence ----------
  useEffect(() => {
    const saved = typeof window !== "undefined" && window.localStorage.getItem("pc-theme");
    if (saved === "light" || saved === "dark") setTheme(saved);
  }, []);
  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.dataset.theme = theme;
      window.localStorage.setItem("pc-theme", theme);
    }
  }, [theme]);

  // ---------- Background data ----------
  const refreshThreads = useCallback(async () => {
    try {
      const res = await api(`/threads`);
      if (res.ok) setThreads(await res.json());
    } catch {}
  }, []);

  const refreshAllDocs = useCallback(async () => {
    try {
      const res = await api(`/documents`);
      if (res.ok) setAllDocs(await res.json());
    } catch {}
  }, []);

  const refreshMcp = useCallback(async () => {
    try {
      const res = await api(`/mcp/servers`);
      if (res.ok) setMcpServers(await res.json());
    } catch {}
  }, []);

  const refreshAgents = useCallback(async () => {
    try {
      const res = await api(`/agents`);
      if (res.ok) {
        const list = await res.json();
        if (Array.isArray(list) && list.length) setAgents(list);
      }
    } catch {}
  }, []);

  useEffect(() => {
    refreshThreads();
    refreshAllDocs();
    refreshMcp();
    refreshAgents();
  }, [refreshThreads, refreshAllDocs, refreshMcp, refreshAgents]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [threadId, turns.length === 0]);

  useEffect(() => {
    if (lastTurn?.stage === "answering") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [turns]);

  // When user picks a non-generalist agent, snap mode + focus to its defaults.
  useEffect(() => {
    const cfg = agents.find((a) => a.key === agentKey);
    if (!cfg) return;
    if (cfg.default_mode && agentKey !== "generalist") setMode(cfg.default_mode);
    if (cfg.default_focus && agentKey !== "generalist") setFocus(cfg.default_focus);
  }, [agentKey, agents]);

  // ---------- Helpers ----------

  function updateLastTurn(patch) {
    setTurns((ts) => {
      if (ts.length === 0) return ts;
      const next = [...ts];
      const last = next[next.length - 1];
      next[next.length - 1] = typeof patch === "function" ? patch(last) : { ...last, ...patch };
      return next;
    });
  }

  function startNewThread() {
    setThreadId(null);
    setTurns([]);
    setQuery("");
    setDocs([]);
    setUploadError("");
    setTimeout(() => inputRef.current?.focus(), 0);
  }

  // ---------- /ask SSE pipeline ----------

  async function ask(q) {
    if (!q.trim() || busy) return;
    const turnMode = mode;
    const turnAgent = agentKey;
    const activeSkill = skill;
    const finalQuery = activeSkill ? activeSkill.prompt + q : q;
    setQuery("");
    setSkill(null);
    setTurns((ts) => [...ts, { ...newTurn(q, turnMode, turnAgent), skill: activeSkill }]);

    try {
      const res = await api(`/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: finalQuery,
          thread_id: threadId,
          mode: turnMode,
          focus,
          doc_ids: docs.map((d) => d.id),
          agent: turnAgent,
        }),
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
          if (frame.trim()) handleFrame(frame);
        }
      }
      updateLastTurn({ stage: "done" });
      refreshThreads();
    } catch (err) {
      updateLastTurn({ stage: "error", error: err.message || String(err) });
    }
  }

  function handleFrame(frame) {
    let event = "message";
    const dataLines = [];
    for (const line of frame.split("\n")) {
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
    }
    const data = dataLines.join("\n");

    if (event === "thread") {
      try {
        const { id } = JSON.parse(data);
        setThreadId((curr) => curr || id);
      } catch {}
    } else if (event === "sources") {
      try {
        const sources = JSON.parse(data);
        updateLastTurn({ sources, stage: "reading" });
      } catch {}
    } else if (event === "step") {
      try {
        const s = JSON.parse(data);
        updateLastTurn((t) => ({
          ...t,
          stage: "thinking",
          steps: [...t.steps, { ...s, status: "running" }],
        }));
      } catch {}
    } else if (event === "step_result") {
      try {
        const s = JSON.parse(data);
        updateLastTurn((t) => ({
          ...t,
          steps: t.steps.map((p, i) =>
            i === t.steps.length - 1 && p.step === s.step && p.tool === s.tool
              ? { ...p, result: s.result, status: "done" }
              : p
          ),
        }));
      } catch {}
    } else if (event === "token") {
      updateLastTurn((t) => ({
        ...t,
        answer: t.answer + data,
        stage: "answering",
      }));
    } else if (event === "error") {
      updateLastTurn({ error: data, stage: "error" });
    } else if (event === "agent_phase") {
      try {
        const p = JSON.parse(data);
        updateLastTurn((t) => {
          if (p.phase === "planning") return { ...t, phase: "planning", stage: "thinking" };
          if (p.phase === "synthesizing") return { ...t, phase: "synthesizing", stage: "thinking" };
          if (p.phase === "running") {
            const subAgents = [...(t.subAgents || [])];
            if (!subAgents[p.index]) {
              subAgents[p.index] = { agent: p.agent, subtask: p.subtask, status: "running", steps: [] };
            } else {
              subAgents[p.index] = { ...subAgents[p.index], status: "running" };
            }
            return { ...t, phase: "running", subAgents, stage: "thinking" };
          }
          if (p.phase === "done") {
            const subAgents = [...(t.subAgents || [])];
            if (subAgents[p.index]) {
              subAgents[p.index] = { ...subAgents[p.index], status: "done" };
            }
            return { ...t, subAgents };
          }
          return t;
        });
      } catch {}
    } else if (event === "plan") {
      try {
        const { plan } = JSON.parse(data);
        updateLastTurn((t) => {
          const subAgents = (plan || []).map((p) => ({
            agent: p.agent,
            subtask: p.subtask,
            status: "pending",
            steps: [],
          }));
          return { ...t, plan, subAgents };
        });
      } catch {}
    } else if (event === "sub_step") {
      try {
        const s = JSON.parse(data);
        updateLastTurn((t) => {
          const subAgents = [...(t.subAgents || [])];
          const idx = s.sub_index;
          if (subAgents[idx]) {
            subAgents[idx] = {
              ...subAgents[idx],
              steps: [...subAgents[idx].steps, { ...s, status: "running" }],
            };
          }
          return { ...t, subAgents };
        });
      } catch {}
    } else if (event === "sub_step_result") {
      try {
        const s = JSON.parse(data);
        updateLastTurn((t) => {
          const subAgents = [...(t.subAgents || [])];
          const idx = s.sub_index;
          if (subAgents[idx]) {
            const steps = subAgents[idx].steps.map((p, i, arr) =>
              i === arr.length - 1 && p.step === s.step && p.tool === s.tool
                ? { ...p, result: s.result, status: "done" }
                : p
            );
            subAgents[idx] = { ...subAgents[idx], steps };
          }
          return { ...t, subAgents };
        });
      } catch {}
    } else if (event === "sub_error") {
      try {
        const s = JSON.parse(data);
        updateLastTurn((t) => {
          const subAgents = [...(t.subAgents || [])];
          const idx = s.sub_index;
          if (subAgents[idx]) {
            subAgents[idx] = { ...subAgents[idx], status: "error", error: s.error };
          }
          return { ...t, subAgents };
        });
      } catch {}
    }
  }

  // ---------- Threads ----------

  async function loadThread(id) {
    try {
      const res = await api(`/threads/${id}`);
      if (!res.ok) return;
      const data = await res.json();
      const loaded = [];
      for (let i = 0; i < data.messages.length; i += 2) {
        const u = data.messages[i];
        const a = data.messages[i + 1];
        loaded.push({
          question: u?.content || "",
          mode: "quick",
          sources: a?.sources || [],
          answer: a?.content || "",
          stage: "done",
          error: "",
          steps: [],
        });
      }
      setThreadId(id);
      setTurns(loaded);
      setQuery("");
    } catch {}
  }

  async function deleteThread(id, e) {
    e.stopPropagation();
    if (!confirm("Delete this thread?")) return;
    try {
      await api(`/threads/${id}`, { method: "DELETE" });
      if (id === threadId) startNewThread();
      refreshThreads();
    } catch {}
  }

  // ---------- Documents ----------

  async function uploadFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setUploadError("Only PDF uploads are supported.");
      return;
    }
    setUploading(true);
    setUploadError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api(`/documents/upload`, { method: "POST", body: fd });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const doc = await res.json();
      setDocs((d) => [...d, doc]);
      setAllDocs((d) => [doc, ...d.filter((x) => x.id !== doc.id)]);
    } catch (err) {
      setUploadError(err.message || String(err));
    } finally {
      setUploading(false);
    }
  }

  function removeDoc(id) {
    setDocs((d) => d.filter((x) => x.id !== id));
  }

  function attachDoc(doc) {
    setDocs((d) => (d.find((x) => x.id === doc.id) ? d : [...d, doc]));
  }

  async function deleteDoc(id) {
    if (!confirm("Delete this document?")) return;
    try {
      await api(`/documents/${id}`, { method: "DELETE" });
      setAllDocs((d) => d.filter((x) => x.id !== id));
      setDocs((d) => d.filter((x) => x.id !== id));
    } catch {}
  }

  // ---------- Render ----------

  const hasActivity = turns.length > 0;

  return (
    <div className={`app ${sidebarOpen ? "app--sidebar" : ""}`}>
      <Sidebar
        open={sidebarOpen}
        threads={threads}
        currentThreadId={threadId}
        allDocs={allDocs}
        attachedIds={docs.map((d) => d.id)}
        mcpServers={mcpServers}
        mode={mode}
        setMode={setMode}
        theme={theme}
        setTheme={setTheme}
        onToggle={() => setSidebarOpen((o) => !o)}
        onNewThread={startNewThread}
        onSelectThread={loadThread}
        onDeleteThread={deleteThread}
        onAttachDoc={attachDoc}
        onDetachDoc={removeDoc}
        onDeleteDoc={deleteDoc}
      />

      <div className="content">
        <Header
          hasActivity={hasActivity}
          onToggleSidebar={() => setSidebarOpen((o) => !o)}
          sidebarOpen={sidebarOpen}
          onNewThread={startNewThread}
          focus={focus}
          setFocus={setFocus}
        />

        <main className={`main ${hasActivity ? "main--thread" : "main--home"}`}>
          {!hasActivity ? (
            <HomeView
              query={query}
              setQuery={setQuery}
              onSubmit={() => ask(query)}
              inputRef={inputRef}
              mode={mode}
              setMode={setMode}
              docs={docs}
              uploading={uploading}
              uploadError={uploadError}
              onUpload={uploadFile}
              onRemoveDoc={removeDoc}
              skill={skill}
              setSkill={setSkill}
              agentKey={agentKey}
              setAgentKey={setAgentKey}
              agents={agents}
            />
          ) : (
            <div className="thread">
              {turns.map((t, i) => (
                <Turn key={i} turn={t} isLast={i === turns.length - 1} onOpenPdf={setPdfView} />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        {hasActivity && (
          <FollowUpBar
            sidebarOpen={sidebarOpen}
            query={query}
            setQuery={setQuery}
            onSubmit={() => ask(query)}
            disabled={busy}
            inputRef={inputRef}
            mode={mode}
            setMode={setMode}
            docs={docs}
            uploading={uploading}
            uploadError={uploadError}
            onUpload={uploadFile}
            onRemoveDoc={removeDoc}
            skill={skill}
            setSkill={setSkill}
            agentKey={agentKey}
            setAgentKey={setAgentKey}
            agents={agents}
          />
        )}
      </div>

      {pdfView && <PdfPanel view={pdfView} onClose={() => setPdfView(null)} />}
    </div>
  );
}
