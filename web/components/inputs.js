// File-upload affordances for the input bar.

import { useRef } from "react";
import { FileIcon, PaperclipIcon, Spinner } from "./icons";

export function UploadButton({ uploading, onUpload }) {
  const ref = useRef(null);
  return (
    <>
      <input
        ref={ref}
        type="file"
        accept="application/pdf,.pdf"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onUpload(f);
          e.target.value = "";
        }}
      />
      <button
        type="button"
        className="upload-btn"
        onClick={() => ref.current?.click()}
        disabled={uploading}
        aria-label="Upload PDF"
        title="Upload PDF"
      >
        {uploading ? <Spinner /> : <PaperclipIcon />}
      </button>
    </>
  );
}

export function AttachmentStrip({ docs, uploading, uploadError, onRemove }) {
  if (!docs.length && !uploading && !uploadError) return null;
  return (
    <div className="attachments">
      {docs.map((d) => (
        <div key={d.id} className="attachment-chip" title={`${d.pages} pages · ${d.chunks} chunks`}>
          <FileIcon />
          <span className="attachment-name">{d.filename}</span>
          <span className="attachment-meta">{d.pages}p</span>
          <button
            type="button"
            className="attachment-remove"
            onClick={() => onRemove(d.id)}
            aria-label="Remove attachment"
          >
            ×
          </button>
        </div>
      ))}
      {uploading && (
        <div className="attachment-chip attachment-chip--uploading">
          <Spinner /> <span>Uploading…</span>
        </div>
      )}
      {uploadError && <div className="attachment-error">{uploadError}</div>}
    </div>
  );
}
