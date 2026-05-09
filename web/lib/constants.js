// Static UI configuration. Pure data, no React imports.

import {
  BoltIcon, BeakerIcon, DesktopIcon,
} from "../components/icons";

// Brand identity — change here to rebrand the whole app.
export const BRAND = {
  name: "Lumen",
  tagline: "an open-source answer engine",
  hero: {
    title: ["Where knowledge", "begins."],   // second word gets the gradient accent
    sub: "Cited answers from the live web — multi-agent, streaming, open-source.",
  },
  features: ["Cited sources", "Multi-agent", "Streaming", "Open-source"],
};

// Suggestion cards on the home view. `kind` drives the small icon shown on each card.
export const SUGGESTIONS = [
  { cmd: "explain",   kind: "science", text: "How does CRISPR gene editing work?" },
  { cmd: "compare",   kind: "compare", text: "Compare React, Vue, and Svelte in 2026" },
  { cmd: "latest",    kind: "news",    text: "Latest milestones for the JWST" },
  { cmd: "summarize", kind: "history", text: "Causes of the 2008 financial crisis" },
];

// Mode dropdown entries.
export const MODE_META = {
  quick:    { label: "Quick",    sub: "Single search → fast answer",      Icon: BoltIcon },
  deep:     { label: "Deep",     sub: "Multi-step research agent",        Icon: BeakerIcon },
  computer: { label: "Computer", sub: "You watch the agent browse pages", Icon: DesktopIcon },
};

// Header focus tabs (passed through to SearXNG).
export const FOCUS_TABS = [
  { key: "web",      label: "Web" },
  { key: "academic", label: "Academic" },
  { key: "news",     label: "News" },
  { key: "reddit",   label: "Reddit" },
];

// Slash-prefixed shortcuts that prepend a system-style instruction to the user's question.
export const SKILLS = [
  {
    cmd: "tldr",
    label: "TL;DR",
    desc: "Ultra-concise 3-bullet summary",
    prompt: "Answer in TL;DR form: at most 3 short bullet points, no preamble. Then include citations.\n\nQuestion: ",
  },
  {
    cmd: "explain",
    label: "Explain like I'm 5",
    desc: "Plain-language explanation",
    prompt: "Explain in simple, plain language a curious 12-year-old would understand. Avoid jargon. Use a concrete analogy if helpful. Keep it short.\n\nQuestion: ",
  },
  {
    cmd: "cite",
    label: "MLA citations",
    desc: "Format every source as MLA",
    prompt: "Answer concisely, then provide a numbered MLA-style works-cited list of every source used at the bottom under \"Works Cited\".\n\nQuestion: ",
  },
  {
    cmd: "code",
    label: "Write code",
    desc: "Working code with a brief why",
    prompt: "Reply with a working code snippet inside a fenced code block. Default to Python unless the question specifies otherwise. Add a one-line comment above explaining what it does, and one line below describing how to run it.\n\nTask: ",
  },
  {
    cmd: "translate",
    label: "Translate",
    desc: "Specify target language in your message",
    prompt: "Translate the following message. If a target language is not specified, ask which language. Preserve formatting and proper nouns.\n\nText: ",
  },
  {
    cmd: "outline",
    label: "Outline",
    desc: "Hierarchical outline of the topic",
    prompt: "Produce a hierarchical outline (max 3 levels deep, ~12 leaf items total) covering the topic. Use markdown headings and nested bullet lists. Cite sources where possible.\n\nTopic: ",
  },
  {
    cmd: "flashcards",
    label: "Flashcards",
    desc: "Q&A flashcards on the topic",
    prompt: "Generate 8 study flashcards on the topic. Format as a markdown table with two columns: Question | Answer. Keep each cell to one sentence. Cite the source [N] for the answer column where applicable.\n\nTopic: ",
  },
  {
    cmd: "critique",
    label: "Critique",
    desc: "Strengths, weaknesses, and risks",
    prompt: "Critique the following idea or text. Format as three sections — **Strengths**, **Weaknesses**, **Risks** — each with 2–4 short bullets. Be candid, not flattering. Cite sources [N] for any factual claims.\n\nSubject: ",
  },
  {
    cmd: "extract",
    label: "Extract data",
    desc: "Pull structured fields as a table",
    prompt: "Extract the structured data from the source(s) and present as a single markdown table. Infer column names from the data. If fields are uncertain, write \"unknown\" rather than guessing. Cite [N] in a final source column.\n\nWhat to extract: ",
  },
];

// Fallback agent list — replaced at runtime by GET /agents.
export const DEFAULT_AGENTS = [
  { key: "generalist",   label: "Generalist",   blurb: "Balanced answer engine." },
  { key: "researcher",   label: "Researcher",   blurb: "Citation-heavy research." },
  { key: "coder",        label: "Coder",        blurb: "Working code first." },
  { key: "analyst",      label: "Analyst",      blurb: "Tidy tables." },
  { key: "orchestrator", label: "Orchestrator", blurb: "Multi-agent delegation.", is_orchestrator: true },
];
