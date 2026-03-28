import type { DashboardSnapshot, SettingsSnapshot } from "./api";

const SERVER_API_BASE_URL =
  process.env.INFLUENCERPY_API_BASE_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000/api";

export async function getInitialDashboardSnapshot(): Promise<DashboardSnapshot | null> {
  try {
    const response = await fetch(`${SERVER_API_BASE_URL}/dashboard`, {
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
    const response = await fetch(`${SERVER_API_BASE_URL}/settings`, {
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
