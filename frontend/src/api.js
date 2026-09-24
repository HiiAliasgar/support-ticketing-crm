const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
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
    throw new Error(detail);
  }
  return response.json();
}

export const listTickets = (params = {}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.search) qs.set("search", params.search);
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

export const getDashboard = () => request("/dashboard");