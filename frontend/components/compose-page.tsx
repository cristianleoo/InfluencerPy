"use client";

import { useState, useTransition } from "react";

import { createQuickPost } from "../lib/api";

export function ComposePage() {
  const [content, setContent] = useState("");
  const [reviewBeforePublish, setReviewBeforePublish] = useState(true);
  const [platforms, setPlatforms] = useState<string[]>(["telegram"]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const togglePlatform = (platform: string) => {
    setPlatforms((current) =>
      current.includes(platform)
        ? current.filter((item) => item !== platform)
        : [...current, platform]
    );
  };

  const submit = () => {
    startTransition(() => {
      createQuickPost({
        content,
        platforms,
        review_before_publish: reviewBeforePublish,
      })
        .then(() => {
          setMessage("Post workflow completed");
          setError(null);
          if (!reviewBeforePublish) {
            setContent("");
          }
        })
        .catch((submitError) => {
          setError(submitError instanceof Error ? submitError.message : "Compose failed");
        });
    });
  };

  return (
    <section className="page-stack">
      <section className="page-hero">
        <p className="eyebrow">Compose</p>
        <h2>Quick post without touching the terminal.</h2>
        <p>
          This replaces the CLI quick-post flow. Write once, choose platforms, and either send the
          draft into review or publish immediately.
        </p>
      </section>

      {message ? <p className="feedback-banner success">{message}</p> : null}
      {error ? <p className="feedback-banner error">{error}</p> : null}

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Draft</p>
              <h2>Content</h2>
            </div>
          </div>
          <textarea
            className="input textarea"
            onChange={(event) => setContent(event.target.value)}
            placeholder="Write your post content here..."
            rows={14}
            value={content}
          />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Workflow</p>
              <h2>Delivery options</h2>
            </div>
          </div>

          <div className="settings-stack">
            <label className="toggle-row">
              <input
                checked={reviewBeforePublish}
                onChange={(event) => setReviewBeforePublish(event.target.checked)}
                type="checkbox"
              />
              <span>Route through review before publishing</span>
            </label>

            <div className="option-group">
              <span className="console-label">Platforms</span>
              <label className="toggle-row">
                <input
                  checked={platforms.includes("telegram")}
                  onChange={() => togglePlatform("telegram")}
                  type="checkbox"
                />
                <span>Telegram</span>
              </label>
              <label className="toggle-row">
                <input
                  checked={platforms.includes("x")}
                  onChange={() => togglePlatform("x")}
                  type="checkbox"
                />
                <span>X</span>
              </label>
              <label className="toggle-row">
                <input
                  checked={platforms.includes("substack")}
                  onChange={() => togglePlatform("substack")}
                  type="checkbox"
                />
                <span>Substack</span>
              </label>
            </div>

            <button
              className="button button-primary"
              disabled={isPending || !content.trim() || platforms.length === 0}
              onClick={submit}
              type="button"
            >
              Run compose flow
            </button>
          </div>
        </article>
      </section>
    </section>
  );
}
