"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Package,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
  FileText,
  Clock,
  RefreshCw,
} from "lucide-react";

interface TriageResult {
  id?: number;
  status: "RESOLVED" | "ESCALATED";
  category: string;
  answer?: string | null;
  agent_reason: string;
}

const SAMPLE_QUERIES = [
  {
    label: "FAQ: Create Business Account",
    title: "Account Registration Process",
    description: "How do I create a BoxNFreight business account and what are the initial steps?",
  },
  {
    label: "FAQ: Track Shipment via LR",
    title: "Tracking with LR Number",
    description: "How do I track my shipment using the LR number on BoxNFreight?",
  },
  {
    label: "Ambiguous: Stuck / Lost Cargo",
    title: "Urgent issue with cargo",
    description: "My shipment has been stuck somewhere with no updates, driver was rude, please compensate immediately!",
  },
];

export default function CustomerPortalPage() {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TriageResult | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      setError("Please fill in both the ticket title and description.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("https://boxnfreight-triage.onrender.com/tickets", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${res.statusText}`);
      }

      const data: TriageResult = await res.json();
      setResult(data);
    } catch (err: unknown) {
      console.error("Submission error:", err);
      const message =
        err instanceof Error
          ? err.message
          : "Failed to reach the triage backend. Ensure backend server is running on port 8000.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleApplySample = (sample: typeof SAMPLE_QUERIES[0]) => {
    setTitle(sample.title);
    setDescription(sample.description);
    setError(null);
    setResult(null);
  };

  const handleReset = () => {
    setTitle("");
    setDescription("");
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 via-slate-50 to-white flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">BoxNFreight</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  Support Portal
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">Automated Logistics Support & Triage</p>
            </div>
          </div>

          <Link
            href="/admin"
            className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
          >
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span>Admin Queue</span>
            <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 sm:px-6 py-8 sm:py-12">
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
            How can we help your freight today?
          </h1>
          <p className="mt-2 text-slate-600 text-sm sm:text-base max-w-xl mx-auto">
            Submit your inquiry or issue below. Common questions are instantly answered by our verified FAQ knowledge base; complex issues are automatically escalated for priority human support.
          </p>
        </div>

        {/* Quick Sample Chips */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="text-slate-400 flex items-center gap-1 mr-1">
            <HelpCircle className="w-3.5 h-3.5" /> Try a sample:
          </span>
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplySample(sample)}
              className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-blue-400 hover:bg-blue-50/50 hover:text-blue-700 transition shadow-2xs font-medium"
            >
              {sample.label}
            </button>
          ))}
        </div>

        {/* Ticket Submission Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
          <div className="border-b border-slate-100 bg-slate-50/60 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-800">Submit a Support Ticket</h2>
            </div>
            {(title || description || result) && (
              <button
                type="button"
                onClick={handleReset}
                className="text-xs text-slate-400 hover:text-slate-600 transition flex items-center gap-1"
              >
                <RefreshCw className="w-3 h-3" /> Clear
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-5">
            <div>
              <label htmlFor="ticket-title" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Ticket Title / Subject <span className="text-rose-500">*</span>
              </label>
              <input
                id="ticket-title"
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Issue generating LR or Question about transit insurance"
                disabled={loading}
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-sm transition"
              />
            </div>

            <div>
              <label htmlFor="ticket-description" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Description / Question Details <span className="text-rose-500">*</span>
              </label>
              <textarea
                id="ticket-description"
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe your inquiry in detail. Include relevant LR numbers, booking reference, or specific questions..."
                disabled={loading}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/50 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-sm transition resize-none"
              />
            </div>

            {error && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={loading}
                className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm transition shadow-sm shadow-blue-500/20 disabled:opacity-60 disabled:cursor-not-allowed min-w-[150px]"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Analyzing Ticket...</span>
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    <span>Submit Ticket</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Triage Result Card */}
        {result && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            <div
              className={`rounded-2xl border p-6 sm:p-8 shadow-md transition ${
                result.status === "RESOLVED"
                  ? "bg-emerald-50/40 border-emerald-200"
                  : "bg-amber-50/40 border-amber-200"
              }`}
            >
              {/* Status Header */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-slate-200/60">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-9 h-9 rounded-xl flex items-center justify-center ${
                      result.status === "RESOLVED"
                        ? "bg-emerald-600 text-white"
                        : "bg-amber-600 text-white"
                    }`}
                  >
                    {result.status === "RESOLVED" ? (
                      <CheckCircle2 className="w-5 h-5" />
                    ) : (
                      <AlertTriangle className="w-5 h-5" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs uppercase tracking-wider font-semibold text-slate-500">
                        Triage Verdict
                      </span>
                      {result.id && (
                        <span className="text-xs text-slate-400 font-mono">
                          Ticket #{result.id}
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-lg font-bold tracking-tight ${
                          result.status === "RESOLVED"
                            ? "text-emerald-900"
                            : "text-amber-900"
                        }`}
                      >
                        {result.status === "RESOLVED"
                          ? "Resolved via Instant FAQ Match"
                          : "Escalated for Priority Human Review"}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Badges */}
                <div className="flex items-center gap-2">
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-bold border ${
                      result.status === "RESOLVED"
                        ? "bg-emerald-100 text-emerald-800 border-emerald-300"
                        : "bg-amber-100 text-amber-800 border-amber-300"
                    }`}
                  >
                    {result.status}
                  </span>
                  <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">
                    {result.category}
                  </span>
                </div>
              </div>

              {/* Agent Reasoning Box */}
              <div className="mt-5 p-4 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-1.5 uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                  Agent Reasoning
                </div>
                <p className="text-sm text-slate-700 leading-relaxed font-normal">
                  {result.agent_reason}
                </p>
              </div>

              {/* Answer / Solution Box */}
              <div className="mt-4 p-5 rounded-xl bg-white border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wider">
                  <FileText className="w-3.5 h-3.5 text-slate-600" />
                  {result.status === "RESOLVED" ? "Verified Resolution Answer" : "Next Steps & Note"}
                </div>
                <p className="text-sm sm:text-base text-slate-900 leading-relaxed whitespace-pre-line font-normal">
                  {result.answer || (
                    <span className="text-slate-500 italic">
                      Ticket has been logged to the escalation queue. A customer representative will contact you shortly.
                    </span>
                  )}
                </p>
              </div>

              {/* Escalated Notice banner */}
              {result.status === "ESCALATED" && (
                <div className="mt-4 flex items-center justify-between text-xs text-amber-800 bg-amber-100/70 border border-amber-300/60 rounded-xl px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-700 shrink-0" />
                    <span>This ticket is currently queued for human investigation in the Admin Dashboard.</span>
                  </div>
                  <Link
                    href="/admin"
                    className="font-semibold underline hover:text-amber-900 transition shrink-0 ml-2"
                  >
                    View in Admin Queue &rarr;
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <p>BoxNFreight Logistics Platform &copy; 2026. Automated Support Ticket Triage.</p>
      </footer>
    </div>
  );
}
