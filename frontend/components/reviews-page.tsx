"use client";

import { useEffect, useState, useTransition } from "react";

import { approvePost, type DashboardSnapshot, getDashboardSnapshot, rejectPost } from "../lib/api";
import { prettyLabel, statusTone } from "../lib/present";

export function ReviewsPage({
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
      setError(loadError instanceof Error ? loadError.message : "Failed to load reviews");
    }
  };

  useEffect(() => {
    if (!initialSnapshot) {
      void load();
    }
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
        <h2>Loading review queue</h2>
        <p>{error ?? "Connecting to the local dashboard API."}</p>
      </section>
    );
  }

  return (
    <section className="page-stack">
      <section className="page-hero">
        <p className="eyebrow">Reviews</p>
        <h2>Handle drafts in one focused queue.</h2>
        <p>
          Approvals and rejections now live in a dedicated review surface, so you do not have to
          scan a mixed dashboard to find the next decision.
        </p>
      </section>

      {notice ? <p className="feedback-banner success">{notice}</p> : null}
      {error ? <p className="feedback-banner error">{error}</p> : null}

      <section className="review-stack">
        {snapshot.pending_posts.length === 0 ? (
          <article className="panel">
            <p className="empty-copy">No drafts waiting for review.</p>
          </article>
        ) : (
          snapshot.pending_posts.map((post) => (
            <article className="review-panel" key={post.id}>
              <div className="review-head">
                <span>{post.scout_name || "Manual draft"}</span>
                <span className={`mini-status ${statusTone(post.status)}`}>
                  {prettyLabel(post.platform)} • {prettyLabel(post.status)}
                </span>
              </div>
              <p>{post.content}</p>
              <div className="button-row compact">
                <button
                  className="button button-primary"
                  disabled={isPending}
                  onClick={() => runAction(() => approvePost(post.id), "Draft approved")}
                  type="button"
                >
                  Approve
                </button>
                <button
                  className="button button-secondary"
                  disabled={isPending}
                  onClick={() => runAction(() => rejectPost(post.id), "Draft rejected")}
                  type="button"
                >
                  Reject
                </button>
              </div>
            </article>
          ))
        )}
      </section>
    </section>
  );
}
