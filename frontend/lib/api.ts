const PUBLIC_BASE_PATH =
  process.env.NEXT_PUBLIC_BASE_PATH?.replace(/\/+$/, "") ?? "";

const RAW_API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  (PUBLIC_BASE_PATH ? `${PUBLIC_BASE_PATH}/api` : "http://127.0.0.1:8000/api");

function isUnsafePublicApiBaseUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return (
      url.hostname === "0.0.0.0" ||
      url.hostname === "127.0.0.1" ||
      url.hostname === "localhost"
    );
  } catch {
    return false;
  }
}

function getApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return RAW_API_BASE_URL;
  }

  if (RAW_API_BASE_URL.startsWith("/")) {
    return RAW_API_BASE_URL;
  }

  if (
    window.location.protocol === "https:" &&
    isUnsafePublicApiBaseUrl(RAW_API_BASE_URL)
  ) {
    return `${PUBLIC_BASE_PATH}/api`;
  }

  return RAW_API_BASE_URL;
}

export type Scout = {
  id: number;
  name: string;
  type: string;
  intent: string;
  schedule_cron: string | null;
  last_run: string | null;
  created_at: string | null;
  telegram_review: boolean;
  platforms: string[];
  delivery_platforms?: string[];
  verifier_platform?: string | null;
  config: Record<string, unknown>;
  nodes?: {
    scout: {
      id: number;
      name: string;
      type: string;
      schedule_cron: string | null;
      last_run: string | null;
      created_at: string | null;
      config: Record<string, unknown>;
    };
    scouts?: Array<{
      id: number;
      name: string;
      type: string;
      schedule_cron: string | null;
      last_run: string | null;
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
    agent: {
      id: number;
      name: string;
      intent: string;
      prompt_template: string | null;
      created_at: string | null;
      config: Record<string, unknown>;
    };
    verifier?: {
      id: number;
      name: string;
      platforms: string[];
      telegram_review: boolean;
      kind: "verifier" | "channel";
      created_at: string | null;
      config: Record<string, unknown>;
    } | null;
    channel: {
      id: number;
      name: string;
      platforms: string[];
      telegram_review: boolean;
      kind: "verifier" | "channel";
      created_at: string | null;
      config: Record<string, unknown>;
    };
    channels?: Array<{
      id: number;
      name: string;
      platforms: string[];
      telegram_review: boolean;
      kind: "verifier" | "channel";
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
  };
};

export type ScoutPayload = {
  name: string;
  scout_node_id?: number;
  scout_node_ids?: number[];
  scout_node_name?: string;
  agent_node_id?: number;
  agent_node_name?: string;
  channel_node_id?: number;
  channel_node_ids?: number[];
  channel_node_name?: string;
  verifier_enabled: boolean;
  verifier_node_id?: number;
  verifier_node_name?: string;
  verifier_platform: string;
  type: string;
  intent: string;
  schedule_cron: string | null;
  tools: string[];
  prompt_template: string;
  telegram_review: boolean;
  platforms: string[];
  image_generation: boolean;
  provider: string;
  model_id: string;
  temperature: number;
  flow_policy?: "as_it_comes" | "pool";
  query?: string;
  feeds?: string[];
  subreddits?: string[];
  reddit_sort?: string;
  newsletter_url?: string;
  substack_sort?: string;
  url?: string;
  date_filter?: string;
};

export type ScoutBuilderSnapshot = {
  gemini_models: string[];
  flow_generator: {
    enabled: boolean;
    provider: string;
    model_id: string;
    connection_verified: boolean;
    connection_verified_at?: string | null;
    missing_requirements: string[];
    settings_path: string;
  };
  flow_policies: Array<{
    id: "as_it_comes" | "pool";
    label: string;
    description: string;
  }>;
  type_defaults: Record<string, string[]>;
  tool_catalog: Array<{
    id: string;
    label: string;
    description: string;
    recommended_for: string[];
  }>;
  nodes: {
    scouts: Array<{
      id: number;
      name: string;
      type: string;
      schedule_cron: string | null;
      last_run: string | null;
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
    agents: Array<{
      id: number;
      name: string;
      intent: string;
      prompt_template: string | null;
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
    channels: Array<{
      id: number;
      name: string;
      platforms: string[];
      telegram_review: boolean;
      kind: "verifier" | "channel";
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
    verifiers: Array<{
      id: number;
      name: string;
      platforms: string[];
      telegram_review: boolean;
      kind: "verifier" | "channel";
      created_at: string | null;
      config: Record<string, unknown>;
    }>;
  };
};

export type ScoutNode = ScoutBuilderSnapshot["nodes"]["scouts"][number];

export type ScoutPreview = {
  items_found: number;
  items: Array<{
    title: string;
    url: string;
    summary: string | null;
    published_at: string | null;
  }>;
};

export type FlowSuggestion = {
  mode: "plan";
  assistant_message: string;
  name: string;
  summary: string;
  prompt: string;
  payload: ScoutPayload;
  nodes: {
    scouts: ScoutBuilderSnapshot["nodes"]["scouts"];
    agent: ScoutBuilderSnapshot["nodes"]["agents"][number];
    channels: ScoutBuilderSnapshot["nodes"]["channels"];
    verifier: ScoutBuilderSnapshot["nodes"]["verifiers"][number] | null;
  };
};

export type FlowClarification = {
  mode: "clarify";
  assistant_message: string;
  questions: string[];
};

export type PlannerMessage = {
  role: "user" | "assistant";
  content: string;
};

export type FlowPlannerResponse = FlowSuggestion | FlowClarification;

export type Post = {
  id: number;
  content: string;
  platform: string;
  status: string;
  scheduled_time: string | null;
  created_at: string | null;
  posted_at: string | null;
  external_id: string | null;
  scout_id: number | null;
  scout_name: string | null;
  role: "delivery" | "verification";
  delivery_targets: string[];
};

export type DashboardSnapshot = {
  system: {
    bot_running: boolean;
    updated_at: string;
  };
  stats: {
    scouts_total: number;
    scheduled_scouts: number;
    posts_total: number;
    posts_by_status: Record<string, number>;
    pending_reviews: number;
    rss_feeds: number;
    rss_entries: number;
    rss_processed_entries: number;
  };
  scouts: Scout[];
  recent_posts: Post[];
  pending_posts: Post[];
};

export type SettingsSnapshot = {
  config_file: string;
  env_file: string;
  storage: {
    env_readable: boolean;
    env_writable: boolean;
    config_writable: boolean;
  };
  ai: {
    default_provider: string;
    gemini_model: string;
    gemini_models: string[];
    gemini_connection_verified: boolean;
    gemini_connection_verified_at?: string | null;
  };
  embeddings: {
    enabled: boolean;
    model_name: string | null;
  };
  credentials: Record<string, boolean>;
  values: {
    telegram_chat_id: string;
    substack_subdomain: string;
    langfuse_host: string;
  };
};

export type GeminiSettingsTestResult = {
  message: string;
  settings: SettingsSnapshot;
};

export type SettingsValidationResult = {
  message: string;
  settings: SettingsSnapshot;
};

export type SavedSecretResult = {
  value: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    try {
      const parsed = JSON.parse(detail) as { detail?: string };
      throw new Error(parsed.detail || detail || `Request failed: ${response.status}`);
    } catch {
      throw new Error(detail || `Request failed: ${response.status}`);
    }
  }

  return response.json() as Promise<T>;
}

export function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  return request<DashboardSnapshot>("/dashboard");
}

export function getScoutBuilder(): Promise<ScoutBuilderSnapshot> {
  return request<ScoutBuilderSnapshot>("/scout-builder");
}

export function generateFlowSuggestion(
  prompt: string,
  messages?: PlannerMessage[],
): Promise<FlowPlannerResponse> {
  return request<FlowPlannerResponse>("/flow-suggestions", {
    method: "POST",
    body: JSON.stringify({ prompt, messages }),
  });
}

export function runScout(scoutId: number): Promise<unknown> {
  return request(`/scouts/${scoutId}/run`, { method: "POST" });
}

export function createScout(payload: ScoutPayload): Promise<Scout> {
  return request<Scout>("/scouts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createScoutNode(payload: ScoutPayload): Promise<ScoutNode> {
  return request<ScoutNode>("/scout-nodes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateScoutNode(nodeId: number, payload: ScoutPayload): Promise<ScoutNode> {
  return request<ScoutNode>(`/scout-nodes/${nodeId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function previewScoutNode(payload: ScoutPayload): Promise<ScoutPreview> {
  return request<ScoutPreview>("/scout-nodes/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateScout(scoutId: number, payload: ScoutPayload): Promise<Scout> {
  return request<Scout>(`/scouts/${scoutId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deleteScout(scoutId: number): Promise<{ deleted: boolean; name: string }> {
  return request<{ deleted: boolean; name: string }>(`/scouts/${scoutId}`, {
    method: "DELETE",
  });
}

export function approvePost(postId: number): Promise<unknown> {
  return request(`/posts/${postId}/approve`, { method: "POST" });
}

export function rejectPost(postId: number): Promise<unknown> {
  return request(`/posts/${postId}/reject`, { method: "POST" });
}

export function startSystem(): Promise<unknown> {
  return request("/system/start", { method: "POST" });
}

export function stopSystem(): Promise<unknown> {
  return request("/system/stop", { method: "POST" });
}

export function createQuickPost(payload: {
  content: string;
  platforms: string[];
  review_before_publish: boolean;
}): Promise<unknown> {
  return request("/posts/quick", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSettings(): Promise<SettingsSnapshot> {
  return request<SettingsSnapshot>("/settings");
}

export function saveSettings(payload: Record<string, unknown>): Promise<SettingsSnapshot> {
  return request<SettingsSnapshot>("/settings", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function saveAndTestGeminiSettings(
  payload: Record<string, unknown>,
): Promise<GeminiSettingsTestResult> {
  return request<GeminiSettingsTestResult>("/settings/gemini/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getSavedGeminiKey(): Promise<SavedSecretResult> {
  return request<SavedSecretResult>("/settings/gemini/secret");
}

export function saveAndTestTelegramSettings(
  payload: Record<string, unknown>,
): Promise<SettingsValidationResult> {
  return request<SettingsValidationResult>("/settings/telegram/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveAndTestXSettings(
  payload: Record<string, unknown>,
): Promise<SettingsValidationResult> {
  return request<SettingsValidationResult>("/settings/x/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function saveAndTestSubstackSettings(
  payload: Record<string, unknown>,
): Promise<SettingsValidationResult> {
  return request<SettingsValidationResult>("/settings/substack/test", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getLogs(lines = 100): Promise<{ app: string[]; bot: string[] }> {
  return request<{ app: string[]; bot: string[] }>(`/logs?lines=${lines}`);
}

export function getPosts(params?: { status?: string; limit?: number; q?: string }): Promise<Post[]> {
  const search = new URLSearchParams();
  if (params?.status) search.set("status", params.status);
  if (params?.limit) search.set("limit", String(params.limit));
  if (params?.q) search.set("q", params.q);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<Post[]>(`/posts${suffix}`);
}
