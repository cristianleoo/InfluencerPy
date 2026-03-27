"use client";

import { useEffect, useState, useTransition } from "react";

import { getLogs } from "../lib/api";

export function LogsPage() {
  const [logs, setLogs] = useState<{ app: string[]; bot: string[] }>({ app: [], bot: [] });
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const load = () => {
    startTransition(() => {
      getLogs(120)
        .then((data) => {
          setLogs(data);
          setError(null);
        })
        .catch((loadError) => {
          setError(loadError instanceof Error ? loadError.message : "Failed to load logs");
        });
    });
  };

  useEffect(() => {
    load();
    const interval = window.setInterval(load, 5000);
    return () => window.clearInterval(interval);
  }, []);

  return (
    <section className="page-stack">
      <section className="page-hero">
        <p className="eyebrow">Logs</p>
        <h2>Inspect runtime output in the UI.</h2>
        <p>
          This replaces the common terminal tailing workflow for normal operation. You can still
          use CLI logs as fallback, but the web surface should be enough day to day.
        </p>
      </section>

      {error ? <p className="feedback-banner error">{error}</p> : null}

      <div className="button-row">
        <button className="button button-secondary" disabled={isPending} onClick={load} type="button">
          Refresh logs
        </button>
      </div>

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel-header"><div><p className="eyebrow">Application</p><h2>App log</h2></div></div>
          <pre className="log-viewer">{logs.app.join("\n") || "No app logs yet."}</pre>
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="eyebrow">Bot Service</p><h2>Bot log</h2></div></div>
          <pre className="log-viewer">{logs.bot.join("\n") || "No bot logs yet."}</pre>
        </article>
      </section>
    </section>
  );
}
