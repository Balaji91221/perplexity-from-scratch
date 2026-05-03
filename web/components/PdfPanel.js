// 560px right-side panel that renders an uploaded PDF in an iframe, jumped
// to a specific page via the `#page=N` URL fragment.

import { useEffect } from "react";

import { API, getDeviceUserId } from "../lib/api";
import { FileIcon } from "./icons";

export default function PdfPanel({ view, onClose }) {
  useEffect(() => {
    const onEsc = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  // Iframes can't send custom headers; the backend accepts ?uid= as a fallback
  // for the same per-device auth.
  const uid = getDeviceUserId();
  const src = `${API}/documents/${view.docId}/file?uid=${uid}#page=${view.page || 1}`;

  return (
    <aside className="pdf-panel" role="dialog" aria-label="PDF viewer">
      <header className="pdf-panel-head">
        <div className="pdf-panel-title">
          <FileIcon />
          <span>{view.filename}</span>
          {view.page && <span className="pdf-panel-page">Page {view.page}</span>}
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close PDF" title="Close (Esc)">
          ×
        </button>
      </header>
      <iframe
        key={`${view.docId}-${view.page}`}
        className="pdf-frame"
        src={src}
        title={view.filename}
      />
    </aside>
  );
}
