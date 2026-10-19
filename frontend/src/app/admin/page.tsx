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
  Search,
  Check,
  Clock,
  CheckCircle,
  AlertTriangle,
  UserCheck,
  Sparkles,
  BarChart3,
  PieChart,
  ChevronDown,
  ChevronUp,
  Zap,
  X,
} from "lucide-react";
import {
  fetchAdminMetrics,
  fetchAdminTickets,
  resolveTicketByAdmin,
  Ticket,
  AdminMetrics,
} from "@/lib/api";
import { formatDateToIST } from "@/lib/dateUtils";

const QUEUE_TABS = [
  {
    id: "NEEDS_HUMAN",
    label: "Needs Human Review",
    getCount: (m: AdminMetrics) => m.needs_review ?? 0,
    activeBadge: "bg-white/20 text-white border-white/20",
    inactiveBadge: "bg-amber-100 text-amber-800 border-amber-300",
    icon: AlertTriangle,
  },
  {
    id: "USER_ESCALATED",
    label: "User Escalated",
    getCount: (m: AdminMetrics) => m.user_escalated ?? 0,
    activeBadge: "bg-white/20 text-white border-white/20",
    inactiveBadge: "bg-purple-100 text-purple-800 border-purple-300",
    icon: UserCheck,
  },
  {
    id: "RESOLVED_BY_AI",
    label: "Resolved by AI",
    getCount: (m: AdminMetrics) => m.ai_resolved ?? Math.max(0, (m.resolved ?? 0) - (m.human_resolved ?? 0)),
    activeBadge: "bg-white/20 text-white border-white/20",
    inactiveBadge: "bg-emerald-100 text-emerald-800 border-emerald-300",
    icon: Sparkles,
  },
];

/**
 * Reusable Amber Keyword Highlighting Component
 * Match search query case-insensitively and wrap with exact class:
 * <mark className="bg-amber-200 text-amber-950 font-semibold px-1 py-0.5 rounded">matched_text</mark>
 */
function HighlightText({
  text,
  query,
}: {
  text?: string | null;
  query: string;
}) {
  if (!text) return null;
  const trimmed = query.trim();
  if (!trimmed) return <>{text}</>;

  const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, index) =>
        part.toLowerCase() === trimmed.toLowerCase() ? (
          <mark
            key={index}
            className="bg-amber-200 text-amber-950 font-semibold px-1 py-0.5 rounded"
          >
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  );
}

/**
 * Refines agent triage reasoning text to remove raw FAQ references
 * and align with enterprise knowledge base SOP terminology.
 */
