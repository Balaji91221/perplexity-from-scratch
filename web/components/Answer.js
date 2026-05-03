// Markdown-rendered answer with clickable citation pills.
// Citations from web sources link out; doc citations open the PDF side panel.

import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { processCitations } from "../lib/citations";

export default function Answer({ text, sources, onOpenPdf }) {
  const sourceByN = useMemo(() => {
    const m = new Map();
    for (const s of sources || []) m.set(s.n, s);
    return m;
  }, [sources]);

  return (
    <div className="answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: (props) => <p>{processCitations(props.children, sourceByN, onOpenPdf)}</p>,
          li: (props) => <li>{processCitations(props.children, sourceByN, onOpenPdf)}</li>,
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer">{children}</a>
          ),
          code: ({ inline, children, ...rest }) =>
            inline ? (
              <code className="inline-code" {...rest}>{children}</code>
            ) : (
              <pre className="code-block"><code {...rest}>{children}</code></pre>
            ),
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
