const timeFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

export function formatTime(value: string | null): string {
  if (!value) {
    return "Never";
  }

  return timeFormatter.format(new Date(value));
}

export function prettyLabel(value: string): string {
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function statusTone(value: string): string {
  if (value.includes("posted") || value.includes("online")) {
    return "good";
  }
  if (value.includes("pending") || value.includes("review")) {
    return "warn";
  }
  if (value.includes("rejected") || value.includes("failed") || value.includes("offline")) {
    return "bad";
  }
  return "neutral";
}
