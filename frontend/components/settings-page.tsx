"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import {
  getSavedGeminiKey,
  getSettings,
  saveAndTestGeminiSettings,
  saveAndTestSubstackSettings,
  saveAndTestTelegramSettings,
  saveAndTestXSettings,
  saveSettings,
  type SettingsSnapshot,
} from "../lib/api";
import {
  ComposeIcon,
  ReviewIcon,
  SparkIcon,
} from "./icons";

type IntegrationCardProps = {
  title: string;
  eyebrow: string;
  description: string;
  configured: boolean;
  optional?: boolean;
  enabled?: boolean;
  enabledLabel?: string;
  onToggleEnabled?: (enabled: boolean) => void;
  children: React.ReactNode;
};

function IntegrationCard({
  title,
  eyebrow,
  description,
  configured,
  optional = true,
  enabled = true,
  enabledLabel,
  onToggleEnabled,
  children,
}: IntegrationCardProps) {
  return (
    <article className="settings-integration-card">
      <div className="settings-integration-head">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
        <span className={`status-chip ${configured ? "good" : optional ? "neutral" : "warn"}`}>
          {configured ? "Connected" : optional ? "Optional" : "Required"}
        </span>
      </div>
      {onToggleEnabled ? (
        <label className="settings-enable-row">
          <input
            checked={enabled}
            onChange={(event) => onToggleEnabled(event.target.checked)}
            type="checkbox"
          />
          <span>{enabledLabel ?? `Set up ${title} now`}</span>
        </label>
      ) : null}
      {enabled ? (
        <div className="settings-stack">{children}</div>
      ) : (
        <div className="settings-collapsed-note">
          Leave this disconnected for now. You can come back later when you want to enable it.
        </div>
      )}
    </article>
  );
}

function preserveIfFilled(value: string) {
  return value.trim() ? value.trim() : undefined;
}

