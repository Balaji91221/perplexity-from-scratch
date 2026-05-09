// Tiny pub-sub toast store. No React import — components subscribe via a hook.
//
// Usage from anywhere:
//   import { toast } from "../lib/toast";
//   toast.success("Document uploaded");
//   toast.error("Upload failed");
//   toast.info("Thread cleared");

let nextId = 1;
const listeners = new Set();
let toasts = [];

function emit() {
  for (const fn of listeners) fn(toasts);
}

function push(kind, message, ttl = 3500) {
  const id = nextId++;
  toasts = [...toasts, { id, kind, message }];
  emit();
  setTimeout(() => {
    toasts = toasts.filter((t) => t.id !== id);
    emit();
  }, ttl);
}

export const toast = {
  success: (m) => push("success", m),
  error: (m) => push("error", m, 5000),
  info: (m) => push("info", m),
};

export function subscribe(fn) {
  listeners.add(fn);
  fn(toasts);
  return () => listeners.delete(fn);
}
