"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  ArrowLeft,
  RefreshCw,
  Tag,
  AlertCircle,
  CheckCircle2,
  Package,
  Calendar,
} from "lucide-react";
import { formatDateToIST } from "@/lib/dateUtils";

interface Ticket {
  id: number;
  title: string;
  description: string;
  status: string;
  category: string;
  agent_reason: string;
  created_at: string;
}

export default function AdminEscalationPage() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchEscalated = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("https://boxnfreight-triage.onrender.com/tickets?status=ESCALATED");
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      }
      const data: Ticket[] = await res.json();
      setTickets(data);
    } catch (err: unknown) {
      console.error("Failed to fetch tickets:", err);
      const message =
        err instanceof Error
          ? err.message
          : "Failed to fetch escalated tickets. Verify backend is running at https://boxnfreight-triage.onrender.com.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    const loadTickets = async () => {
      try {
        const res = await fetch("https://boxnfreight-triage.onrender.com/tickets?status=ESCALATED");
        if (!res.ok) {
          throw new Error(`Server returned ${res.status}: ${res.statusText}`);
        }
        const data: Ticket[] = await res.json();
        if (!ignore) {
          setTickets(data);
        }
      } catch (err: unknown) {
        if (!ignore) {
          console.error("Failed to fetch tickets:", err);
          const message =
            err instanceof Error
              ? err.message
              : "Failed to fetch escalated tickets. Verify backend is running at https://boxnfreight-triage.onrender.com.";
          setError(message);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };
    loadTickets();
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      {/* Admin Header */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-20 shadow-2xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 rounded-lg text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition"
              title="Return to Customer Portal"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-amber-600 flex items-center justify-center text-white shadow-sm">
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-bold text-lg text-slate-900 tracking-tight">
                    Admin Escalation Queue
                  </h1>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                    Live Triage
                  </span>
                </div>
                <p className="text-xs text-slate-500 hidden sm:block">
                  Tickets requiring human investigation & operational review
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs sm:text-sm font-medium text-slate-600 hover:text-blue-600 transition flex items-center gap-1.5"
            >
              <Package className="w-4 h-4" />
              <span className="hidden sm:inline">Customer Portal</span>
            </Link>
            <button
              onClick={fetchEscalated}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3.5 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition shadow-sm disabled:opacity-60"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Queue</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-8">
        {/* Status overview bar */}
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6 bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-amber-500 animate-pulse" />
            <span className="text-sm font-medium text-slate-700">
              {loading ? (
                "Checking escalation queue..."
              ) : (
                <>
                  <strong className="text-slate-900">{tickets.length}</strong>{" "}
                  {tickets.length === 1 ? "ticket" : "tickets"} awaiting human triage
                </>
              )}
            </span>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unable to load escalated tickets</p>
              <p className="text-xs text-rose-600 mt-0.5">{error}</p>
              <button
                onClick={fetchEscalated}
                className="mt-2 text-xs font-semibold underline hover:text-rose-900"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Loading Skeletons */}
        {loading && (
          <div className="space-y-4">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="bg-white rounded-xl border border-slate-200 p-6 animate-pulse space-y-4"
              >
                <div className="flex items-center justify-between">
                  <div className="h-4 w-40 bg-slate-200 rounded" />
                  <div className="h-5 w-24 bg-slate-200 rounded-full" />
                </div>
                <div className="h-4 w-3/4 bg-slate-200 rounded" />
                <div className="h-16 bg-slate-100 rounded-lg" />
              </div>
            ))}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && tickets.length === 0 && (
          <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-2xs max-w-lg mx-auto my-8">
            <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-4 border border-emerald-200">
              <CheckCircle2 className="w-7 h-7" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Escalation Queue is Clear</h3>
            <p className="mt-1 text-sm text-slate-500 max-w-sm mx-auto">
              No tickets are currently pending human review. All incoming tickets have been resolved automatically via verified FAQs.
            </p>
            <div className="mt-6 flex justify-center gap-3">
              <button
                onClick={fetchEscalated}
                className="px-4 py-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium transition flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh
              </button>
              <Link
                href="/"
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium transition"
              >
                Go to Portal
              </Link>
            </div>
          </div>
        )}

        {/* Tickets Cards List */}
        {!loading && !error && tickets.length > 0 && (
          <div className="space-y-4">
            {tickets.map((t) => (
              <div
                key={t.id}
                className="bg-white rounded-xl border border-slate-200 hover:border-slate-300 shadow-2xs overflow-hidden transition"
              >
                {/* Ticket Top bar */}
                <div className="p-5 sm:p-6">
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-mono text-xs font-bold border border-slate-200">
                        #{t.id}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300 flex items-center gap-1">
                        <AlertCircle className="w-3 h-3" />
                        {t.status}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
                        <Tag className="w-3 h-3" />
                        {t.category}
                      </span>
                    </div>

                    <div className="text-xs text-slate-400 flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{formatDateToIST(t.created_at)}</span>
                    </div>
                  </div>

                  {/* Title & Description */}
                  <h2 className="text-base font-bold text-slate-900 mb-1.5">{t.title}</h2>
                  <p className="text-sm text-slate-600 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-150 mb-3 whitespace-pre-wrap">
                    {t.description}
                  </p>

                  {/* Agent Escalation Reason */}
                  <div className="p-3.5 rounded-lg bg-amber-50/70 border border-amber-200/80 text-xs sm:text-sm">
                    <div className="flex items-center gap-1.5 font-bold text-amber-900 mb-1">
                      <ShieldAlert className="w-4 h-4 text-amber-700" />
                      Agent Escalation Reason:
                    </div>
                    <p className="text-amber-800 leading-relaxed">{t.agent_reason}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        BoxNFreight Internal Admin Console &bull; Triage Operations
      </footer>
    </div>
  );
}
