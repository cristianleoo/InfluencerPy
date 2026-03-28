"use client";

import { useEffect, useState, useTransition } from "react";

import { getSettings, saveSettings, type SettingsSnapshot } from "../lib/api";

export function SettingsPage({
  initialSettings = null,
}: {
  initialSettings?: SettingsSnapshot | null;
}) {
  const [settings, setSettings] = useState<SettingsSnapshot | null>(initialSettings);
  const [form, setForm] = useState({
    geminiModel: initialSettings?.ai.gemini_model ?? "gemini-2.5-flash",
    embeddingsEnabled: initialSettings?.embeddings.enabled ?? true,
    embeddingsModel: initialSettings?.embeddings.model_name ?? "",
    geminiApiKey: "",
    telegramBotToken: "",
    telegramChatId: initialSettings?.values.telegram_chat_id ?? "",
    xApiKey: "",
    xApiSecret: "",
    xAccessToken: "",
    xAccessTokenSecret: "",
    substackSubdomain: initialSettings?.values.substack_subdomain ?? "",
    substackSid: "",
    substackLli: "",
    stabilityApiKey: "",
    langfuseHost: initialSettings?.values.langfuse_host ?? "",
    langfusePublicKey: "",
    langfuseSecretKey: "",
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const storageIssues = settings
    ? [
        !settings.storage.env_readable ? "The mounted .env file is not readable by the app runtime." : null,
        !settings.storage.env_writable ? "The mounted .env file is not writable, so saving credentials will fail." : null,
        !settings.storage.config_writable ? "The config file is not writable, so saving model or embedding settings will fail." : null,
      ].filter((issue): issue is string => Boolean(issue))
    : [];

  const load = async () => {
    try {
      const data = await getSettings();
      setSettings(data);
      setForm((current) => ({
        ...current,
        geminiModel: data.ai.gemini_model,
        embeddingsEnabled: data.embeddings.enabled,
        embeddingsModel: data.embeddings.model_name ?? "",
        telegramChatId: data.values.telegram_chat_id ?? "",
        substackSubdomain: data.values.substack_subdomain ?? "",
        langfuseHost: data.values.langfuse_host ?? "",
      }));
      setError(null);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load settings");
    }
  };

  useEffect(() => {
    if (!initialSettings) {
      void load();
    }
  }, [initialSettings]);

  const save = () => {
    startTransition(() => {
      saveSettings({
        ai: {
          default_provider: "gemini",
          gemini_model: form.geminiModel,
        },
        embeddings: {
          enabled: form.embeddingsEnabled,
          model_name: form.embeddingsModel || null,
        },
        credentials: {
          gemini_api_key: form.geminiApiKey,
          telegram_bot_token: form.telegramBotToken,
          telegram_chat_id: form.telegramChatId,
          x_api_key: form.xApiKey,
          x_api_secret: form.xApiSecret,
          x_access_token: form.xAccessToken,
          x_access_token_secret: form.xAccessTokenSecret,
          substack_subdomain: form.substackSubdomain,
          substack_sid: form.substackSid,
          substack_lli: form.substackLli,
          stability_api_key: form.stabilityApiKey,
          langfuse_host: form.langfuseHost,
          langfuse_public_key: form.langfusePublicKey,
          langfuse_secret_key: form.langfuseSecretKey,
        },
      })
        .then((data) => {
          setSettings(data);
          setMessage("Settings saved");
          setError(null);
        })
        .catch((saveError) => {
          setError(saveError instanceof Error ? saveError.message : "Failed to save settings");
        });
    });
  };

  return (
    <section className="page-stack">
      <section className="page-hero">
        <p className="eyebrow">Settings</p>
        <h2>Gemini-first configuration.</h2>
        <p>
          Keep the setup simple: Gemini is the supported AI path in the UI right now, and the
          model list comes from the current Gemini model catalog exposed by Google.
        </p>
      </section>

      {message ? <p className="feedback-banner success">{message}</p> : null}
      {error ? <p className="feedback-banner error">{error}</p> : null}
      {storageIssues.length > 0 ? (
        <div className="feedback-banner warning">
          <strong>Settings storage needs attention.</strong>
          <p>
            InfluencerPy can read the page, but some settings files are not accessible to the runtime.
            Fix the mounted file permissions before relying on saves from this screen.
          </p>
          <ul className="warning-list">
            {storageIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className="two-column-grid">
        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Gemini</p>
              <h2>Model and inference defaults</h2>
            </div>
          </div>
          <div className="settings-stack">
            <label className="field">
              <span>Gemini model</span>
              <select
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, geminiModel: event.target.value }))}
                value={form.geminiModel}
              >
                {(settings?.ai.gemini_models ?? []).map((modelId) => (
                  <option key={modelId} value={modelId}>
                    {modelId}
                  </option>
                ))}
              </select>
            </label>
            <label className="toggle-row">
              <input
                checked={form.embeddingsEnabled}
                onChange={(event) => setForm((current) => ({ ...current, embeddingsEnabled: event.target.checked }))}
                type="checkbox"
              />
              <span>Enable embeddings</span>
            </label>
            <label className="field">
              <span>Embedding model override</span>
              <input
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, embeddingsModel: event.target.value }))}
                placeholder="Leave empty for auto"
                value={form.embeddingsModel}
              />
            </label>
            <label className="field">
              <span>Gemini API key</span>
              <input
                className="input"
                onChange={(event) => setForm((current) => ({ ...current, geminiApiKey: event.target.value }))}
                type="password"
                value={form.geminiApiKey}
              />
            </label>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Configured Status</p>
              <h2>Current setup</h2>
            </div>
          </div>
          <div className="status-cluster">
            <div className={`status-tile ${settings?.storage.env_readable ? "good" : "warn"}`}>
              <span>.env readability</span>
              <strong>{settings?.storage.env_readable ? "Readable" : "Blocked"}</strong>
            </div>
            <div className={`status-tile ${settings?.storage.env_writable ? "good" : "warn"}`}>
              <span>.env write access</span>
              <strong>{settings?.storage.env_writable ? "Writable" : "Blocked"}</strong>
            </div>
            <div className={`status-tile ${settings?.storage.config_writable ? "good" : "warn"}`}>
              <span>Config write access</span>
              <strong>{settings?.storage.config_writable ? "Writable" : "Blocked"}</strong>
            </div>
            {Object.entries(settings?.credentials ?? {}).map(([name, configured]) => (
              <div className={`status-tile ${configured ? "good" : "bad"}`} key={name}>
                <span>{name}</span>
                <strong>{configured ? "Ready" : "Missing"}</strong>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="page-grid">
        <article className="panel">
          <div className="panel-header"><div><p className="eyebrow">Core services</p><h2>Telegram and publishing</h2></div></div>
          <div className="settings-stack">
            <label className="field"><span>Telegram bot token</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, telegramBotToken: event.target.value }))} type="password" value={form.telegramBotToken} /></label>
            <label className="field"><span>Telegram chat ID</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, telegramChatId: event.target.value }))} value={form.telegramChatId} /></label>
            <label className="field"><span>X API key</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, xApiKey: event.target.value }))} type="password" value={form.xApiKey} /></label>
            <label className="field"><span>X API secret</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, xApiSecret: event.target.value }))} type="password" value={form.xApiSecret} /></label>
            <label className="field"><span>X access token</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, xAccessToken: event.target.value }))} type="password" value={form.xAccessToken} /></label>
            <label className="field"><span>X access token secret</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, xAccessTokenSecret: event.target.value }))} type="password" value={form.xAccessTokenSecret} /></label>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header"><div><p className="eyebrow">Extended services</p><h2>Substack, Stability, Langfuse</h2></div></div>
          <div className="settings-stack">
            <label className="field"><span>Substack subdomain</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, substackSubdomain: event.target.value }))} value={form.substackSubdomain} /></label>
            <label className="field"><span>Substack sid</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, substackSid: event.target.value }))} type="password" value={form.substackSid} /></label>
            <label className="field"><span>Substack lli</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, substackLli: event.target.value }))} type="password" value={form.substackLli} /></label>
            <label className="field"><span>Stability API key</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, stabilityApiKey: event.target.value }))} type="password" value={form.stabilityApiKey} /></label>
            <label className="field"><span>Langfuse host</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, langfuseHost: event.target.value }))} value={form.langfuseHost} /></label>
            <label className="field"><span>Langfuse public key</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, langfusePublicKey: event.target.value }))} type="password" value={form.langfusePublicKey} /></label>
            <label className="field"><span>Langfuse secret key</span><input className="input" onChange={(event) => setForm((current) => ({ ...current, langfuseSecretKey: event.target.value }))} type="password" value={form.langfuseSecretKey} /></label>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header"><div><p className="eyebrow">Apply</p><h2>Save configuration</h2></div></div>
        <div className="button-row">
          <button className="button button-primary" disabled={isPending} onClick={save} type="button">
            Save settings
          </button>
          <button className="button button-secondary" disabled={isPending} onClick={() => void load()} type="button">
            Refresh model list
          </button>
        </div>
      </section>
    </section>
  );
}