export function SettingsPage({
  initialSettings = null,
}: {
  initialSettings?: SettingsSnapshot | null;
}) {
  const [activeTab, setActiveTab] = useState<"core" | "delivery" | "advanced" | "workspace">("core");
  const [settings, setSettings] = useState<SettingsSnapshot | null>(initialSettings);
  const [form, setForm] = useState({
    geminiModel: initialSettings?.ai.gemini_model ?? "gemini-2.5-flash",
    customGeminiModel: "",
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
  const [isGeminiPending, startGeminiTransition] = useTransition();
  const [deliveryPending, setDeliveryPending] = useState<null | "telegram" | "x" | "substack">(null);
  const [savedGeminiKey, setSavedGeminiKey] = useState<string | null>(null);
  const [isGeminiSecretPending, setIsGeminiSecretPending] = useState(false);
  const [optionalSetup, setOptionalSetup] = useState({
    telegram: initialSettings?.credentials.telegram ?? false,
    x: initialSettings?.credentials.x ?? false,
    substack: initialSettings?.credentials.substack ?? false,
    stability: initialSettings?.credentials.stability ?? false,
    langfuse: initialSettings?.credentials.langfuse ?? false,
  });

  const storageIssues = settings
    ? [
        !settings.storage.env_readable ? "The mounted .env file is not readable by the app runtime." : null,
        !settings.storage.env_writable ? "The mounted .env file is not writable, so saving credentials will fail." : null,
        !settings.storage.config_writable ? "The config file is not writable, so saving model or embedding settings will fail." : null,
      ].filter((issue): issue is string => Boolean(issue))
    : [];

  const modelOptions = settings?.ai.gemini_models ?? [];
  const activeModelId = form.customGeminiModel.trim() || form.geminiModel;

  const setupProgress = useMemo(() => {
    const steps = [
      Boolean(settings?.credentials.gemini),
      Boolean(activeModelId),
      Boolean(settings?.credentials.telegram || settings?.credentials.substack || settings?.credentials.x),
    ];
    return steps.filter(Boolean).length;
  }, [activeModelId, settings?.credentials]);

  const load = async () => {
    try {
      const data = await getSettings();
      setSettings(data);
      setForm((current) => ({
        ...current,
        geminiModel: data.ai.gemini_model,
        customGeminiModel: "",
        embeddingsEnabled: data.embeddings.enabled,
        embeddingsModel: data.embeddings.model_name ?? "",
        telegramChatId: data.values.telegram_chat_id ?? "",
        substackSubdomain: data.values.substack_subdomain ?? "",
        langfuseHost: data.values.langfuse_host ?? "",
      }));
      setOptionalSetup({
        telegram: data.credentials.telegram,
        x: data.credentials.x,
        substack: data.credentials.substack,
        stability: data.credentials.stability,
        langfuse: data.credentials.langfuse,
      });
      setSavedGeminiKey(null);
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
      const credentialPayload: Record<string, string> = {};

      const maybeAssign = (key: string, value: string) => {
        const next = preserveIfFilled(value);
        if (next !== undefined) {
          credentialPayload[key] = next;
        }
      };

      maybeAssign("gemini_api_key", form.geminiApiKey);
      maybeAssign("telegram_bot_token", form.telegramBotToken);
      credentialPayload.telegram_chat_id = form.telegramChatId.trim();
      maybeAssign("x_api_key", form.xApiKey);
      maybeAssign("x_api_secret", form.xApiSecret);
      maybeAssign("x_access_token", form.xAccessToken);
      maybeAssign("x_access_token_secret", form.xAccessTokenSecret);
      credentialPayload.substack_subdomain = form.substackSubdomain.trim();
      maybeAssign("substack_sid", form.substackSid);
      maybeAssign("substack_lli", form.substackLli);
      maybeAssign("stability_api_key", form.stabilityApiKey);
      credentialPayload.langfuse_host = form.langfuseHost.trim();
      maybeAssign("langfuse_public_key", form.langfusePublicKey);
      maybeAssign("langfuse_secret_key", form.langfuseSecretKey);

      saveSettings({
        ai: {
          default_provider: "gemini",
          gemini_model: activeModelId,
        },
        embeddings: {
          enabled: form.embeddingsEnabled,
          model_name: form.embeddingsModel || null,
        },
        credentials: credentialPayload,
      })
        .then((data) => {
          setSettings(data);
          setMessage("Settings saved");
          setError(null);
          setForm((current) => ({
            ...current,
            geminiApiKey: "",
            telegramBotToken: "",
            xApiKey: "",
            xApiSecret: "",
            xAccessToken: "",
            xAccessTokenSecret: "",
            substackSid: "",
            substackLli: "",
            stabilityApiKey: "",
            langfusePublicKey: "",
            langfuseSecretKey: "",
            customGeminiModel: "",
            geminiModel: data.ai.gemini_model,
          }));
          setSavedGeminiKey(null);
        })
        .catch((saveError) => {
          setError(saveError instanceof Error ? saveError.message : "Failed to save settings");
        });
    });
  };

  const saveAndTestGemini = () => {
    startGeminiTransition(() => {
      saveAndTestGeminiSettings({
        ai: {
          gemini_model: activeModelId,
        },
        credentials: {
          gemini_api_key: form.geminiApiKey.trim(),
        },
      })
        .then(({ message: successMessage, settings: nextSettings }) => {
          setSettings(nextSettings);
          setMessage(successMessage);
          setError(null);
          setForm((current) => ({
            ...current,
            geminiApiKey: "",
            customGeminiModel: "",
            geminiModel: nextSettings.ai.gemini_model,
          }));
        })
        .catch((saveError) => {
          setError(saveError instanceof Error ? saveError.message : "Failed to connect Gemini");
        });
    });
  };

  const saveAndTestTelegram = () => {
    setDeliveryPending("telegram");
    saveAndTestTelegramSettings({
      telegram_bot_token: form.telegramBotToken.trim(),
      telegram_chat_id: form.telegramChatId.trim(),
    })
      .then(({ message: successMessage, settings: nextSettings }) => {
        setSettings(nextSettings);
        setMessage(successMessage);
        setError(null);
        setForm((current) => ({
          ...current,
          telegramBotToken: "",
          telegramChatId: nextSettings.values.telegram_chat_id ?? "",
        }));
        setSavedGeminiKey(null);
      })
      .catch((saveError) => {
        setError(saveError instanceof Error ? saveError.message : "Failed to validate Telegram");
      })
      .finally(() => setDeliveryPending(null));
  };

  const toggleSavedGeminiKey = () => {
    if (savedGeminiKey !== null) {
      setSavedGeminiKey(null);
      return;
    }

    setIsGeminiSecretPending(true);
    getSavedGeminiKey()
      .then(({ value }) => {
        setSavedGeminiKey(value || "");
        setError(null);
      })
      .catch((loadError) => {
        setError(loadError instanceof Error ? loadError.message : "Failed to load saved Gemini key");
      })
      .finally(() => setIsGeminiSecretPending(false));
  };

  const saveAndTestX = () => {
    setDeliveryPending("x");
    saveAndTestXSettings({
      x_api_key: form.xApiKey.trim(),
      x_api_secret: form.xApiSecret.trim(),
      x_access_token: form.xAccessToken.trim(),
      x_access_token_secret: form.xAccessTokenSecret.trim(),
    })
      .then(({ message: successMessage, settings: nextSettings }) => {
        setSettings(nextSettings);
        setMessage(successMessage);
        setError(null);
        setForm((current) => ({
          ...current,
          xApiKey: "",
          xApiSecret: "",
          xAccessToken: "",
          xAccessTokenSecret: "",
        }));
      })
      .catch((saveError) => {
        setError(saveError instanceof Error ? saveError.message : "Failed to validate X");
      })
      .finally(() => setDeliveryPending(null));
  };

  const saveAndTestSubstack = () => {
    setDeliveryPending("substack");
    saveAndTestSubstackSettings({
      substack_subdomain: form.substackSubdomain.trim(),
      substack_sid: form.substackSid.trim(),
      substack_lli: form.substackLli.trim(),
    })
      .then(({ message: successMessage, settings: nextSettings }) => {
        setSettings(nextSettings);
        setMessage(successMessage);
        setError(null);
        setForm((current) => ({
          ...current,
          substackSubdomain: nextSettings.values.substack_subdomain ?? "",
          substackSid: "",
          substackLli: "",
        }));
      })
      .catch((saveError) => {
        setError(saveError instanceof Error ? saveError.message : "Failed to validate Substack");
      })
      .finally(() => setDeliveryPending(null));
  };

  return (
    <section className="page-stack settings-page-shell">
      <section className="settings-hero panel">
        <div className="settings-hero-main">
          <div>
            <p className="eyebrow">Settings</p>
            <h2>Set up InfluencerPy in the right order.</h2>
            <p>
              Start with Gemini so the workspace can plan and generate. Connect Telegram or the
              other services only when you are ready to use them.
            </p>
          </div>
          <div className="settings-hero-progress">
            <span className="settings-progress-kicker">Workspace readiness</span>
            <strong>{setupProgress}/3</strong>
            <p>Gemini, model choice, and at least one delivery path.</p>
          </div>
        </div>
        <div className="settings-summary-grid">
          <div className="settings-summary-card">
            <SparkIcon className="settings-summary-icon" />
            <div>
              <span>Gemini</span>
              <strong>{settings?.credentials.gemini ? "Connected" : "Needed first"}</strong>
            </div>
          </div>
          <div className="settings-summary-card">
            <ComposeIcon className="settings-summary-icon" />
            <div>
              <span>Active model</span>
              <strong>{activeModelId || "Choose one"}</strong>
            </div>
          </div>
          <div className="settings-summary-card">
            <ReviewIcon className="settings-summary-icon" />
            <div>
              <span>Delivery</span>
              <strong>
                {settings?.credentials.telegram
                  ? "Telegram ready"
                  : settings?.credentials.substack
                    ? "Substack ready"
                    : settings?.credentials.x
                      ? "X ready"
                      : "Optional"}
              </strong>
            </div>
          </div>
        </div>
      </section>

      {message ? <p className="feedback-banner success">{message}</p> : null}
      {error ? <p className="feedback-banner error">{error}</p> : null}
      {storageIssues.length > 0 ? (
        <div className="feedback-banner warning">
          <strong>Settings storage needs attention.</strong>
          <p>
            The page is available, but the runtime cannot fully access its mounted settings files.
            Fix those permissions before relying on changes from this screen.
          </p>
          <ul className="warning-list">
            {storageIssues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        </div>
      ) : null}

      <section className="settings-tab-bar panel">
        <button
          className={`settings-tab ${activeTab === "core" ? "active" : ""}`}
          onClick={() => setActiveTab("core")}
          type="button"
        >
          <span>Core</span>
          <strong>Gemini and models</strong>
        </button>
        <button
          className={`settings-tab ${activeTab === "delivery" ? "active" : ""}`}
          onClick={() => setActiveTab("delivery")}
          type="button"
        >
          <span>Delivery</span>
          <strong>Telegram, X, Substack</strong>
        </button>
        <button
          className={`settings-tab ${activeTab === "advanced" ? "active" : ""}`}
          onClick={() => setActiveTab("advanced")}
          type="button"
        >
          <span>Advanced</span>
          <strong>Stability, Langfuse, embeddings</strong>
        </button>
        <button
          className={`settings-tab ${activeTab === "workspace" ? "active" : ""}`}
          onClick={() => setActiveTab("workspace")}
          type="button"
        >
          <span>Workspace</span>
          <strong>Health and readiness</strong>
        </button>
      </section>

      {activeTab === "core" ? (
        <section className="settings-tab-layout">
          <div className="settings-tab-main">
            <section className="settings-essential-grid">
              <article className="panel settings-primary-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Step 1</p>
                    <h2>Connect Gemini</h2>
                  </div>
                  <span className={`status-chip ${settings?.credentials.gemini ? "good" : "warn"}`}>
                    {settings?.credentials.gemini ? "Ready" : "Required"}
                  </span>
                </div>
                <div className="settings-stack">
                  <p className="settings-section-copy">
                    This powers planning, generation, and the AI flow builder. Add the API key once, then
                    choose the default model ID below.
                  </p>
                  <label className="field">
                    <span>Gemini API key</span>
                    <input
                      className="input"
                      onChange={(event) => setForm((current) => ({ ...current, geminiApiKey: event.target.value }))}
                      placeholder={settings?.credentials.gemini ? "Leave empty to keep the saved API key" : "Paste your Gemini API key"}
                      type="password"
                      value={form.geminiApiKey}
                    />
                  </label>
                  {settings?.credentials.gemini ? (
                    <div className="settings-secret-row">
                      <div className="settings-secret-display">
                        <span>Saved key</span>
                        <strong>{savedGeminiKey ?? "****"}</strong>
                      </div>
                      <button
                        className="button button-secondary"
                        disabled={isGeminiSecretPending}
                        onClick={toggleSavedGeminiKey}
                        type="button"
                      >
                        {isGeminiSecretPending ? "Loading..." : savedGeminiKey !== null ? "Hide key" : "Show key"}
                      </button>
                    </div>
                  ) : null}
                  <div className="button-row">
                    <button
                      className="button button-primary"
                      disabled={isPending || isGeminiPending}
                      onClick={saveAndTestGemini}
                      type="button"
                    >
                      {isGeminiPending ? "Testing Gemini..." : "Save and test Gemini"}
                    </button>
                  </div>
                  <div className="helper-note">
                    <span>How it works</span>
                    <p>
                      This saves the Gemini API key only after the connection test succeeds. Leaving the
                      field empty keeps the current saved key.
                    </p>
                  </div>
                </div>
              </article>

              <article className="panel settings-primary-panel">
                <div className="panel-header">
                  <div>
                    <p className="eyebrow">Step 2</p>
                    <h2>Choose the default model ID</h2>
                  </div>
                  <span className="status-chip neutral">Gemini catalog</span>
                </div>
                <div className="settings-stack">
                  <p className="settings-section-copy">
                    Pick from the live Gemini model IDs, or paste a specific model ID if you want to pin one manually.
                  </p>
                  <label className="field">
                    <span>Model IDs list</span>
                    <select
                      className="input"
                      onChange={(event) => setForm((current) => ({ ...current, geminiModel: event.target.value, customGeminiModel: "" }))}
                      value={form.customGeminiModel ? "" : form.geminiModel}
                    >
                      {modelOptions.map((modelId) => (
                        <option key={modelId} value={modelId}>
                          {modelId}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span>Or paste a custom model ID</span>
                    <input
                      className="input"
                      list="gemini-model-ids"
                      onChange={(event) => setForm((current) => ({ ...current, customGeminiModel: event.target.value }))}
                      placeholder="Optional custom Gemini model ID"
                      value={form.customGeminiModel}
                    />
                    <datalist id="gemini-model-ids">
                      {modelOptions.map((modelId) => (
                        <option key={modelId} value={modelId} />
                      ))}
                    </datalist>
                  </label>
                </div>
              </article>
            </section>
          </div>

          <aside className="settings-tab-side">
            <article className="panel settings-side-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">What to do first</p>
                  <h2>Simple setup path</h2>
                </div>
              </div>
              <div className="settings-checklist">
                <div>
                  <SparkIcon className="settings-check-icon" />
                  <div>
                    <strong>1. Add Gemini</strong>
                    <p>This is the only required provider for the current UI.</p>
                  </div>
                </div>
                <div>
                  <ComposeIcon className="settings-check-icon" />
                  <div>
                    <strong>2. Pick the model ID</strong>
                    <p>Use the live model list or pin a custom Gemini model ID.</p>
                  </div>
                </div>
                <div>
                  <ReviewIcon className="settings-check-icon" />
                  <div>
                    <strong>3. Add delivery later</strong>
                    <p>Telegram, Substack, X, Stability, and Langfuse are optional.</p>
                  </div>
                </div>
              </div>
            </article>
          </aside>
        </section>
      ) : null}

      {activeTab === "delivery" ? (
        <section className="settings-tab-layout">
          <div className="settings-tab-main">
            <section className="panel settings-delivery-hero">
              <div>
                <p className="eyebrow">Delivery</p>
                <h2>Choose where drafts go after the agent finishes.</h2>
                <p>
                  Start with Telegram if you want review built into the workflow. Add X or
                  Substack later when you are ready to publish directly.
                </p>
              </div>
              <div className="settings-delivery-summary">
                <div className="settings-delivery-summary-card">
                  <span>Best first step</span>
                  <strong>{settings?.credentials.telegram ? "Telegram is ready" : "Connect Telegram review"}</strong>
                </div>
                <div className="settings-delivery-summary-card">
                  <span>Direct publishing</span>
                  <strong>
                    {settings?.credentials.x || settings?.credentials.substack ? "At least one channel is live" : "Optional later"}
                  </strong>
                </div>
              </div>
            </section>

            <article className="panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Delivery</p>
                  <h2>Review and publishing channels</h2>
                </div>
                <span className="status-chip neutral">Optional</span>
              </div>
              <div className="settings-delivery-grid">
                <IntegrationCard
                  configured={Boolean(settings?.credentials.telegram)}
                  description="Recommended if you want draft review or delivery through Telegram. Set this up after Gemini is ready."
                  eyebrow="Telegram"
                  title="Connect Telegram"
                  enabled={optionalSetup.telegram}
                  enabledLabel="Set up Telegram now"
                  onToggleEnabled={(enabled) =>
                    setOptionalSetup((current) => ({ ...current, telegram: enabled }))
                  }
                >
                  <div className="settings-delivery-callout">
                    <strong>Recommended path</strong>
                    <p>Use Telegram when you want drafts to arrive in a chat for approval before anything publishes outward.</p>
                  </div>
                  <div className="settings-guidance-list">
                    <div>
                      <strong>1. Validate the bot</strong>
                      <p>Paste the bot token and test it first. The token is only saved after validation succeeds.</p>
                    </div>
                    <div>
                      <strong>2. Add the destination chat</strong>
                      <p>Chat ID is optional at first, but include it if you want the full route checked too.</p>
                    </div>
                  </div>
                  <div className="settings-inline-grid">
                    <label className="field">
                      <span>Telegram bot token</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, telegramBotToken: event.target.value }))}
                        placeholder={settings?.credentials.telegram ? "Leave empty to keep the saved Telegram bot token" : "Dedicated Telegram bot token"}
                        type="password"
                        value={form.telegramBotToken}
                      />
                    </label>
                    <label className="field">
                      <span>Telegram chat ID</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, telegramChatId: event.target.value }))}
                        placeholder="Optional review or destination chat ID"
                      value={form.telegramChatId}
                    />
                  </label>
                  </div>
                  <div className="button-row">
                    <button
                      className="button button-primary"
                      disabled={isPending || isGeminiPending || deliveryPending !== null}
                      onClick={saveAndTestTelegram}
                      type="button"
                    >
                      {deliveryPending === "telegram" ? "Testing Telegram..." : "Save and test Telegram"}
                    </button>
                  </div>
                </IntegrationCard>

                <div className="settings-delivery-secondary">
                  <IntegrationCard
                    configured={Boolean(settings?.credentials.x)}
                    description="Only needed if you want to publish directly to X. You can leave this disconnected while you build flows."
                    eyebrow="X"
                    title="Connect X publishing"
                    enabled={optionalSetup.x}
                    enabledLabel="Set up X now"
                    onToggleEnabled={(enabled) =>
                      setOptionalSetup((current) => ({ ...current, x: enabled }))
                    }
                  >
                    <div className="settings-guidance-list compact">
                      <div>
                        <strong>Publish only when ready</strong>
                        <p>This checks the connected X account before InfluencerPy is allowed to post there.</p>
                      </div>
                    </div>
                    <label className="field">
                      <span>X API key</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, xApiKey: event.target.value }))}
                        placeholder={settings?.credentials.x ? "Leave empty to keep the saved X API key" : "X API key"}
                        type="password"
                        value={form.xApiKey}
                      />
                    </label>
                    <div className="settings-inline-grid">
                      <label className="field">
                        <span>X API secret</span>
                        <input
                          className="input"
                          onChange={(event) => setForm((current) => ({ ...current, xApiSecret: event.target.value }))}
                          type="password"
                          value={form.xApiSecret}
                        />
                      </label>
                      <label className="field">
                        <span>X access token</span>
                        <input
                          className="input"
                          onChange={(event) => setForm((current) => ({ ...current, xAccessToken: event.target.value }))}
                          type="password"
                          value={form.xAccessToken}
                        />
                      </label>
                    </div>
                    <label className="field">
                      <span>X access token secret</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, xAccessTokenSecret: event.target.value }))}
                        type="password"
                        value={form.xAccessTokenSecret}
                      />
                    </label>
                    <div className="button-row">
                      <button
                        className="button button-secondary"
                        disabled={isPending || isGeminiPending || deliveryPending !== null}
                        onClick={saveAndTestX}
                        type="button"
                      >
                        {deliveryPending === "x" ? "Testing X..." : "Save and test X"}
                      </button>
                    </div>
                  </IntegrationCard>

                  <IntegrationCard
                    configured={Boolean(settings?.credentials.substack)}
                    description="Connect this only if you want to publish or draft directly to Substack."
                    eyebrow="Substack"
                    title="Connect Substack"
                    enabled={optionalSetup.substack}
                    enabledLabel="Set up Substack now"
                    onToggleEnabled={(enabled) =>
                      setOptionalSetup((current) => ({ ...current, substack: enabled }))
                    }
                  >
                    <div className="settings-guidance-list compact">
                      <div>
                        <strong>Validate the draft route</strong>
                        <p>We verify the publication and auth cookies first so you know draft creation can work.</p>
                      </div>
                    </div>
                    <label className="field">
                      <span>Substack subdomain</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, substackSubdomain: event.target.value }))}
                        placeholder="your-substack"
                        value={form.substackSubdomain}
                      />
                    </label>
                    <div className="settings-inline-grid">
                      <label className="field">
                        <span>Substack sid</span>
                        <input
                          className="input"
                          onChange={(event) => setForm((current) => ({ ...current, substackSid: event.target.value }))}
                          placeholder={settings?.credentials.substack ? "Leave empty to keep the saved sid" : "Substack sid"}
                          type="password"
                          value={form.substackSid}
                        />
                      </label>
                      <label className="field">
                        <span>Substack lli</span>
                        <input
                          className="input"
                          onChange={(event) => setForm((current) => ({ ...current, substackLli: event.target.value }))}
                          placeholder={settings?.credentials.substack ? "Leave empty to keep the saved lli" : "Substack lli"}
                          type="password"
                          value={form.substackLli}
                        />
                      </label>
                    </div>
                    <div className="button-row">
                      <button
                        className="button button-secondary"
                        disabled={isPending || isGeminiPending || deliveryPending !== null}
                        onClick={saveAndTestSubstack}
                        type="button"
                      >
                        {deliveryPending === "substack" ? "Testing Substack..." : "Save and test Substack"}
                      </button>
                    </div>
                  </IntegrationCard>
                </div>
              </div>
            </article>
          </div>

          <aside className="settings-tab-side">
            <article className="panel settings-side-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Recommended order</p>
                  <h2>How to approach delivery</h2>
                </div>
              </div>
              <div className="settings-checklist">
                <div>
                  <ReviewIcon className="settings-check-icon" />
                  <div>
                    <strong>1. Start with Telegram review</strong>
                    <p>It is the easiest way to validate drafts before turning on direct publishing.</p>
                  </div>
                </div>
                <div>
                  <ComposeIcon className="settings-check-icon" />
                  <div>
                    <strong>2. Add direct channels later</strong>
                    <p>X and Substack make sense after your prompts and flows are already behaving well.</p>
                  </div>
                </div>
              </div>
            </article>

            <article className="panel settings-side-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Live status</p>
                  <h2>Current delivery setup</h2>
                </div>
              </div>
              <div className="status-cluster settings-status-cluster">
                <div className={`status-tile ${settings?.credentials.telegram ? "good" : "neutral"}`}>
                  <span>Telegram</span>
                  <strong>{settings?.credentials.telegram ? "Ready" : "Not set"}</strong>
                </div>
                <div className={`status-tile ${settings?.credentials.x ? "good" : "neutral"}`}>
                  <span>X</span>
                  <strong>{settings?.credentials.x ? "Ready" : "Not set"}</strong>
                </div>
                <div className={`status-tile ${settings?.credentials.substack ? "good" : "neutral"}`}>
                  <span>Substack</span>
                  <strong>{settings?.credentials.substack ? "Ready" : "Not set"}</strong>
                </div>
              </div>
            </article>
          </aside>
        </section>
      ) : null}

      {activeTab === "advanced" ? (
        <section className="settings-tab-layout">
          <div className="settings-tab-main">
            <article className="panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Advanced</p>
                  <h2>Optional supporting services</h2>
                </div>
                <span className="status-chip neutral">Optional</span>
              </div>
              <div className="settings-card-stack">
                <IntegrationCard
                  configured={Boolean(settings?.credentials.stability)}
                  description="Only needed if you want image generation in flows or generated posts."
                  eyebrow="Stability"
                  title="Connect Stability AI"
                  enabled={optionalSetup.stability}
                  enabledLabel="Set up Stability AI now"
                  onToggleEnabled={(enabled) =>
                    setOptionalSetup((current) => ({ ...current, stability: enabled }))
                  }
                >
                  <label className="field">
                    <span>Stability API key</span>
                    <input
                      className="input"
                      onChange={(event) => setForm((current) => ({ ...current, stabilityApiKey: event.target.value }))}
                      placeholder={settings?.credentials.stability ? "Leave empty to keep the saved Stability API key" : "Stability API key"}
                      type="password"
                      value={form.stabilityApiKey}
                    />
                  </label>
                </IntegrationCard>

                <IntegrationCard
                  configured={Boolean(settings?.credentials.langfuse)}
                  description="Use Langfuse only if you want traces and telemetry for runs."
                  eyebrow="Langfuse"
                  title="Connect Langfuse"
                  enabled={optionalSetup.langfuse}
                  enabledLabel="Set up Langfuse now"
                  onToggleEnabled={(enabled) =>
                    setOptionalSetup((current) => ({ ...current, langfuse: enabled }))
                  }
                >
                  <label className="field">
                    <span>Langfuse host</span>
                    <input
                      className="input"
                      onChange={(event) => setForm((current) => ({ ...current, langfuseHost: event.target.value }))}
                      placeholder="https://cloud.langfuse.com"
                      value={form.langfuseHost}
                    />
                  </label>
                  <div className="settings-inline-grid">
                    <label className="field">
                      <span>Langfuse public key</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, langfusePublicKey: event.target.value }))}
                        placeholder={settings?.credentials.langfuse ? "Leave empty to keep the saved public key" : "Langfuse public key"}
                        type="password"
                        value={form.langfusePublicKey}
                      />
                    </label>
                    <label className="field">
                      <span>Langfuse secret key</span>
                      <input
                        className="input"
                        onChange={(event) => setForm((current) => ({ ...current, langfuseSecretKey: event.target.value }))}
                        placeholder={settings?.credentials.langfuse ? "Leave empty to keep the saved secret key" : "Langfuse secret key"}
                        type="password"
                        value={form.langfuseSecretKey}
                      />
                    </label>
                  </div>
                </IntegrationCard>
              </div>
            </article>
          </div>

          <aside className="settings-tab-side">
            <article className="panel settings-side-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Embedding defaults</p>
                  <h2>Optional memory tuning</h2>
                </div>
              </div>
              <div className="settings-stack">
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
              </div>
            </article>
          </aside>
        </section>
      ) : null}

      {activeTab === "workspace" ? (
        <section className="settings-tab-layout">
          <div className="settings-tab-main">
            <article className="panel settings-side-panel">
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Workspace status</p>
                  <h2>Current setup</h2>
                </div>
              </div>
              <div className="status-cluster settings-status-cluster">
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
                  <div className={`status-tile ${configured ? "good" : "neutral"}`} key={name}>
                    <span>{name}</span>
                    <strong>{configured ? "Ready" : "Not set"}</strong>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>
      ) : null}

      <section className="panel settings-save-bar">
        <div className="settings-save-copy">
          <p className="eyebrow">Apply</p>
          <h2>Save only when the section you need is ready</h2>
          <p>Blank secret fields keep the current saved value. Save now to update Gemini, delivery, or optional integrations.</p>
        </div>
        <div className="button-row">
          <button className="button button-primary" disabled={isPending} onClick={save} type="button">
            Save settings
          </button>
          <button className="button button-secondary" disabled={isPending} onClick={() => void load()} type="button">
            Refresh model IDs
          </button>
        </div>
      </section>
    </section>
  );
}
