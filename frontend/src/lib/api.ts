/**
 * API client configuration and helper functions for BoxnFreight Triage frontend.
 */

export interface Ticket {
  id: number | null;
  reference_id: string | null;
  ticket_id?: string | null;
  category: string;
  description: string;
  title?: string;
  status:
    | "RESOLVED_BY_AI"
    | "ESCALATED"
    | "HUMAN_RESOLVED"
    | "NEEDS_INFO"
    | "NEEDS_HUMAN"
    | "USER_ESCALATED"
    | "CONVERSATIONAL"
    | string;
  answer?: string | null;
  resolution_guidance?: string | null;
  agent_reason: string;
  created_at: string | null;
  resolved_at?: string | null;
  is_idempotent?: boolean;
  notice?: string | null;
  is_conversational?: boolean;
}

export interface AdminMetrics {
  needs_review: number;
  user_escalated: number;
  resolved: number;
  pending_review?: number;
  human_resolved?: number;
  total_tickets?: number;
  ai_resolved?: number;
}

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/$/, "");
  }
  // If running in browser locally
  if (typeof window !== "undefined") {
    if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
      return "http://localhost:8000";
    }
  }
  return "https://boxnfreight-triage.onrender.com";
}

export async function submitTicket(payload: {
  category: string;
  description: string;
}): Promise<Ticket> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/api/tickets`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    let errorDetail = res.statusText;
    try {
      const errJson = await res.json();
      if (errJson.detail) errorDetail = errJson.detail;
    } catch {
      // fallback to statusText
    }
    throw new Error(`Failed to submit ticket (${res.status}): ${errorDetail}`);
  }

  return await res.json();
}

export async function escalateTicket(ticketId: number): Promise<{ success: boolean; ticket: Ticket }> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/api/tickets/${ticketId}/escalate`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to escalate ticket (${res.status}): ${res.statusText}`);
  }

  return await res.json();
}

export async function fetchAdminMetrics(): Promise<AdminMetrics> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/api/admin/metrics`, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch admin metrics (${res.status}): ${res.statusText}`);
  }

  return await res.json();
}

export async function fetchAdminTickets(params?: {
  status?: string;
  category?: string;
  search?: string;
}): Promise<Ticket[]> {
  const baseUrl = getApiBaseUrl();
  const query = new URLSearchParams();
  if (params?.status && params.status !== "ALL") query.set("status", params.status);
  if (params?.category && params.category !== "ALL") query.set("category", params.category);
  if (params?.search && params.search.trim()) query.set("q", params.search.trim());

  const url = `${baseUrl}/api/admin/tickets${query.toString() ? `?${query.toString()}` : ""}`;
  const res = await fetch(url, {
    cache: "no-store",
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch admin tickets (${res.status}): ${res.statusText}`);
  }

  return await res.json();
}

export async function resolveTicketByAdmin(ticketId: number): Promise<{ success: boolean; ticket: Ticket }> {
  const baseUrl = getApiBaseUrl();
  const res = await fetch(`${baseUrl}/api/admin/tickets/${ticketId}/resolve`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Failed to resolve ticket (${res.status}): ${res.statusText}`);
  }

  return await res.json();
}
