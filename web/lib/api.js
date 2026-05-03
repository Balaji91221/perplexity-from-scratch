// Network layer + device-UUID auth.
// Every call goes through `api()` so the X-User-Id header rides along.

export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function makeUUIDv4() {
  // Fallback when crypto.randomUUID isn't available.
  const b = new Uint8Array(16);
  crypto.getRandomValues(b);
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}

// Stable UUID per browser. Sent as X-User-Id header.
// NOT real authentication — just a per-device tag for data isolation.
export function getDeviceUserId() {
  if (typeof window === "undefined") return null;
  let id = window.localStorage.getItem("pc-user-id");
  if (!id || !UUID_RE.test(id)) {
    id = (crypto.randomUUID && crypto.randomUUID()) || makeUUIDv4();
    window.localStorage.setItem("pc-user-id", id);
  }
  return id;
}

export function api(path, init = {}) {
  const headers = new Headers(init.headers || {});
  const uid = getDeviceUserId();
  if (uid) headers.set("X-User-Id", uid);
  return fetch(`${API}${path}`, { ...init, headers });
}
