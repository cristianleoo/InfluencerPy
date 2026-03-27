"use client";

import Link from "next/link";
import { useEffect, useState, useTransition } from "react";

import { type DashboardSnapshot, getDashboardSnapshot, startSystem, stopSystem } from "../lib/api";
import {
  ClockIcon,
  ComposeIcon,
  PlayIcon,
  RadarIcon,
  ReviewIcon,
  SparkIcon,
  StopIcon,
} from "./icons";
import { formatTime, statusTone } from "../lib/present";

export function OverviewPage({
  initialSnapshot = null,
}: {
  initialSnapshot?: DashboardSnapshot | null;
}) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(initialSnapshot);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const load = async () => {
    try {
      const data = await getDashboardSnapshot();
      setSnapshot(data);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load dashboard");
    }
  };

  useEffect(() => {
    if (!initialSnapshot) {
      void load();
    }

    const interval = window.setInterval(() => {
      void load();
    }, 10000);

    return () => window.clearInterval(interval);
  }, [initialSnapshot]);

  const runAction = (action: () => Promise<unknown>, successMessage: string) => {
    startTransition(() => {
      action()
        .then(() => {
          setNotice(successMessage);
          return load();
        })
        .catch((actionError) => {
          setError(actionError instanceof Error ? actionError.message : "Action failed");
        });
    });
  };

  if (!snapshot) {
    return (
      <section className="empty-page">
        <h2>Loading overview</h2>
        <p>{error ?? "Connecting to the local dashboard API."}</p>
        <button className="button button-primary" onClick={() => void load()} type="button">
          Retry
        </button>
      </section>
    );
  }

  const topScout = snapshot.scouts[0] ?? null;
  const hasPendingReviews = snapshot.stats.pending_reviews > 0;
  const isBotRunning = snapshot.system.bot_running;

  const nextAction = hasPendingReviews
    ? {
        label: `Review ${snapshot.stats.pending_reviews} pending draft${snapshot.stats.pending_reviews === 1 ? "" : "s"}`,
        description: "Clear the queue first so drafts do not pile up.",
        href: "/reviews",
      }
    : topScout
      ? {
          label: `Run ${topScout.name}`,
          description: "Pull a fresh batch of content from your strongest scout.",
          href: "/scouts",
        }
      : {
          label: "Create your first scout",
          description: "Set up a scout to start discovering content automatically.",
          href: "/scouts",
        };

  return (
    <section className="page-stack">
      <section className="home-summary">
        <div className="home-summary-copy">
          <p className="eyebrow">Workspace</p>
          <h2 className="hero-title">
            {hasPendingReviews
              ? `You have ${snapshot.stats.pending_reviews} draft${snapshot.stats.pending_reviews === 1 ? "" : "s"} waiting for review.`
              : isBotRunning
                ? "Your workflow is running smoothly."
                : "Automation is currently offline."}
          </h2>
          <p className="home-summary-text">
            Use home as your operator surface. Check the system state, pick the
            next action, and then move into flows, reviews, or history when you
            need detail.
          </p>

          <div className="signal-strip">
            <div className={`signal-chip ${statusTone(isBotRunning ? "online" : "offline")}`}>
              <span className="signal-dot" />
              {isBotRunning ? "System online" : "System offline"}
            </div>
            <div className="signal-chip neutral">{snapshot.stats.scheduled_scouts} scheduled scouts</div>
            <div className="signal-chip neutral">Updated {formatTime(snapshot.system.updated_at)}</div>
          </div>

          {notice ? <p className="feedback-banner success">{notice}</p> : null}
          {error ? <p className="feedback-banner error">{error}</p> : null}
        </div>

        <article className="primary-action-card">
          <div className="primary-action-head">
            <span className="panel-kicker">
              <SparkIcon className="inline-icon" />
              Up Next
            </span>
          </div>
          <strong>{nextAction.label}</strong>
          <p>{nextAction.description}</p>
          <div className="button-row">
            <Link className="button button-primary" href={nextAction.href}>
              <ReviewIcon className="button-icon" />
              Open now
            </Link>
            {isBotRunning ? (
              <button
                className="button button-secondary"
                disabled={isPending}
                onClick={() => runAction(stopSystem, "Bot service stopped")}
                type="button"
              >
                <StopIcon className="button-icon" />
                Stop automation
              </button>
            ) : (
              <button
                className="button button-secondary"
                disabled={isPending}
                onClick={() => runAction(startSystem, "Bot service started")}
                type="button"
              >
                <PlayIcon className="button-icon" />
                Start automation
              </button>
            )}
          </div>
        </article>
      </section>

      <section className="overview-stat-strip">
        <article className="compact-stat-card">
          <span className="compact-stat-label">
            <ReviewIcon className="metric-icon" />
            Pending
          </span>
          <strong>{snapshot.stats.pending_reviews}</strong>
          <p>Needs review</p>
        </article>
        <article className="compact-stat-card">
          <span className="compact-stat-label">
            <RadarIcon className="metric-icon" />
            Scouts
          </span>
          <strong>{snapshot.stats.scouts_total}</strong>
          <p>{snapshot.stats.scheduled_scouts} scheduled</p>
        </article>
        <article className="compact-stat-card">
          <span className="compact-stat-label">
            <ClockIcon className="metric-icon" />
            Last run
          </span>
          <strong>{topScout?.last_run ? formatTime(topScout.last_run) : "Never"}</strong>
          <p>{topScout?.name ?? "No scout yet"}</p>
        </article>
      </section>

      <section className="overview-grid-simple">
        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Shortcuts</p>
              <h2>Common actions</h2>
            </div>
          </div>
          <div className="shortcut-grid">
            <Link className="shortcut-card" href="/reviews">
              <ReviewIcon className="shortcut-icon" />
              <strong>Review drafts</strong>
              <p>Approve or reject pending items.</p>
            </Link>
            <Link className="shortcut-card" href="/scouts">
              <RadarIcon className="shortcut-icon" />
              <strong>Open flows</strong>
              <p>Build, run, and monitor your automation graph.</p>
            </Link>
            <Link className="shortcut-card" href="/compose">
              <ComposeIcon className="shortcut-icon" />
              <strong>Compose post</strong>
              <p>Write and route a quick post.</p>
            </Link>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Recent signal</p>
              <h2>Current focus</h2>
            </div>
          </div>
          <div className="focus-note">
            <div className="focus-note-head">
              <RadarIcon className="shortcut-icon small" />
              <strong>{topScout?.name ?? "No scout configured"}</strong>
            </div>
            <p>
              {topScout
                ? `Most recent flow activity was ${formatTime(topScout.last_run)}. Open Flows to run it again or adjust the graph.`
                : "Create a flow to start building a steady discovery and publishing system."}
            </p>
          </div>
        </article>
      </section>
    </section>
  );
}
