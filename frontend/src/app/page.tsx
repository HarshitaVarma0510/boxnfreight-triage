"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Package,
  Send,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  HelpCircle,
  Clock,
  RefreshCw,
  Copy,
  Check,
  UserCheck,
  Info,
  ChevronDown,
  Headphones,
} from "lucide-react";
import { submitTicket, escalateTicket, Ticket } from "@/lib/api";

const CATEGORY_OPTIONS = [
  "Shipment Tracking (Track consignment, ETA, delay status)",
  "Proof of Delivery (POD / Signed copy download)",
  "Lorry Receipt / Bilty (LR copy, LR status, consignment note)",
  "Freight Booking & Orders (New vehicle placement, capacity)",
  "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
  "Payment & Outstanding (Ledger balance, payment reconciliation)",
  "Transit Damage & Claims (Damaged goods, insurance claims, shortage)",
  "Driver & Vehicle Details (Driver number, truck GPS location)",
  "Account & Portal Access (Login, password reset, user roles)",
  "Other / General Inquiry (Custom query or general help)",
] as const;

type CategoryType = (typeof CATEGORY_OPTIONS)[number];

const SAMPLE_QUERIES: {
  label: string;
  category: CategoryType;
  description: string;
}[] = [
  {
    label: "POD: Download Proof of Delivery",
    category: "Proof of Delivery (POD / Signed copy download)",
    description: "How do I get Proof of Delivery (POD) after my shipment is delivered?",
  },
  {
    label: "Tracking: LR Number Tracking",
    category: "Shipment Tracking (Track consignment, ETA, delay status)",
    description: "How do I track my shipment using the LR number on BoxNFreight?",
  },
  {
    label: "Booking: Advance Pickup Scheduling",
    category: "Freight Booking & Orders (New vehicle placement, capacity)",
    description: "Can I schedule a shipment booking in advance for a future pickup date?",
  },
  {
    label: "Billing: Apply for Credit Terms",
    category: "Billing & Invoicing (Freight bills, GST invoice, credit notes)",
    description: "How do I apply for a credit account and monthly GST billing cycle?",
  },
  {
    label: "Dispute: Damaged Cargo on Arrival",
    category: "Transit Damage & Claims (Damaged goods, insurance claims, shortage)",
    description: "My shipment arrived badly damaged with packages torn. Driver refused to sign exception on POD. Please investigate and initiate an urgent compensation review!",
  },
  {
    label: "Greeting: Conversational Query",
    category: "Other / General Inquiry (Custom query or general help)",
    description: "Hello, good morning team!",
  },
];

const LOADING_STEPS = [
  "Analyzing issue description...",
  "Checking logistics knowledge base...",
  "Evaluating BRD operational rules...",
  "Synthesizing triage resolution...",
];

