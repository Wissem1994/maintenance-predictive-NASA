const BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/$/, '');
export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(BASE + path, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Paramètres invalides. Vérifiez les champs.');
  }
  return response.json() as Promise<T>;
}
export const websocketUrl = BASE.replace(/^http/, 'ws') + '/ws';
