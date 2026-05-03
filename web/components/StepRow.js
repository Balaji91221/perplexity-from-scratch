// One row in the agent's "Steps" section. Renders the running spinner /
// completed checkmark, a tool-specific label, a result badge, and (in
// Computer Use mode) a clickable screenshot thumbnail.

import { useState } from "react";
import { CheckIcon, DotIcon, Spinner } from "./icons";
import Lightbox from "./Lightbox";

export function shortDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url || "";
  }
}

export function parseMcpName(name) {
  const rest = name.slice("mcp_".length);
  const idx = rest.indexOf("__");
  if (idx === -1) return { server: rest, tool: "" };
  return { server: rest.slice(0, idx), tool: rest.slice(idx + 2) };
}

export default function StepRow({ step, computer }) {
  const { tool, args, result, status } = step;
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const isMcp = typeof tool === "string" && tool.startsWith("mcp_");
  const mcpInfo = isMcp ? parseMcpName(tool) : null;

  const label =
    tool === "search"
      ? `Searching: "${args?.query || ""}"`
      : tool === "read_url"
      ? `Reading ${shortDomain(args?.url)}`
      : tool === "browse_url"
      ? (computer ? `Looking at ${shortDomain(args?.url)}` : `Browsing ${shortDomain(args?.url)}`)
      : tool === "read_doc"
      ? `Searching documents: "${args?.query || ""}"`
      : isMcp
      ? `MCP · ${mcpInfo.server}: ${mcpInfo.tool}`
      : tool;

  let detail = null;
  if (status === "done" && result) {
    if (tool === "search" && Array.isArray(result.results)) {
      detail = `${result.results.length} results`;
    } else if (tool === "read_doc" && typeof result.hits === "number") {
      detail = `${result.hits} passages`;
    } else if (isMcp) {
      detail = result.error ? "error" : (result.ok === false ? "empty" : "ok");
    } else if (result.error) {
      detail = "error";
    } else if (result.ok) {
      detail = result.chars ? `${result.chars} chars` : "ok";
    } else if (result.ok === false) {
      detail = "empty";
    }
  }

  const screenshot = result?.screenshot;

  return (
    <>
      <li className={`step-row step-row--${status} ${screenshot ? "step-row--has-shot" : ""}`}>
        <span className="step-icon">
          {status === "running" ? <Spinner /> : status === "done" ? <CheckIcon /> : <DotIcon />}
        </span>
        <span className="step-label">{label}</span>
        {detail && <span className="step-detail">{detail}</span>}
        {screenshot && (
          <button
            type="button"
            className="step-shot"
            onClick={() => setLightboxOpen(true)}
            title="View full screenshot"
            aria-label="View screenshot"
          >
            <img src={screenshot} alt="" loading="lazy" />
          </button>
        )}
      </li>
      {lightboxOpen && screenshot && (
        <Lightbox src={screenshot} caption={label} onClose={() => setLightboxOpen(false)} />
      )}
    </>
  );
}