export default function CustomerPortalPage() {
  const [category, setCategory] = useState<string>("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingStepIdx, setLoadingStepIdx] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Ticket | null>(null);
  const [copied, setCopied] = useState(false);
  const [escalating, setEscalating] = useState(false);

  const resultRef = useRef<HTMLDivElement>(null);

  // Cycle loading steps when in flight
  useEffect(() => {
    if (!loading) {
      setLoadingStepIdx(0);
      return;
    }
    const interval = setInterval(() => {
      setLoadingStepIdx((prev) => (prev + 1) % LOADING_STEPS.length);
    }, 1200);
    return () => clearInterval(interval);
  }, [loading]);

  // Auto-scroll smoothly to result card on submit/result change
  useEffect(() => {
    if (result) {
      const timer = setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [result]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!category.trim()) {
      setError("Please select an issue category before submitting.");
      return;
    }
    if (!description.trim()) {
      setError("Please describe your issue or question before submitting.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setCopied(false);

    try {
      const data = await submitTicket({
        category,
        description: description.trim(),
      });
      setResult(data);

      // Auto-scroll smoothly to response card
      setTimeout(() => {
        resultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 100);
    } catch (err: unknown) {
      console.error("Submission error:", err);
      const message =
        err instanceof Error
          ? err.message
          : "Failed to submit ticket. Please check your network and verify the backend server is running.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleEscalate = async () => {
    if (!result?.id || escalating) return;
    setEscalating(true);
    try {
      const res = await escalateTicket(result.id);
      if (res?.ticket) {
        setResult(res.ticket);
      } else {
        setResult((prev) => (prev ? { ...prev, status: "USER_ESCALATED" } : prev));
      }
    } catch (err) {
      console.error("Escalation failed:", err);
      // Seamlessly update status to USER_ESCALATED
      setResult((prev) => (prev ? { ...prev, status: "USER_ESCALATED" } : prev));
    } finally {
      setEscalating(false);
    }
  };

  const handleCopyReference = () => {
    if (!result?.reference_id) return;
    navigator.clipboard.writeText(result.reference_id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleApplySample = (sample: (typeof SAMPLE_QUERIES)[0]) => {
    setCategory(sample.category);
    setDescription(sample.description);
    setError(null);
    setResult(null);
  };

  const handleReset = () => {
    setDescription("");
    setCategory("");
    setResult(null);
    setError(null);
  };

  // Pure greeting condition
  const isGreeting = Boolean(result && (result.ticket_id === null || result.is_conversational));

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 via-slate-50 to-white flex flex-col font-sans">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white/90 backdrop-blur sticky top-0 z-20">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Package className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-slate-900 tracking-tight">BoxNFreight</span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                  AI Support Hub
                </span>
              </div>
              <p className="text-xs text-slate-500 hidden sm:block">
                Intelligent Logistics Triage & Automated Knowledge Base
              </p>
            </div>
          </div>

          <Link
            href="/admin"
            className="flex items-center gap-2 text-sm font-medium px-4 py-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-sm"
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
            How can we assist your logistics today?
          </h1>
          <p className="mt-2 text-slate-600 text-sm sm:text-base max-w-xl mx-auto">
            Choose your issue category and describe what you need. Inquiries matching verified operational FAQs are resolved instantly; disputes and complex requests are automatically escalated to our human operations team.
          </p>
        </div>

        {/* Quick Sample Queries */}
        <div className="mb-6 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span className="text-slate-400 flex items-center gap-1 mr-1">
            <HelpCircle className="w-3.5 h-3.5" /> Try a sample:
          </span>
          {SAMPLE_QUERIES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplySample(sample)}
              className="px-3 py-1.5 rounded-full bg-white border border-slate-200 text-slate-700 hover:border-blue-400 hover:bg-blue-50/60 hover:text-blue-700 transition shadow-2xs font-medium cursor-pointer"
            >
              {sample.label}
            </button>
          ))}
        </div>

        {/* Simplified Ticket Intake Card */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden mb-8">
          <div className="border-b border-slate-100 bg-slate-50/80 px-6 py-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-800">Support Intake & AI Triage</h2>
            </div>
            {(description || category || result) && (
              <button
                type="button"
                onClick={handleReset}
                className="text-xs text-slate-400 hover:text-slate-600 transition flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Reset Form
              </button>
            )}
          </div>

          <form onSubmit={handleSubmit} className="p-6 sm:p-8 space-y-5">
            {/* Neutral Category Dropdown with Full 10 Business Categories */}
            <div>
              <label htmlFor="ticket-category" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Issue Category <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <select
                  id="ticket-category"
                  value={category}
                  onChange={(e) => {
                    setCategory(e.target.value);
                    if (error) setError(null);
                  }}
                  disabled={loading}
                  required
                  className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/60 text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-sm transition appearance-none cursor-pointer pr-10 font-medium invalid:text-slate-400"
                >
                  <option value="" disabled>
                    -- Select a Category (or choose Other) --
                  </option>
                  {CATEGORY_OPTIONS.map((cat) => (
                    <option key={cat} value={cat} className="text-slate-900">
                      {cat}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 text-slate-400 absolute right-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Single Focused Description Textarea */}
            <div>
              <label htmlFor="ticket-description" className="block text-sm font-semibold text-slate-800 mb-1.5">
                Issue Description & Details <span className="text-rose-500">*</span>
              </label>
              <textarea
                id="ticket-description"
                rows={4}
                value={description}
                onChange={(e) => {
                  setDescription(e.target.value);
                  if (error) setError(null);
                }}
                placeholder="Describe your inquiry in detail. Include any relevant LR numbers, booking reference, or specific questions..."
                disabled={loading}
                required
                className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50/60 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white text-sm transition resize-none leading-relaxed"
              />
            </div>

            {error && (
              <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex justify-end pt-1">
              <button
                type="submit"
                disabled={loading || !category.trim() || !description.trim()}
                className="flex items-center justify-center gap-2 px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm transition shadow-sm shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed min-w-[160px] cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processing...</span>
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

        {/* Animated Loading Skeleton State */}
        {loading && (
          <div className="rounded-2xl border border-blue-200 bg-blue-50/40 p-6 sm:p-8 shadow-sm space-y-4 animate-pulse">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-blue-200 flex items-center justify-center text-blue-600">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-blue-600 uppercase tracking-wider">
                    AI Triage In Flight
                  </div>
                  <div className="text-base font-bold text-slate-800 transition-all duration-300">
                    {LOADING_STEPS[loadingStepIdx]}
                  </div>
                </div>
              </div>
              <div className="h-6 w-24 bg-blue-100 rounded-full" />
            </div>

            <div className="h-16 bg-white/70 rounded-xl border border-blue-100 p-4 space-y-2">
              <div className="h-3 w-1/3 bg-slate-200 rounded" />
              <div className="h-3 w-4/5 bg-slate-200 rounded" />
            </div>

            <div className="h-24 bg-white/70 rounded-xl border border-blue-100 p-4 space-y-2">
              <div className="h-3 w-1/4 bg-slate-200 rounded" />
              <div className="h-3 w-full bg-slate-200 rounded" />
              <div className="h-3 w-3/4 bg-slate-200 rounded" />
            </div>
          </div>
        )}

        {/* SINGLE UNIFIED RESULT CARD */}
        {result && (
          <div ref={resultRef} className="animate-in fade-in slide-in-from-bottom-4 duration-300">
            {/* Idempotency Notice Banner */}
            {result.is_idempotent && (
              <div className="mb-4 p-3.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-900 text-xs sm:text-sm flex items-center gap-2.5 shadow-2xs">
                <Info className="w-4 h-4 text-indigo-600 shrink-0" />
                <span>
                  <strong>Idempotent Submission:</strong> {result.notice || "Identical ticket submitted within the 5-minute cooldown window. Returned existing ticket record."}
                </span>
              </div>
            )}

            {/* 3. PURE GREETINGS: Virtual Assistant card without ticket ID and without black escalation button */}
            {isGreeting ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-8 shadow-sm">
                <div className="flex items-center gap-3 pb-4 border-b border-slate-100">
                  <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-sm">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold tracking-tight text-slate-900">
                      Virtual Assistant
                    </h3>
                  </div>
                </div>

                <div className="mt-4 p-5 rounded-xl bg-slate-50 border border-slate-100 text-sm sm:text-base text-slate-900 leading-relaxed whitespace-pre-line font-normal">
                  {result.answer || result.resolution_guidance}
                </div>
              </div>
            ) : (
              /* 1 & 2. SINGLE UNIFIED RESULT CARD (Resolved by AI, User Escalated, Needs Human) */
              <div
                className={`bg-white rounded-2xl border p-6 sm:p-8 shadow-sm transition ${
                  result.status === "USER_ESCALATED"
                    ? "border-purple-200"
                    : result.status === "RESOLVED_BY_AI"
                    ? "border-emerald-200"
                    : result.status === "HUMAN_RESOLVED"
                    ? "border-blue-200"
                    : "border-amber-200"
                }`}
              >
                {/* Header Row: Left Title & Icon + Right Badges */}
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-sm ${
                        result.status === "USER_ESCALATED"
                          ? "bg-purple-600"
                          : result.status === "RESOLVED_BY_AI"
                          ? "bg-emerald-600"
                          : result.status === "HUMAN_RESOLVED"
                          ? "bg-blue-600"
                          : "bg-amber-600"
                      }`}
                    >
                      {result.status === "USER_ESCALATED" ? (
                        <UserCheck className="w-5 h-5" />
                      ) : result.status === "RESOLVED_BY_AI" || result.status === "HUMAN_RESOLVED" ? (
                        <CheckCircle2 className="w-5 h-5" />
                      ) : (
                        <AlertCircle className="w-5 h-5" />
                      )}
                    </div>
                    <div>
                      <h3 className="text-lg font-bold tracking-tight text-slate-900">
                        {result.status === "USER_ESCALATED"
                          ? "Escalated to Support Specialist"
                          : result.status === "RESOLVED_BY_AI"
                          ? "Resolved by AI"
                          : result.status === "HUMAN_RESOLVED"
                          ? "Closed by Operations Staff"
                          : "Ticket Submitted Successfully"}
                      </h3>
                    </div>
                  </div>

                  {/* Badges: #TKT-xxxx + Category + Status Badge */}
                  <div className="flex flex-wrap items-center gap-2">
                    {result.reference_id && (
                      <div className="flex items-center bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-200 shadow-2xs">
                        <span className="text-xs font-mono font-bold text-slate-800 mr-2">
                          {result.reference_id}
                        </span>
                        <button
                          type="button"
                          onClick={handleCopyReference}
                          className="text-slate-400 hover:text-slate-700 transition p-1 rounded-md hover:bg-slate-200/60 cursor-pointer"
                          title="Copy Ticket Reference"
                        >
                          {copied ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Copy className="w-3.5 h-3.5" />
                          )}
                        </button>
                        {copied && (
                          <span className="text-[10px] font-semibold text-emerald-600 ml-1">Copied!</span>
                        )}
                      </div>
                    )}

                    {result.category && (
                      <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-50 text-slate-700 border border-slate-200">
                        {result.category}
                      </span>
                    )}

                    {/* Status Pill Badge: Green for Resolved by AI, Purple for User Escalated, Amber for Needs Human */}
                    {result.status === "USER_ESCALATED" ? (
                      <span className="bg-purple-100 text-purple-700 font-semibold px-2.5 py-1 rounded-full text-xs">
                        User Escalated
                      </span>
                    ) : result.status === "RESOLVED_BY_AI" ? (
                      <span className="bg-emerald-100 text-emerald-800 font-bold px-2.5 py-1 rounded-full text-xs border border-emerald-300">
                        Resolved by AI
                      </span>
                    ) : result.status === "HUMAN_RESOLVED" ? (
                      <span className="bg-blue-100 text-blue-800 font-bold px-2.5 py-1 rounded-full text-xs border border-blue-300">
                        Human Resolved
                      </span>
                    ) : (
                      <span className="bg-amber-100 text-amber-800 font-semibold px-2.5 py-1 rounded-full text-xs">
                        Needs Human Review
                      </span>
                    )}
                  </div>
                </div>

                {/* Card Body: Show the AI guidance/FAQ answer or reassurance message (clean, without ugly labels) */}
                <div className="mt-4 p-5 rounded-xl bg-slate-50 border border-slate-100 text-sm sm:text-base text-slate-900 leading-relaxed whitespace-pre-line font-normal">
                  {result.status === "USER_ESCALATED"
                    ? (result.answer || "Your request has been escalated to our priority human support queue. A specialist has been notified and will review your shipment details.")
                    : result.status === "RESOLVED_BY_AI"
                    ? (result.answer || result.resolution_guidance)
                    : result.status === "HUMAN_RESOLVED"
                    ? (result.answer || result.resolution_guidance || "This ticket has been resolved by our operations staff.")
                    : "Your inquiry has been routed to our operations team for specialist review. We are actively investigating your request."}
                </div>

                {/* 1. Escalation Action: SOLID BLACK BUTTON at bottom right for RESOLVED_BY_AI */}
                {result.status === "RESOLVED_BY_AI" && (
                  <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs text-slate-500">
                      Did this answer address your inquiry, or do you need personalized support?
                    </div>
                    <button
                      type="button"
                      onClick={handleEscalate}
                      disabled={escalating}
                      className="bg-black hover:bg-zinc-800 text-white text-xs font-medium px-3.5 py-2 rounded-lg flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-60"
                    >
                      {escalating ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-white" />
                          <span>Escalating...</span>
                        </>
                      ) : (
                        <>
                          <Headphones className="w-3.5 h-3.5 text-white" />
                          <span>Talk to a Human Agent</span>
                        </>
                      )}
                    </button>
                  </div>
                )}

                {/* 2. AFTER CLICKING 'TALK TO A HUMAN AGENT': Black button removed; PURPLE CONFIRMATION BANNER rendered */}
                {result.status === "USER_ESCALATED" && (
                  <div className="mt-4 bg-purple-50 border border-purple-200 text-purple-900 rounded-lg p-3 text-sm flex items-center gap-2">
                    <span>Priority Support: Placed in the live agent queue. A representative will reach out shortly.</span>
                  </div>
                )}

                {/* Clean reassurance banner for NEEDS_HUMAN */}
                {result.status !== "RESOLVED_BY_AI" && result.status !== "USER_ESCALATED" && result.status !== "HUMAN_RESOLVED" && (
                  <div className="mt-4 bg-amber-50 border border-amber-200 text-amber-900 rounded-lg p-3 text-sm flex items-center gap-2">
                    <Clock className="w-4 h-4 text-amber-700 flex-shrink-0" />
                    <span>A specialist will inspect your consignment details and follow up shortly.</span>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
        <p>BoxNFreight Logistics Platform &copy; 2026 &bull; Automated Support Ticket Triage SaaS</p>
      </footer>
    </div>
  );
}
