// Global toast renderer. Mounted once in pages/index.js.

import { useEffect, useState } from "react";

import { subscribe } from "../lib/toast";

export default function Toaster() {
  const [toasts, setToasts] = useState([]);
  useEffect(() => subscribe(setToasts), []);

  if (toasts.length === 0) return null;

  return (
    <div className="toaster" aria-live="polite" aria-atomic="true">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.kind}`} role="status">
          <span className="toast-dot" aria-hidden="true" />
          <span className="toast-message">{t.message}</span>
        </div>
      ))}
    </div>
  );
}
