// Source cards shown above the answer. Web cards have favicons; doc cards
// have a teal file icon and a Page badge, and clicking opens the PDF panel.

import { useMemo } from "react";
import { FileIcon } from "./icons";

export function SourceCard({ source, onOpenPdf }) {
  const isDoc = source.type === "doc";

  const hostname = useMemo(() => {
    if (isDoc) return source.filename || "document";
    try {
      return new URL(source.url).hostname.replace(/^www\./, "");
    } catch {
      return source.url;
    }
  }, [source.url, isDoc, source.filename]);

  if (isDoc) {
    return (
      <button
        type="button"
        className="source-card source-card--doc"
        title={`${source.title} — click to open PDF`}
        onClick={() => onOpenPdf?.({ docId: source.doc_id, page: source.page || 1, filename: source.filename })}
      >
        <div className="source-card-head">
          <span className="source-favicon source-favicon--doc"><FileIcon /></span>
          <span className="source-domain">{source.filename}</span>
          <span className="source-num">{source.n}</span>
        </div>
        <div className="source-title">
          {source.page ? `Page ${source.page}` : "Document passage"}
        </div>
        {source.snippet && <div className="source-snippet">{source.snippet}</div>}
      </button>
    );
  }

  const favicon = `https://www.google.com/s2/favicons?domain=${hostname}&sz=64`;
  return (
    <a className="source-card" href={source.url} target="_blank" rel="noreferrer" title={source.title}>
      <div className="source-card-head">
        <img className="source-favicon" src={favicon} alt="" loading="lazy" />
        <span className="source-domain">{hostname}</span>
        <span className="source-num">{source.n}</span>
      </div>
      <div className="source-title">{source.title}</div>
    </a>
  );
}

export function SourceSkeleton() {
  return (
    <div className="source-grid">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="source-card source-card--skeleton">
          <div className="skel skel-line" style={{ width: "60%" }} />
          <div className="skel skel-line" style={{ width: "90%", marginTop: 8 }} />
          <div className="skel skel-line" style={{ width: "75%", marginTop: 4 }} />
        </div>
      ))}
    </div>
  );
}

export function AnswerSkeleton() {
  return (
    <div className="answer-skeleton">
      <div className="skel skel-line" style={{ width: "92%" }} />
      <div className="skel skel-line" style={{ width: "85%" }} />
      <div className="skel skel-line" style={{ width: "70%" }} />
    </div>
  );
}
