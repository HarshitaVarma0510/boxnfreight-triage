/**
 * Utility functions for formatting dates across the BoxNFreight frontend.
 */

/**
 * Formats a given date string or Date object into Indian Standard Time (IST - Asia/Kolkata),
 * cleanly formatted like: "DD MMM YYYY, hh:mm A IST" (e.g. "04 Oct 2026, 09:49 AM IST").
 *
 * Handles SQLite CURRENT_TIMESTAMP strings ("YYYY-MM-DD HH:MM:SS" stored in UTC),
 * standard ISO strings with or without timezone offsets, and Date objects.
 */
export function formatDateToIST(dateInput?: string | Date | null): string {
  if (!dateInput) return "Just now";

  try {
    let normalized: string | Date = dateInput;

    if (typeof dateInput === "string") {
      const trimmed = dateInput.trim();
      if (!trimmed) return "Just now";

      // If the incoming date string lacks timezone info (e.g. doesn't end with 'Z'),
      // explicitly treat it as UTC by appending 'Z' before passing it to new Date().
      normalized =
        trimmed.endsWith("Z") || /[+-]\d{2}(?::?\d{2})?$/.test(trimmed)
          ? trimmed
          : `${trimmed.replace(" ", "T")}Z`;
    }

    const d = new Date(normalized);
    if (isNaN(d.getTime())) {
      return typeof dateInput === "string" ? dateInput : "Just now";
    }

    const formatter = new Intl.DateTimeFormat("en-IN", {
      timeZone: "Asia/Kolkata",
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: true,
    });

    const parts = formatter.formatToParts(d);
    const getPart = (type: Intl.DateTimeFormatPartTypes) =>
      parts.find((p) => p.type === type)?.value || "";

    const day = getPart("day");
    const month = getPart("month");
    const year = getPart("year");
    const hour = getPart("hour");
    const minute = getPart("minute");
    const dayPeriod = getPart("dayPeriod").toUpperCase();

    return `${day} ${month} ${year}, ${hour}:${minute} ${dayPeriod} IST`;
  } catch {
    return typeof dateInput === "string" ? dateInput : "Just now";
  }
}
