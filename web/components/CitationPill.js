// Inline `[N]` citation. Web sources open in a new tab; doc sources open the
// PDF side panel via `onOpenPdf`.

export default function CitationPill({ n, source, onOpenPdf }) {
  if (!source) return <span className="cite cite--missing">[{n}]</span>;
  if (source.type === "doc") {
    return (
      <button
        type="button"
        className="cite cite--doc"
        title={`${source.title} — open PDF`}
        onClick={() =>
          onOpenPdf?.({
            docId: source.doc_id,
            page: source.page || 1,
            filename: source.filename,
          })
        }
      >
        {n}
      </button>
    );
  }
  return (
    <a className="cite" href={source.url} target="_blank" rel="noreferrer" title={source.title || source.url}>
      {n}
    </a>
  );
}
