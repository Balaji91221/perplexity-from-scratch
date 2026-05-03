// Walks markdown-rendered children, replaces inline `[N]` (or full-width 【N】)
// markers with <CitationPill> components linking to the matching source.

import CitationPill from "../components/CitationPill";

export function processCitations(children, sourceByN, onOpenPdf) {
  const re = /[\[【](\d+)[\]】]/g;

  function transform(node, keyPrefix) {
    if (typeof node === "string") {
      const out = [];
      let last = 0;
      let m;
      let i = 0;
      while ((m = re.exec(node)) !== null) {
        if (m.index > last) out.push(node.slice(last, m.index));
        const n = parseInt(m[1], 10);
        const src = sourceByN.get(n);
        out.push(
          <CitationPill
            key={`${keyPrefix}-${i}`}
            n={n}
            source={src}
            onOpenPdf={onOpenPdf}
          />
        );
        last = re.lastIndex;
        i += 1;
      }
      if (last < node.length) out.push(node.slice(last));
      re.lastIndex = 0;
      return out.length ? out : node;
    }
    return node;
  }

  if (Array.isArray(children)) {
    return children.flatMap((c, idx) => {
      const r = transform(c, `c${idx}`);
      return Array.isArray(r) ? r : [r];
    });
  }
  return transform(children, "c0");
}
