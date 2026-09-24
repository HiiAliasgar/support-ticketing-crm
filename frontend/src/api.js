const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";
const TOKEN_KEY = "supporttick_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, options = {}) {
  let response;
  try {
    const token = getToken();
    const headers = { "Content-Type": "application/json" };
    if (token) headers.Authorization = `Bearer ${token}`;
    response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("Network error — is the API running?");
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail)) {
        detail = body.detail
          .map((err) => `${err.loc?.join(".")}: ${err.msg}`)
          .join("; ");
      }
    } catch {
      /* non-JSON error body */
    }
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

/* --- Auth --- */
export const login = (username, password) =>
  request("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });

export const currentUser = () => request("/auth/me");

export const logout = () =>
  request("/auth/logout", { method: "POST" }).catch(() => ({}));

/* --- Tickets --- */
export const listTickets = (params = {}) => {
  const qs = new URLSearchParams();
  for (const key of ["status", "priority", "search", "page", "per_page"]) {
    if (params[key] !== undefined && params[key] !== null && params[key] !== "") {
      qs.set(key, params[key]);
    }
  }
  if (params.assignee_id !== undefined && params.assignee_id !== null) {
    qs.set("assignee_id", params.assignee_id);
  }
  const query = qs.toString();
  return request(`/tickets${query ? `?${query}` : ""}`);
};

export const getTicket = (ticketId) => request(`/tickets/${ticketId}`);

export const createTicket = (payload) =>
  request("/tickets", { method: "POST", body: JSON.stringify(payload) });

export const updateTicket = (ticketId, payload) =>
  request(`/tickets/${ticketId}`, { method: "PUT", body: JSON.stringify(payload) });

export const addNote = (ticketId, payload) =>
  request(`/tickets/${ticketId}/notes`, {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const assignTicket = (ticketId, assigneeId) =>
  request(`/tickets/${ticketId}/assign`, {
    method: "POST",
    body: JSON.stringify({ assignee_id: assigneeId }),
  });

export const deleteTicket = (ticketId) =>
  request(`/tickets/${ticketId}`, { method: "DELETE" });

export const getDashboard = () => request("/dashboard");

/* --- Team / admin --- */
export const listAgents = () => request("/agents");

export const adminListAgents = () => request("/admin/agents");
export const adminCreateAgent = (payload) =>
  request("/admin/agents", { method: "POST", body: JSON.stringify(payload) });
export const adminUpdateAgent = (agentId, payload) =>
  request(`/admin/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(payload) });

export const adminGetSettings = () => request("/admin/settings");
export const adminUpdateSettings = (payload) =>
  request("/admin/settings", { method: "PUT", body: JSON.stringify(payload) });

export const adminAudit = (page = 1, perPage = 25) =>
  request(`/admin/audit?page=${page}&per_page=${perPage}`);

export const adminBulkStatus = (status, ticketIds) =>
  request("/admin/tickets/bulk-status", {
    method: "POST",
    body: JSON.stringify({ status, ticket_ids: ticketIds }),
  });

export async function adminExportCsv() {
  const token = getToken();
  const response = await fetch(`${API_BASE}/admin/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) throw new Error(`Export failed (${response.status})`);
  return response.text();
}