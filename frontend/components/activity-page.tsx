"use client";

import { useEffect, useMemo, useState } from "react";

import { type DashboardSnapshot, getDashboardSnapshot, getPosts, type Post } from "../lib/api";
import { formatTime, prettyLabel, statusTone } from "../lib/present";

export function ActivityPage({
  initialSnapshot = null,
}: {
  initialSnapshot?: DashboardSnapshot | null;
}) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(initialSnapshot);
  const [posts, setPosts] = useState<Post[]>(initialSnapshot?.recent_posts ?? []);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    try {
      const [data, history] = await Promise.all([
        getDashboardSnapshot(),
        getPosts({ limit: 100, q: query }),
      ]);
      setSnapshot(data);
      setPosts(history);
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load activity");
    }
  };

  useEffect(() => {
    void load();
  }, [initialSnapshot, query]);

  const statusEntries = useMemo(() => {
    if (!snapshot) {
      return [];
    }

    return Object.entries(snapshot.stats.posts_by_status).sort((a, b) => b[1] - a[1]);
  }, [snapshot]);

  if (!snapshot) {
    return (
      <section className="empty-page">
        <h2>Loading activity</h2>
        <p>{error ?? "Connecting to the local dashboard API."}</p>
      </section>
    );
  }

  return (
    <section className="page-stack">
      <section className="page-hero">
        <p className="eyebrow">Activity</p>
        <h2>Track publishing and workflow history.</h2>
        <p>
          This page keeps operational history separate from navigation and review work, so recent
          outcomes are easier to scan and audit.
        </p>
      </section>

      {error ? <p className="feedback-banner error">{error}</p> : null}

      <section className="panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Search</p>
            <h2>Find posts in history</h2>
          </div>
        </div>
        <input
          className="input"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search content, scout name, platform, or status..."
          value={query}
        />
      </section>

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Status Mix</p>
              <h2>Post states</h2>
            </div>
          </div>
          <div className="status-cluster">
            {statusEntries.map(([status, count]) => (
              <div className={`status-tile ${statusTone(status)}`} key={status}>
                <span>{prettyLabel(status)}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Pipeline Summary</p>
              <h2>Current totals</h2>
            </div>
          </div>
          <div className="insight-list">
            <div className="insight-row">
              <strong>{snapshot.stats.posts_total}</strong>
              <p>Total post records across generated, reviewed, and published content.</p>
            </div>
            <div className="insight-row">
              <strong>{snapshot.stats.rss_feeds}</strong>
              <p>RSS feeds actively stored in the local database.</p>
            </div>
            <div className="insight-row">
              <strong>{snapshot.stats.rss_entries}</strong>
              <p>RSS entries collected into the scouting intake layer.</p>
            </div>
          </div>
        </article>
      </section>

      <section className="activity-stack">
        {posts.map((post) => (
          <article className="activity-panel" key={post.id}>
            <div className="activity-copy">
              <strong>{post.scout_name || "Manual post"}</strong>
              <p>
                {post.content.slice(0, 220)}
                {post.content.length > 220 ? "..." : ""}
              </p>
            </div>
            <div className="activity-meta">
              <span>{prettyLabel(post.platform)}</span>
              <span>{prettyLabel(post.status)}</span>
              <span>{formatTime(post.created_at)}</span>
            </div>
          </article>
        ))}
      </section>
    </section>
  );
}
