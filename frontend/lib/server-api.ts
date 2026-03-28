import { headers } from "next/headers";

import type { DashboardSnapshot, SettingsSnapshot } from "./api";

const PUBLIC_BASE_PATH =
  process.env.NEXT_PUBLIC_BASE_PATH?.replace(/\/+$/, "") ?? "";

function normalizeServerApiBaseUrl(value: string | undefined): string | null {
  if (!value) {
    return null;
  }

  const trimmed = value.replace(/\/$/, "");
  if (!trimmed) {
    return null;
  }

  try {
    const url = new URL(trimmed);
    if (
      url.hostname === "0.0.0.0" ||
      url.hostname === "127.0.0.1" ||
      url.hostname === "localhost"
    ) {
      return null;
    }
  } catch {
    return trimmed;
  }

  return trimmed;
}

async function getServerApiBaseUrl(): Promise<string> {
  const explicitBaseUrl = normalizeServerApiBaseUrl(
    process.env.INFLUENCERPY_API_BASE_URL,
  );
  if (explicitBaseUrl) {
    return explicitBaseUrl;
  }

  const headerStore = await headers();
  const forwardedProto = headerStore.get("x-forwarded-proto");
  const forwardedHost = headerStore.get("x-forwarded-host");
  const host = forwardedHost || headerStore.get("host");
  if (host) {
    const protocol = forwardedProto || "http";
    return `${protocol}://${host}${PUBLIC_BASE_PATH}/api`;
  }

  return "http://127.0.0.1:8000/api";
}

export async function getInitialDashboardSnapshot(): Promise<DashboardSnapshot | null> {
  try {
    const apiBaseUrl = await getServerApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/dashboard`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as DashboardSnapshot;
  } catch {
    return null;
  }
}

export async function getInitialSettingsSnapshot(): Promise<SettingsSnapshot | null> {
  try {
    const apiBaseUrl = await getServerApiBaseUrl();
    const response = await fetch(`${apiBaseUrl}/settings`, {
      cache: "no-store",
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as SettingsSnapshot;
  } catch {
    return null;
  }
}
