// Fullscreen modal for viewing a screenshot at native size.

import { useEffect } from "react";

export default function Lightbox({ src, caption, onClose }) {
  useEffect(() => {
    const onEsc = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);

  return (
    <div className="lightbox" onClick={onClose} role="dialog" aria-modal="true">
      <button className="lightbox-close" onClick={onClose} aria-label="Close">×</button>
      <figure className="lightbox-figure" onClick={(e) => e.stopPropagation()}>
        <img src={src} alt={caption || "screenshot"} />
        {caption && <figcaption>{caption}</figcaption>}
      </figure>
    </div>
  );
}
