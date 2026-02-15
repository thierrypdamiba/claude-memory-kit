const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:7749";

let _getToken: (() => Promise<string | null>) | null = null;

export function setTokenProvider(fn: () => Promise<string | null>) {
  _getToken = fn;
}

export interface Memory {
  id: string;
  created: string;
  gate: string;
  person: string | null;
  project: string | null;
  confidence: number;
  last_accessed: string;
  access_count: number;
  decay_class: string;
  content: string;
}

export interface Stats {
  total: number;
  by_gate: Record<string, number>;
  has_identity: boolean;
}

export interface RelatedNode {
  id: string;
  relation: string;
  preview: string;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created: string;
  last_used: string | null;
  revoked: number;
}

export interface SetupInfo {
  key: string;
  user_id: string;
  command: string;
  mcp_config: Record<string, unknown>;
}

export interface Rule {
  id: string;
  user_id: string;
  scope: string;
  condition: string;
  enforcement: string;
  created: string;
  last_triggered: string | null;
}

async function headers(): Promise<HeadersInit> {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (_getToken) {
    const token = await _getToken();
    if (token) h["Authorization"] = `Bearer ${token}`;
  }
  return h;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    cache: "no-store",
    headers: await headers(),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: await headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function put<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "PUT",
    headers: await headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "PATCH",
    headers: await headers(),
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

async function del<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    method: "DELETE",
    headers: await headers(),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  // Auth
  me: () => get<{ user: Record<string, string> }>("/api/auth/me"),

  // API keys
  createKey: (name: string) =>
    post<{ key: { id: string; key: string; prefix: string } }>("/api/keys", { name }),
  listKeys: () => get<{ keys: ApiKey[] }>("/api/keys"),
  revokeKey: (id: string) => del<{ revoked: boolean }>(`/api/keys/${id}`),

  // Memories
  memories: (limit = 50, offset = 0) =>
    get<{ memories: Memory[] }>(`/api/memories?limit=${limit}&offset=${offset}`),
  memory: (id: string) => get<Memory>(`/api/memories/${id}`),
  search: (query: string) => post<{ result: string }>("/api/search", { query }),
  identity: () => get<{ identity: string }>("/api/identity"),
  graph: (id: string) => get<{ related: RelatedNode[] }>(`/api/graph/${id}`),
  stats: () => get<Stats>("/api/stats"),
  reflect: () => post<{ result: string }>("/api/reflect", {}),
  updateIdentity: (content: string) =>
    put<{ result: string }>("/api/identity", { content }),
  updateMemory: (id: string, updates: { content?: string; gate?: string; person?: string; project?: string }) =>
    patch<{ result: string }>(`/api/memories/${id}`, updates),
  mode: () => get<{ mode: string; vector_store: string }>("/api/mode"),
  forget: (id: string, reason: string) =>
    del<{ result: string }>(`/api/memories/${id}?reason=${encodeURIComponent(reason)}`),
  create: (content: string, gate: string, person?: string, project?: string) =>
    post<{ result: string }>("/api/memories", { content, gate, person, project }),

  // Rules
  listRules: () => get<{ rules: Rule[] }>("/api/rules"),
  createRule: (condition: string, scope?: string, enforcement?: string) =>
    post<{ rule: Rule }>("/api/rules", { condition, scope: scope || "global", enforcement: enforcement || "suggest" }),
  updateRule: (id: string, updates: { scope?: string; condition?: string; enforcement?: string }) =>
    put<{ result: string }>(`/api/rules/${id}`, updates),
  deleteRule: (id: string) => del<{ result: string }>(`/api/rules/${id}`),

  // Pin
  pin: (id: string) => post<{ result: string }>(`/api/memories/${id}/pin`, {}),
  unpin: (id: string) => del<{ result: string }>(`/api/memories/${id}/pin`),

  // Setup
  getInitKey: () => post<SetupInfo>("/api/setup/init-key", {}),

  // Data migration
  checkLocalData: () =>
    get<{ has_local_data: boolean; counts: Record<string, number> }>("/api/local-data-check"),
  claimLocal: () =>
    post<{ migrated: Record<string, number>; message: string }>("/api/claim-local", {}),
};