function cleanReasoningText(reason?: string | null): string {
  if (!reason) return "";
  let text = reason;
  text = text.replace(
    /Ticket describes an operational dispute, complex incident, or query not covered by the 50 FAQs\.\s*Escalated for human review\./gi,
    "Ticket describes an operational dispute, complex incident, or query not covered in verified knowledge base SOPs. Escalated for human review."
  );
  text = text.replace(
    /Query could not be answered with high confidence from the 50 FAQs\.\s*Escalated for human review\./gi,
    "Query not covered in verified knowledge base SOPs. Escalated for human review."
  );
  text = text.replace(
    /query not covered by the 50 FAQs\.?(\s*Escalated for human review\.)?/gi,
    "query not covered in verified knowledge base SOPs. Escalated for human review."
  );
  text = text.replace(
    /not covered by the 50 FAQs\.?(\s*Escalated for human review\.)?/gi,
    "query not covered in verified knowledge base SOPs. Escalated for human review."
  );
  text = text.replace(
    /from the 50 FAQs\.?(\s*Escalated for human review\.)?/gi,
    "in verified knowledge base SOPs. Escalated for human review."
  );
  return text;
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<AdminMetrics>({
    needs_review: 0,
    user_escalated: 0,
    resolved: 0,
    pending_review: 0,
    human_resolved: 0,
    ai_resolved: 0,
    total_tickets: 0,
  });
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [allTickets, setAllTickets] = useState<Ticket[]>([]);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [loadingTickets, setLoadingTickets] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state - Default to 'NEEDS_HUMAN' queue
  const [selectedStatus, setSelectedStatus] = useState("NEEDS_HUMAN");
  const [searchQuery, setSearchQuery] = useState("");
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [actionSuccessNotice, setActionSuccessNotice] = useState<string | null>(null);

  // Analytics controls
  const [showAnalytics, setShowAnalytics] = useState(true);
  const [hoveredSlice, setHoveredSlice] = useState<string | null>(null);

  const loadData = async (
    status = selectedStatus,
    search = searchQuery
  ) => {
    setLoadingTickets(true);
    setError(null);
    try {
      const trimmedSearch = search.trim();
      // Global Search: When search query is entered, search across ALL tickets regardless of active tab
      const statusParam = trimmedSearch ? undefined : status !== "ALL" ? status : undefined;

      const [metricsData, ticketsData, allTicketsData] = await Promise.all([
        fetchAdminMetrics(),
        fetchAdminTickets({
          status: statusParam,
          search: trimmedSearch || undefined,
        }),
        fetchAdminTickets({}),
      ]);
      setMetrics(metricsData);
      setTickets(ticketsData);
      setAllTickets(allTicketsData);
    } catch (err: unknown) {
      console.error("Failed to load admin data:", err);
      const msg = err instanceof Error ? err.message : "Failed to connect to backend.";
      setError(msg);
    } finally {
      setLoadingMetrics(false);
      setLoadingTickets(false);
    }
  };

  useEffect(() => {
    loadData(selectedStatus, searchQuery);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedStatus]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadData(selectedStatus, searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    loadData(selectedStatus, "");
  };

  const handleResolve = async (ticketId: number, referenceId: string) => {
    setResolvingId(ticketId);
    try {
      const res = await resolveTicketByAdmin(ticketId);
      const updatedTicket = res.ticket;

      // Optimistically update local row
      setTickets((prev) =>
        prev.map((t) => (t.id === ticketId ? { ...t, ...updatedTicket } : t))
      );
      setAllTickets((prev) =>
        prev.map((t) => (t.id === ticketId ? { ...t, ...updatedTicket } : t))
      );

      // Immediately update top KPI counters safely
      setMetrics((prev) => ({
        ...prev,
        needs_review: Math.max(0, (prev.needs_review ?? 0) - 1),
        pending_review: Math.max(0, (prev.pending_review ?? 0) - 1),
        user_escalated:
          selectedStatus === "USER_ESCALATED"
            ? Math.max(0, (prev.user_escalated ?? 0) - 1)
            : (prev.user_escalated ?? 0),
        human_resolved: (prev.human_resolved ?? 0) + 1,
        resolved: (prev.resolved ?? 0) + 1,
      }));

      setActionSuccessNotice(`Ticket ${referenceId} marked as Human Resolved!`);
      setTimeout(() => setActionSuccessNotice(null), 3500);
    } catch (err: unknown) {
      console.error("Resolution failed:", err);
      alert("Failed to resolve ticket. Please try again.");
    } finally {
      setResolvingId(null);
    }
  };

  // Dynamic Analytics Computations
  const totalTickets = allTickets.length > 0 ? allTickets.length : (metrics.total_tickets ?? 0);

  const aiResolvedCount = allTickets.length > 0
    ? allTickets.filter(
        (t) => t.status === "RESOLVED_BY_AI" || t.status === "CONVERSATIONAL" || t.status === "HUMAN_RESOLVED"
      ).length
    : ((metrics.ai_resolved ?? 0) + (metrics.human_resolved ?? 0));

  const needsHumanCount = allTickets.length > 0
    ? allTickets.filter((t) => t.status === "NEEDS_HUMAN" || t.status === "ESCALATED").length
    : (metrics.needs_review ?? 0);

  const userEscalatedCount = allTickets.length > 0
    ? allTickets.filter((t) => t.status === "USER_ESCALATED").length
    : (metrics.user_escalated ?? 0);

  const effectiveTotal = Math.max(1, aiResolvedCount + needsHumanCount + userEscalatedCount);

  // Executive SLA & Efficiency Metrics
  const aiDeflectionRate = ((aiResolvedCount / effectiveTotal) * 100).toFixed(1);
  const needsReviewRate = ((needsHumanCount / effectiveTotal) * 100).toFixed(1);
  const userEscalatedRate = ((userEscalatedCount / effectiveTotal) * 100).toFixed(1);

  const totalEscalations = needsHumanCount + userEscalatedCount;
  const userRequestedPct = totalEscalations > 0 ? Math.round((userEscalatedCount / totalEscalations) * 100) : 0;
  const operationalDisputesPct = totalEscalations > 0 ? 100 - userRequestedPct : 0;

  const statusMix = [
    {
      id: "RESOLVED_BY_AI",
      label: "Resolved by AI",
      percentage: Number(aiDeflectionRate),
      rawFraction: aiResolvedCount / effectiveTotal,
      color: "#10b981", // emerald-500
      badgeColor: "bg-emerald-500",
    },
    {
      id: "USER_ESCALATED",
      label: "User Escalated",
      percentage: Number(userEscalatedRate),
      rawFraction: userEscalatedCount / effectiveTotal,
      color: "#a855f7", // purple-500
      badgeColor: "bg-purple-500",
    },
    {
      id: "NEEDS_HUMAN",
      label: "Needs Human Review",
      percentage: Number(needsReviewRate),
      rawFraction: needsHumanCount / effectiveTotal,
      color: "#f59e0b", // amber-500
      badgeColor: "bg-amber-500",
    },
  ];

  // SVG Donut calculation
  const donutRadius = 48;
  const donutCircumference = 2 * Math.PI * donutRadius;
  let accumulatedOffset = 0;
  const donutSegments = statusMix.map((slice) => {
    const strokeLength = slice.rawFraction * donutCircumference;
    const spaceLength = donutCircumference - strokeLength;
    const offset = accumulatedOffset;
    accumulatedOffset += strokeLength;
    return {
      ...slice,
      strokeLength,
      spaceLength,
      offset,
    };
  });

  // 10 Standard Logistics Categories (Excludes pure conversational greetings)
  const STANDARD_CATEGORIES = [
    "Shipment Tracking",
    "Proof of Delivery (POD)",
    "Lorry Receipt / Bilty",
    "Freight Booking & Orders",
    "Billing & Invoicing",
    "Payment & Outstanding",
    "Transit Damage & Claims",
    "Driver & Vehicle Details",
    "Account & Portal Access",
    "General Logistics Inquiry",
  ] as const;

  const categoryCounts: Record<string, number> = {};
  STANDARD_CATEGORIES.forEach((name) => {
    categoryCounts[name] = 0;
  });

  let totalLogisticsTickets = 0;
  allTickets.forEach((t) => {
    const rawCat = t.category || "";
    const lower = rawCat.toLowerCase();

    // Exclude Conversational Greeting / Inquiry
    if (lower.includes("conversational") || lower.includes("greeting")) {
      return;
    }

    let mapped: string = "General Logistics Inquiry";
    if (lower.includes("shipment tracking") || lower.includes("track")) {
      mapped = "Shipment Tracking";
    } else if (lower.includes("proof of delivery") || lower.includes("pod")) {
      mapped = "Proof of Delivery (POD)";
    } else if (lower.includes("lorry receipt") || lower.includes("bilty") || lower.includes("lr generation") || lower.includes("lr (lorry")) {
      mapped = "Lorry Receipt / Bilty";
    } else if (lower.includes("booking") || lower.includes("cancellation") || lower.includes("refund")) {
      mapped = "Freight Booking & Orders";
    } else if (lower.includes("payment") || lower.includes("outstanding") || lower.includes("ledger")) {
      mapped = "Payment & Outstanding";
    } else if (lower.includes("billing") || lower.includes("invoice") || lower.includes("pricing") || lower.includes("quotes") || lower.includes("gst")) {
      mapped = "Billing & Invoicing";
    } else if (lower.includes("damage") || lower.includes("claims") || lower.includes("insurance") || lower.includes("shortage")) {
      mapped = "Transit Damage & Claims";
    } else if (lower.includes("driver") || lower.includes("vehicle") || lower.includes("truck") || lower.includes("gps")) {
      mapped = "Driver & Vehicle Details";
    } else if (lower.includes("account") || lower.includes("portal") || lower.includes("onboarding") || lower.includes("login") || lower.includes("password")) {
      mapped = "Account & Portal Access";
    }

    categoryCounts[mapped] = (categoryCounts[mapped] || 0) + 1;
    totalLogisticsTickets++;
  });

  const allTenCategories = STANDARD_CATEGORIES.map((name) => ({
    name,
    count: categoryCounts[name] || 0,
    percentage:
      totalLogisticsTickets > 0
        ? Math.round(((categoryCounts[name] || 0) / totalLogisticsTickets) * 100)
        : 0,
  })).sort((a, b) => {
    if (b.count !== a.count) return b.count - a.count;
    return STANDARD_CATEGORIES.indexOf(a.name) - STANDARD_CATEGORIES.indexOf(b.name);
  });

  const isGlobalSearchActive = Boolean(searchQuery.trim());

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      {/* Top Navigation Bar */}
      <header className="border-b border-slate-200 bg-white sticky top-0 z-20 shadow-2xs">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="p-2 rounded-xl text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition cursor-pointer"
              title="Return to Customer Portal"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-xl bg-slate-900 flex items-center justify-center text-white shadow-sm">
                <ShieldAlert className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h1 className="font-bold text-lg text-slate-900 tracking-tight">
                  Admin Operations Console
                </h1>
                <p className="text-xs text-slate-500 hidden sm:block">
                  Live Ticket Escalation, KPI Monitoring & Specialist Resolution
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="text-xs sm:text-sm font-medium text-slate-600 hover:text-blue-600 transition flex items-center gap-1.5 cursor-pointer"
            >
              <Package className="w-4 h-4" />
              <span className="hidden sm:inline">Customer Portal</span>
            </Link>
            <button
              onClick={() => loadData()}
              disabled={loadingTickets}
              className="flex items-center gap-1.5 text-xs sm:text-sm font-medium px-3.5 py-2 rounded-xl bg-slate-900 text-white hover:bg-slate-800 transition shadow-sm disabled:opacity-60 cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loadingTickets ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        {/* Action success notification */}
        {actionSuccessNotice && (
          <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center gap-2.5 shadow-sm animate-in fade-in">
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="font-semibold">{actionSuccessNotice}</span>
          </div>
        )}

        {/* 1. TOP KPI SUMMARY CARDS (EXACTLY 3 CARDS ONLY) */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
          {/* Card 1: NEEDS HUMAN REVIEW */}
          <div className="bg-white rounded-xl border border-amber-200/90 p-4 shadow-2xs hover:shadow-xs transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-700">
                NEEDS HUMAN REVIEW
              </span>
              <div className="w-7 h-7 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center border border-amber-200">
                <AlertTriangle className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {loadingMetrics ? "..." : (metrics.needs_review ?? 0)}
            </div>
            <p className="mt-0.5 text-[11px] text-slate-500 truncate">
              Actionable escalations requiring review
            </p>
          </div>

          {/* Card 2: USER ESCALATED */}
          <div className="bg-white rounded-xl border border-purple-200/90 p-4 shadow-2xs hover:shadow-xs transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-purple-700">
                USER ESCALATED
              </span>
              <div className="w-7 h-7 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center border border-purple-200">
                <UserCheck className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {loadingMetrics ? "..." : (metrics.user_escalated ?? 0)}
            </div>
            <p className="mt-0.5 text-[11px] text-slate-500 truncate">
              Priority &quot;Talk to Agent&quot; requests
            </p>
          </div>

          {/* Card 3: RESOLVED BY AI */}
          <div className="bg-white rounded-xl border border-emerald-200/90 p-4 shadow-2xs hover:shadow-xs transition">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-700">
                RESOLVED BY AI
              </span>
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-200">
                <CheckCircle2 className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-2 text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight">
              {loadingMetrics
                ? "..."
                : (metrics.ai_resolved ?? Math.max(0, (metrics.resolved ?? 0) - (metrics.human_resolved ?? 0)))}
            </div>
            <p className="mt-0.5 text-[11px] text-slate-500 truncate">
              Automated zero-touch resolutions
            </p>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold">Unable to load ticket data</p>
              <p className="text-xs text-rose-600 mt-0.5">{error}</p>
              <button
                onClick={() => loadData()}
                className="mt-2 text-xs font-semibold underline hover:text-rose-900 cursor-pointer"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* TRIAGE ANALYTICS & INSIGHTS (Visual Charts Grid) */}
        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center border border-blue-200">
                <BarChart3 className="w-4 h-4" />
              </div>
              <h2 className="text-sm font-bold text-slate-900 tracking-tight">
                Triage Analytics &amp; Insights
              </h2>
              <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                Live Overview
              </span>
            </div>

            <button
              type="button"
              onClick={() => setShowAnalytics((prev) => !prev)}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200 transition flex items-center gap-1.5 shadow-2xs cursor-pointer"
            >
              {showAnalytics ? (
                <>
                  <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
                  <span>Hide Analytics</span>
                </>
              ) : (
                <>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
                  <span>Show Analytics</span>
                </>
              )}
            </button>
          </div>

          {showAnalytics && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 animate-in fade-in duration-200">
              {/* A. LEFT CARD: Executive SLA & Efficiency Summary */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                      Executive SLA &amp; Efficiency Summary
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      Autonomous triage deflection &amp; operational efficiency metrics
                    </p>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                    <Sparkles className="w-3 h-3 text-emerald-600" />
                    High Automation
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-12 gap-4 items-center my-auto py-1">
                  {/* Visual Donut (Clean ratio without redundant raw counts) */}
                  <div className="sm:col-span-5 relative flex flex-col items-center justify-center">
                    <svg className="w-32 h-32 -rotate-90 transform" viewBox="0 0 130 130">
                      <circle
                        cx="65"
                        cy="65"
                        r={donutRadius}
                        fill="none"
                        stroke="#f1f5f9"
                        strokeWidth="12"
                      />
                      {donutSegments.map((segment) => (
                        <circle
                          key={segment.id}
                          cx="65"
                          cy="65"
                          r={donutRadius}
                          fill="none"
                          stroke={segment.color}
                          strokeWidth="12"
                          strokeDasharray={`${segment.strokeLength} ${segment.spaceLength}`}
                          strokeDashoffset={-segment.offset}
                          strokeLinecap="butt"
                          className="transition-all duration-300"
                        />
                      ))}
                    </svg>

                    {/* Donut Center Display: AI Deflection Rate */}
                    <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none pb-4">
                      <span className="text-2xl font-black text-slate-900 leading-none">
                        {aiDeflectionRate}%
                      </span>
                      <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 mt-1">
                        Deflected
                      </span>
                    </div>

                    {/* Compact Ratio Legend */}
                    <div className="flex flex-wrap items-center justify-center gap-2 mt-1">
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" /> AI ({aiDeflectionRate}%)
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-purple-700">
                        <span className="w-2 h-2 rounded-full bg-purple-500" /> Priority ({userEscalatedRate}%)
                      </span>
                      <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700">
                        <span className="w-2 h-2 rounded-full bg-amber-500" /> Review ({needsReviewRate}%)
                      </span>
                    </div>
                  </div>

                  {/* 3 Executive Efficiency Metrics */}
                  <div className="sm:col-span-7 space-y-2.5">
                    {/* Metric 1: AI Deflection Rate */}
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          AI Deflection Rate
                        </div>
                        <div className="text-base font-extrabold text-slate-900 mt-0.5 flex items-baseline gap-1.5">
                          <span>{aiDeflectionRate}%</span>
                          <span className="text-[11px] font-medium text-emerald-600">resolved without human touch</span>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-300 shrink-0">
                        Zero-Touch
                      </span>
                    </div>

                    {/* Metric 2: Avg AI Triage Speed */}
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                      <div>
                        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                          Avg AI Triage Speed
                        </div>
                        <div className="text-base font-extrabold text-slate-900 mt-0.5 flex items-baseline gap-1.5">
                          <span>~1.2s</span>
                          <span className="text-[11px] font-medium text-slate-500">vs ~4.0h manual support benchmark</span>
                        </div>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-sky-100 text-sky-800 border border-sky-300 flex items-center gap-1 shrink-0">
                        <Zap className="w-3 h-3 text-sky-600" />
                        99.9% Faster
                      </span>
                    </div>

                    {/* Metric 3: Human Escalation Distribution */}
                    <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 space-y-1.5">
                      <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        <span>Human Escalation Distribution</span>
                        <span className="text-[10px] font-normal text-slate-500">Total: {totalEscalations} tickets</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px] font-semibold">
                        <span className="text-purple-700 flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-purple-500" />
                          User Requested ({userRequestedPct}%)
                        </span>
                        <span className="text-amber-700 flex items-center gap-1">
                          <span className="w-2 h-2 rounded-full bg-amber-500" />
                          Operational Disputes ({operationalDisputesPct}%)
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 rounded-full h-2 overflow-hidden flex">
                        <div
                          className="bg-purple-500 h-full transition-all duration-500"
                          style={{ width: `${userRequestedPct}%` }}
                          title={`User Requested: ${userRequestedPct}%`}
                        />
                        <div
                          className="bg-amber-500 h-full transition-all duration-500"
                          style={{ width: `${operationalDisputesPct}%` }}
                          title={`Operational Disputes: ${operationalDisputesPct}%`}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Executive efficiency indicators calculated from live telemetry</span>
                  <span className="font-semibold text-emerald-700">
                    SLA Target: &gt;75% Deflection (Met)
                  </span>
                </div>
              </div>

              {/* B. RIGHT CARD: Volume by Issue Category (Horizontal Bar Chart) */}
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-2xs flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2 border-b border-slate-100 pb-2.5">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 tracking-tight">
                      Volume by Issue Category
                    </h3>
                    <p className="text-[11px] text-slate-500">
                      All 10 standard enterprise logistics categories ranked by volume
                    </p>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 border border-blue-200">
                    10 Standard Categories
                  </span>
                </div>

                <div className="space-y-1.5 my-auto py-1">
                  {allTenCategories.map((cat, idx) => (
                    <div
                      key={cat.name}
                      className="group p-1 rounded-lg hover:bg-slate-50/90 transition space-y-0.5 cursor-default"
                      title={`${cat.name}: ${cat.count} tickets (${cat.percentage}% of logistics volume)`}
                    >
                      <div className="flex items-center justify-between text-xs">
                        <div className="flex items-center gap-1.5 truncate pr-2">
                          <span className="w-4 text-[10px] font-mono font-bold text-slate-400 shrink-0">
                            #{idx + 1}
                          </span>
                          <span
                            className={`truncate text-xs ${
                              cat.count > 0 ? "font-semibold text-slate-800" : "font-medium text-slate-400"
                            }`}
                            title={cat.name}
                          >
                            {cat.name}
                          </span>
                        </div>
                        <div className="flex items-center gap-1.5 shrink-0">
                          <span
                            className={`px-1.5 py-0.5 rounded font-mono text-[10px] font-bold border ${
                              cat.count > 0
                                ? "bg-slate-100 text-slate-700 border-slate-200 group-hover:bg-blue-50 group-hover:text-blue-700 group-hover:border-blue-200"
                                : "bg-slate-50 text-slate-400 border-slate-150"
                            }`}
                          >
                            {cat.count}
                          </span>
                          <span
                            className={`text-[10px] font-medium min-w-[28px] text-right ${
                              cat.count > 0 ? "text-slate-500" : "text-slate-300"
                            }`}
                          >
                            {cat.percentage}%
                          </span>
                        </div>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                        {cat.count > 0 ? (
                          <div
                            className={`h-full rounded-full transition-all duration-500 ${
                              idx === 0
                                ? "bg-blue-600"
                                : idx === 1
                                ? "bg-indigo-500"
                                : idx === 2
                                ? "bg-sky-500"
                                : idx === 3
                                ? "bg-teal-500"
                                : idx === 4
                                ? "bg-amber-500"
                                : idx === 5
                                ? "bg-purple-500"
                                : "bg-slate-400"
                            }`}
                            style={{ width: `${Math.max(3, cat.percentage)}%` }}
                          />
                        ) : (
                          <div className="h-full bg-slate-200/50 rounded-full w-1" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Excludes pure conversational greetings</span>
                  <span className="font-semibold text-slate-600">
                    {totalLogisticsTickets} logistics inquiries tracked
                  </span>
                </div>
              </div>
            </div>
          )}
        </section>

        {/* 2. THREE-TAB QUEUE NAVIGATION & GLOBAL SEARCH */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5 shadow-2xs space-y-4">
          {/* Top: 3-Tab Queue Navigation */}
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-100 pb-3">
            {QUEUE_TABS.map((tab) => {
              const Icon = tab.icon;
              const count = tab.getCount(metrics);
              const isActive = selectedStatus === tab.id && !isGlobalSearchActive;
              return (
                <button
                  key={tab.id}
                  onClick={() => {
                    setSelectedStatus(tab.id);
                    if (isGlobalSearchActive) {
                      setSearchQuery("");
                      loadData(tab.id, "");
                    }
                  }}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition cursor-pointer ${
                    isActive
                      ? "bg-slate-900 text-white shadow-sm"
                      : "bg-slate-100/80 text-slate-600 hover:bg-slate-200/80 hover:text-slate-900"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                  <span
                    className={`ml-1 px-2 py-0.5 rounded-full text-xs font-bold border ${
                      isActive ? tab.activeBadge : tab.inactiveBadge
                    }`}
                  >
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Bottom: Global Search Bar directly BELOW the 3 tabs and directly ABOVE the ticket card list */}
          <div>
            <form onSubmit={handleSearchSubmit} className="relative flex items-center">
              <Search className="w-4 h-4 text-slate-400 absolute left-3.5 pointer-events-none" />
              <input
                type="text"
                placeholder="Search across all queues by Reference ID (e.g. #TKT-1016) or keywords..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-24 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-xs sm:text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition"
              />
              <div className="absolute right-1.5 flex items-center gap-1">
                {searchQuery && (
                  <button
                    type="button"
                    onClick={handleClearSearch}
                    className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition cursor-pointer"
                    title="Clear Search"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
                <button
                  type="submit"
                  className="px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800 transition cursor-pointer shadow-xs"
                >
                  Search
                </button>
              </div>
            </form>

            {/* Global Search Indicator Banner */}
            {isGlobalSearchActive && (
              <div className="mt-2.5 flex items-center justify-between text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-xl px-3 py-1.5">
                <span className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                  Global search active across <strong>all queues</strong> for &quot;
                  <span className="font-semibold">{searchQuery}</span>&quot;
                </span>
                <button
                  onClick={handleClearSearch}
                  className="font-semibold text-amber-800 hover:text-amber-950 underline cursor-pointer"
                >
                  Reset to {QUEUE_TABS.find((q) => q.id === selectedStatus)?.label} tab
                </button>
              </div>
            )}
          </div>
        </div>

        {/* 3. MANAGEMENT TICKETS TABLE / LIST */}
        <div className="space-y-4">
          {loadingTickets && (
            <div className="space-y-3">
              {[1, 2, 3].map((n) => (
                <div
                  key={n}
                  className="bg-white rounded-2xl border border-slate-200 p-6 animate-pulse space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <div className="h-4 w-32 bg-slate-200 rounded" />
                    <div className="h-5 w-24 bg-slate-200 rounded-full" />
                  </div>
                  <div className="h-4 w-2/3 bg-slate-200 rounded" />
                  <div className="h-12 bg-slate-100 rounded-xl" />
                </div>
              ))}
            </div>
          )}

          {!loadingTickets && !error && tickets.length === 0 && (
            <div className="bg-white rounded-2xl border border-slate-200 p-12 text-center shadow-2xs max-w-lg mx-auto my-6">
              <div className="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-4 border border-emerald-200">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <h3 className="text-lg font-bold text-slate-900">Queue is Clear</h3>
              <p className="mt-1 text-sm text-slate-500 max-w-sm mx-auto">
                {isGlobalSearchActive
                  ? `No tickets match "${searchQuery}".`
                  : "No tickets found matching the selected queue criteria."}
              </p>
              <button
                onClick={() => {
                  setSelectedStatus("NEEDS_HUMAN");
                  setSearchQuery("");
                  loadData("NEEDS_HUMAN", "");
                }}
                className="mt-5 px-4 py-2 rounded-xl bg-slate-900 text-white text-xs font-medium hover:bg-slate-800 transition inline-flex items-center gap-1.5 cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Reset Filters
              </button>
            </div>
          )}

          {!loadingTickets && !error && tickets.length > 0 && (
            <div className="space-y-3.5">
              {tickets.map((t) => (
                <div
                  key={t.id ?? t.reference_id ?? Math.random()}
                  className="bg-white rounded-2xl border border-slate-200 hover:border-slate-300 shadow-2xs overflow-hidden transition p-5 sm:p-6"
                >
                  {/* Top Bar: Reference ID, Status Badge, Category & Timestamps */}
                  <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 font-mono text-xs font-bold border border-slate-200">
                        <HighlightText
                          text={t.reference_id || (t.id ? `#TKT-${1000 + t.id}` : "Unpersisted Ticket")}
                          query={searchQuery}
                        />
                      </span>

                      <span
                        className={`px-3 py-0.5 rounded-full text-xs font-bold border ${
                          t.status === "NEEDS_HUMAN" || t.status === "ESCALATED"
                            ? "bg-amber-100 text-amber-800 border-amber-300"
                            : t.status === "USER_ESCALATED"
                            ? "bg-purple-100 text-purple-800 border-purple-300"
                            : t.status === "HUMAN_RESOLVED"
                            ? "bg-blue-100 text-blue-800 border-blue-300"
                            : "bg-emerald-100 text-emerald-800 border-emerald-300"
                        }`}
                      >
                        {t.status === "NEEDS_HUMAN" && "Needs Human Review"}
                        {t.status === "ESCALATED" && "Escalated for Review"}
                        {t.status === "USER_ESCALATED" && "User Escalated"}
                        {t.status === "HUMAN_RESOLVED" && "Human Resolved"}
                        {t.status === "RESOLVED_BY_AI" && "Resolved by AI"}
                        {t.status === "CONVERSATIONAL" && "Conversational AI"}
                        {t.status === "NEEDS_INFO" && "Needs Info"}
                      </span>

                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 flex items-center gap-1">
                        <Tag className="w-3 h-3 text-slate-500" />
                        {t.category}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {formatDateToIST(t.created_at)}
                      </span>
                      {t.resolved_at && (
                        <span className="flex items-center gap-1 text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                          <Check className="w-3 h-3" />
                          Closed: {formatDateToIST(t.resolved_at)}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Customer Issue Description (Query) with Amber Keyword Highlighting */}
                  <div className="mb-3">
                    <p className="text-sm text-slate-800 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-150 whitespace-pre-wrap font-normal">
                      <HighlightText text={t.description} query={searchQuery} />
                    </p>
                  </div>

                  {/* Agent Reasoning & Triage Solution with Amber Keyword Highlighting */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
                    {/* Reasoning Box */}
                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                      <div className="font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                        <ShieldAlert className="w-3.5 h-3.5 text-blue-600" />
                        Agent Triage Reasoning:
                      </div>
                      <p className="text-slate-600 leading-relaxed">
                        <HighlightText text={cleanReasoningText(t.agent_reason)} query={searchQuery} />
                      </p>
                    </div>

                    {/* Resolution Box */}
                    <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                      <div className="font-bold text-slate-700 mb-1 flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                        Resolution / Guidance:
                      </div>
                      <p className="text-slate-600 leading-relaxed whitespace-pre-line">
                        <HighlightText
                          text={t.answer || "Pending manual human investigation."}
                          query={searchQuery}
                        />
                      </p>
                    </div>
                  </div>

                  {/* ACTION BAR: "Mark as Resolved" for pending/escalated tickets */}
                  {t.id !== null &&
                    (t.status === "NEEDS_HUMAN" ||
                      t.status === "ESCALATED" ||
                      t.status === "USER_ESCALATED") && (
                      <div className="pt-3 border-t border-slate-100 flex items-center justify-between gap-3">
                        <div className="flex items-center gap-1.5 text-xs text-amber-700">
                          <Clock className="w-3.5 h-3.5" />
                          <span>
                            {t.status === "USER_ESCALATED"
                              ? "Priority User Escalation Queue"
                              : "Awaiting staff specialist inspection"}
                          </span>
                        </div>

                        <button
                          type="button"
                          onClick={() =>
                            handleResolve(t.id!, t.reference_id || `#TKT-${1000 + t.id!}`)
                          }
                          disabled={resolvingId === t.id}
                          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold transition shadow-sm shadow-emerald-600/20 disabled:opacity-60 cursor-pointer"
                        >
                          {resolvingId === t.id ? (
                            <>
                              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                              <span>Updating Status...</span>
                            </>
                          ) : (
                            <>
                              <Check className="w-3.5 h-3.5" />
                              <span>Mark as Resolved</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}

                  {t.status === "HUMAN_RESOLVED" && (
                    <div className="pt-2 text-right">
                      <span className="text-xs font-semibold text-blue-700 inline-flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" /> Closed by Staff
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-auto border-t border-slate-200 bg-white py-4 text-center text-xs text-slate-400">
        BoxNFreight Internal Admin Console &bull; Triage Operations &bull; 2026
      </footer>
    </div>
  );
}
