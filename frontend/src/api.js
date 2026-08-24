// Thin fetch wrapper: same-origin cookies (withCredentials), JSON.
const BASE = '';

export async function api(path, { method = 'GET', body, raw = false } = {}) {
  const isForm = body instanceof FormData;
  const res = await fetch(BASE + path, {
    method,
    credentials: 'include',
    headers: (!raw && !isForm && body) ? { 'Content-Type': 'application/json' } : undefined,
    body: (raw || isForm) ? body : (body ? JSON.stringify(body) : undefined),
  });
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || `${res.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

export const SSE_BASE = '';
