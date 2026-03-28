"use client";

import { useEffect, useMemo, useState, useTransition } from "react";

import {
  createScoutNode,
  createScout,
  deleteScout,
  type DashboardSnapshot,
  getScoutBuilder,
  type ScoutNode,
  type ScoutPreview,
  previewScoutNode,
  runScout,
  type ScoutBuilderSnapshot,
  type Scout,
  type ScoutPayload,
  updateScoutNode,
  updateScout,
} from "../lib/api";
import { formatTime, prettyLabel } from "../lib/present";
import {
  BranchIcon,
  ClockIcon,
  ComposeIcon,
  PlusIcon,
  RadarIcon,
  ReviewIcon,
} from "./icons";

type ScheduleMode = "manual" | "daily" | "weekdays" | "weekly" | "custom";
type FlowNodeKind = "scout" | "policy" | "agent" | "verifier" | "channel";

type ScheduleState = {
  mode: ScheduleMode;
  time: string;
  dayOfWeek: string;
  custom: string;
};

type GraphBlock = {
  id: string;
  kind: FlowNodeKind;
  title: string;
  subtitle: string;
  badges: string[];
  x: number;
  y: number;
  removable?: boolean;
  removeLabel?: string;
  removeAction?: () => void;
};

type GraphEdge = {
  id: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
};

function buildGraphPath(edge: GraphEdge) {
  if (Math.abs(edge.toY - edge.fromY) < 6) {
    return `M ${edge.fromX} ${edge.fromY} L ${edge.toX} ${edge.toY}`;
  }

  const horizontalDistance = Math.max(edge.toX - edge.fromX, 120);
  const bendX =
    edge.fromX +
    Math.min(Math.max(horizontalDistance * 0.48, 68), horizontalDistance - 44);
  const cornerRadius = Math.min(18, Math.abs(edge.toY - edge.fromY) / 2, 26);
  const verticalDirection = edge.toY > edge.fromY ? 1 : -1;

  return [
    `M ${edge.fromX} ${edge.fromY}`,
    `L ${bendX - cornerRadius} ${edge.fromY}`,
    `Q ${bendX} ${edge.fromY} ${bendX} ${edge.fromY + verticalDirection * cornerRadius}`,
    `L ${bendX} ${edge.toY - verticalDirection * cornerRadius}`,
    `Q ${bendX} ${edge.toY} ${bendX + cornerRadius} ${edge.toY}`,
    `L ${edge.toX} ${edge.toY}`,
  ].join(" ");
}

function isTimeValue(value: string) {
  return /^\d{2}:\d{2}$/.test(value);
}

function cronFromTime(time: string) {
  const [hour, minute] = time.split(":");
  return { hour, minute };
}

function scheduleStateFromCron(cron?: string | null): ScheduleState {
  if (!cron) {
    return { mode: "manual", time: "09:00", dayOfWeek: "1", custom: "" };
  }

  const parts = cron.trim().split(/\s+/);
  if (parts.length === 5) {
    const [minute, hour, day, month, dayOfWeek] = parts;
    if (
      /^\d{1,2}$/.test(minute) &&
      /^\d{1,2}$/.test(hour) &&
      day === "*" &&
      month === "*"
    ) {
      const time = `${hour.padStart(2, "0")}:${minute.padStart(2, "0")}`;
      if (dayOfWeek === "*") {
        return { mode: "daily", time, dayOfWeek: "1", custom: cron };
      }
      if (dayOfWeek === "1-5") {
        return { mode: "weekdays", time, dayOfWeek: "1", custom: cron };
      }
      if (/^[0-6]$/.test(dayOfWeek)) {
        return { mode: "weekly", time, dayOfWeek, custom: cron };
      }
    }
  }

  return { mode: "custom", time: "09:00", dayOfWeek: "1", custom: cron };
}

function cronFromScheduleState(state: ScheduleState) {
  if (state.mode === "manual") {
    return "";
  }
  if (state.mode === "custom") {
    return state.custom.trim();
  }

  const safeTime = isTimeValue(state.time) ? state.time : "09:00";
  const { hour, minute } = cronFromTime(safeTime);

  if (state.mode === "daily") {
    return `${minute} ${hour} * * *`;
  }
  if (state.mode === "weekdays") {
    return `${minute} ${hour} * * 1-5`;
  }
  return `${minute} ${hour} * * ${state.dayOfWeek}`;
}

function weekdayLabel(dayOfWeek: string) {
  return (
    {
      "0": "Sunday",
      "1": "Monday",
      "2": "Tuesday",
      "3": "Wednesday",
      "4": "Thursday",
      "5": "Friday",
      "6": "Saturday",
    }[dayOfWeek] ?? "Monday"
  );
}

function toggleValue(values: string[], nextValue: string, enabled: boolean) {
  if (enabled) {
    return [...new Set([...values, nextValue])];
  }
  return values.filter((value) => value !== nextValue);
}

function primaryScoutTool(type: string, builder: ScoutBuilderSnapshot | null) {
  return builder?.type_defaults[type]?.[0] ?? type;
}

function scoutToPayload(scout?: Scout | null): ScoutPayload {
  const config = (scout?.config ?? {}) as Record<string, unknown>;
  const scoutNodes = scout?.nodes?.scouts ?? (scout?.nodes?.scout ? [scout.nodes.scout] : []);
  const channelNodes = scout?.nodes?.channels ?? (scout?.nodes?.channel ? [scout.nodes.channel] : []);
  const verifierNode = scout?.nodes?.verifier ?? null;
  return {
    name: scout?.name ?? "",
    scout_node_id: scout?.nodes?.scout.id,
    scout_node_ids: scoutNodes.map((node) => node.id),
    scout_node_name: scout?.nodes?.scout.name ?? "",
    agent_node_id: scout?.nodes?.agent.id,
    agent_node_name: scout?.nodes?.agent.name ?? "",
    channel_node_id: scout?.nodes?.channel.id,
    channel_node_ids: channelNodes.map((node) => node.id),
    channel_node_name: scout?.nodes?.channel.name ?? "",
    verifier_enabled: Boolean(verifierNode),
    verifier_node_id: verifierNode?.id,
    verifier_node_name: verifierNode?.name ?? "",
    verifier_platform: verifierNode?.platforms?.[0] ?? "telegram",
    type: scout?.type ?? "rss",
    intent: scout?.intent ?? "scouting",
    schedule_cron: scout?.schedule_cron ?? "",
    tools: Array.isArray(config.tools) ? (config.tools as string[]) : [],
    prompt_template:
      (config.prompt_template as string) ??
      scout?.config?.prompt_template?.toString?.() ??
      "",
    telegram_review: scout?.telegram_review ?? false,
    platforms:
      scout?.delivery_platforms?.length
        ? scout.delivery_platforms
        : scout?.platforms?.length
          ? scout.platforms
          : ["telegram"],
    image_generation: Boolean(config.image_generation),
    provider:
      ((config.generation_config as { provider?: string } | undefined)?.provider ??
        "gemini"),
    model_id:
      ((config.generation_config as { model_id?: string } | undefined)?.model_id ??
        "gemini-2.5-flash"),
    temperature: Number(
      (config.generation_config as { temperature?: number } | undefined)
        ?.temperature ?? 0.7,
    ),
    flow_policy:
      ((config.flow_policy as "as_it_comes" | "pool" | undefined) ?? "pool"),
    query: (config.query as string) ?? "",
    feeds: Array.isArray(config.feeds) ? (config.feeds as string[]) : [""],
    subreddits: Array.isArray(config.subreddits)
      ? (config.subreddits as string[])
      : [""],
    reddit_sort: (config.reddit_sort as string) ?? "hot",
    newsletter_url: (config.newsletter_url as string) ?? "",
    substack_sort: (config.substack_sort as string) ?? "new",
    url: (config.url as string) ?? "",
    date_filter: (config.date_filter as string) ?? "",
  };
}

function applyScoutNodeToForm(
  current: ScoutPayload,
  node: ScoutNode,
  builder: ScoutBuilderSnapshot | null,
  options?: { preserveSelection?: boolean; addToSelection?: boolean },
): ScoutPayload {
  const config = node.config ?? {};
  const currentSelection = current.scout_node_ids ?? [];
  const nextSelection = options?.preserveSelection
    ? options?.addToSelection
      ? [...new Set([...currentSelection, node.id])]
      : currentSelection
    : [node.id];

  return {
    ...current,
    scout_node_id: node.id,
    scout_node_ids: nextSelection,
    scout_node_name: node.name,
    type: node.type,
    schedule_cron: node.schedule_cron,
    tools: [primaryScoutTool(node.type, builder)],
    query: typeof config.query === "string" ? config.query : "",
    feeds: Array.isArray(config.feeds) ? (config.feeds as string[]) : [""],
    subreddits: Array.isArray(config.subreddits) ? (config.subreddits as string[]) : [""],
    reddit_sort: typeof config.reddit_sort === "string" ? config.reddit_sort : "hot",
    newsletter_url: typeof config.newsletter_url === "string" ? config.newsletter_url : "",
    substack_sort: typeof config.substack_sort === "string" ? config.substack_sort : "new",
    url: typeof config.url === "string" ? config.url : "",
    date_filter: typeof config.date_filter === "string" ? config.date_filter : "",
  };
}

export function ScoutsPage({
  initialSnapshot = null,
}: {
  initialSnapshot?: DashboardSnapshot | null;
}) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot | null>(
    initialSnapshot,
  );
  const [selectedScoutId, setSelectedScoutId] = useState<
    number | "new" | null
  >(null);
  const [form, setForm] = useState<ScoutPayload>(scoutToPayload(null));
  const [builder, setBuilder] = useState<ScoutBuilderSnapshot | null>(null);
  const [activeNode, setActiveNode] = useState<FlowNodeKind>("scout");
  const [inspectorNode, setInspectorNode] = useState<FlowNodeKind | null>(null);
  const [selectedGraphBlockId, setSelectedGraphBlockId] = useState<string | null>(
    null,
  );
  const [draggingKind, setDraggingKind] = useState<"scout" | "agent" | "channel" | null>(null);
  const [draggedScoutNodeId, setDraggedScoutNodeId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [scoutPreview, setScoutPreview] = useState<ScoutPreview | null>(null);
  const [isPending, startTransition] = useTransition();

  const selectedScout = useMemo(
    () => snapshot?.scouts.find((scout) => scout.id === selectedScoutId) ?? null,
    [snapshot, selectedScoutId],
  );
  const scheduleState = useMemo(
    () => scheduleStateFromCron(form.schedule_cron),
    [form.schedule_cron],
  );
  const modelOptions = useMemo(() => {
    const available = builder?.gemini_models ?? [];
    return form.model_id && !available.includes(form.model_id)
      ? [form.model_id, ...available]
      : available;
  }, [builder, form.model_id]);
  const linkedScouts = useMemo(() => {
    const ids = form.scout_node_ids ?? [];
    return ids
      .map((id) => builder?.nodes.scouts.find((node) => node.id === id))
      .filter((node): node is NonNullable<typeof node> => Boolean(node));
  }, [builder, form.scout_node_ids]);
  const linkedChannels = useMemo(() => {
    const ids = form.channel_node_ids ?? [];
    return ids
      .map((id) => builder?.nodes.channels.find((node) => node.id === id))
      .filter((node): node is NonNullable<typeof node> => Boolean(node));
  }, [builder, form.channel_node_ids]);
  const linkedVerifier = useMemo(() => {
    if (!form.verifier_node_id) {
      return null;
    }
    return builder?.nodes.verifiers.find((node) => node.id === form.verifier_node_id) ?? null;
  }, [builder, form.verifier_node_id]);
  const isReusingScoutNode = Boolean(form.scout_node_id);
  const isReusingAgentNode = Boolean(form.agent_node_id);
  const isReusingChannelNode = Boolean(form.channel_node_id);
  const isReusingVerifierNode = Boolean(form.verifier_node_id);
  const flowScoutCount = Math.max(linkedScouts.length, form.scout_node_name ? 1 : 0);
  const hasMultipleScouts = linkedScouts.length > 1;
  const outputLabel =
    linkedChannels.length > 0
      ? linkedChannels.map((node) => node.name).join(", ")
      : form.platforms.length > 0
        ? form.platforms.map(prettyLabel).join(", ")
      : "No outputs";
  const verifierLabel = form.verifier_enabled
    ? linkedVerifier?.name || form.verifier_node_name || prettyLabel(form.verifier_platform)
    : "No verifier";

  const updateScheduleState = (changes: Partial<ScheduleState>) => {
    const nextState = { ...scheduleState, ...changes };
    setForm({ ...form, schedule_cron: cronFromScheduleState(nextState) });
  };

  const openInspectorFor = (kind: FlowNodeKind, blockId?: string) => {
    setActiveNode(kind);
    setInspectorNode(kind);
    setSelectedGraphBlockId(blockId ?? kind);
  };

  const closeInspector = () => {
    setInspectorNode(null);
    setSelectedGraphBlockId(null);
  };

  const startNewScoutNode = () => {
    openInspectorFor("scout", "new-scout");
    setScoutPreview(null);
    setForm((current) => ({
      ...current,
      scout_node_id: undefined,
      scout_node_name: `${current.name || "New"} Scout`,
      tools:
        current.tools.length > 0
          ? current.tools
          : [primaryScoutTool(current.type, builder)],
    }));
  };

  const startNewAgentNode = () => {
    openInspectorFor("agent", "agent");
    setForm((current) => ({
      ...current,
      agent_node_id: undefined,
      agent_node_name: current.agent_node_name || `${current.name || "New"} Agent`,
    }));
  };

  const startNewVerifierNode = () => {
    openInspectorFor("verifier", "verifier");
    setForm((current) => ({
      ...current,
      verifier_enabled: true,
      verifier_node_id: undefined,
      verifier_node_name: current.verifier_node_name || `${current.name || "New"} Verifier`,
      verifier_platform: current.verifier_platform || "telegram",
    }));
  };

  const startNewChannelNode = () => {
    openInspectorFor("channel", "new-channel");
    setForm((current) => ({
      ...current,
      channel_node_id: undefined,
      channel_node_name: `${current.name || "New"} Channel`,
    }));
  };

  const handleTypeChange = (nextType: string) => {
    setForm({
      ...form,
      type: nextType,
      tools: [primaryScoutTool(nextType, builder)],
    });
  };

  const handleScoutNodeSelect = (nodeId: string) => {
    if (!builder) return;
    if (nodeId === "") {
      setForm({
        ...form,
        scout_node_id: undefined,
        scout_node_name: "",
      });
      return;
    }
    const node = builder.nodes.scouts.find((entry) => entry.id === Number(nodeId));
    if (!node) return;
    setScoutPreview(null);
    setForm((current) =>
      applyScoutNodeToForm(current, node, builder, { preserveSelection: true }),
    );
  };

  const handleAgentNodeSelect = (nodeId: string) => {
    if (!builder) return;
    if (nodeId === "") {
      setForm({
        ...form,
        agent_node_id: undefined,
        agent_node_name: "",
      });
      return;
    }
    const node = builder.nodes.agents.find((entry) => entry.id === Number(nodeId));
    if (!node) return;
    const config = node.config ?? {};
    const generation = (config.generation_config ?? {}) as Record<string, unknown>;
    setForm({
      ...form,
      agent_node_id: node.id,
      agent_node_name: node.name,
      intent: node.intent,
      prompt_template: node.prompt_template ?? "",
      flow_policy:
        typeof config.flow_policy === "string"
          ? (config.flow_policy as "as_it_comes" | "pool")
          : "pool",
      provider: typeof generation.provider === "string" ? generation.provider : "gemini",
      model_id: typeof generation.model_id === "string" ? generation.model_id : "gemini-2.5-flash",
      temperature: typeof generation.temperature === "number" ? generation.temperature : 0.7,
      image_generation: Boolean(config.image_generation),
    });
  };

  const handleChannelNodeSelect = (nodeId: string) => {
    if (!builder) return;
    if (nodeId === "") {
      setForm({
        ...form,
        channel_node_id: undefined,
        channel_node_name: "",
      });
      return;
    }
    const node = builder.nodes.channels.find((entry) => entry.id === Number(nodeId));
    if (!node) return;
    setForm({
      ...form,
      channel_node_id: node.id,
      channel_node_ids: Array.from(new Set([...(form.channel_node_ids ?? []), node.id])),
      channel_node_name: node.name,
      platforms: node.platforms,
      telegram_review: false,
    });
  };

  const handleVerifierNodeSelect = (nodeId: string) => {
    if (!builder) return;
    if (nodeId === "") {
      setForm({
        ...form,
        verifier_enabled: false,
        verifier_node_id: undefined,
        verifier_node_name: "",
        verifier_platform: "telegram",
      });
      return;
    }
    const node = builder.nodes.verifiers.find((entry) => entry.id === Number(nodeId));
    if (!node) return;
    setForm({
      ...form,
      verifier_enabled: true,
      verifier_node_id: node.id,
      verifier_node_name: node.name,
      verifier_platform: node.platforms[0] ?? "telegram",
    });
  };

  const addChannelToCanvas = (channelNodeId: number) => {
    const node = builder?.nodes.channels.find((entry) => entry.id === channelNodeId);
    if (!node) return;
    setForm((current) => ({
      ...current,
      channel_node_id: node.id,
      channel_node_ids: Array.from(new Set([...(current.channel_node_ids ?? []), node.id])),
      channel_node_name: node.name,
      platforms: node.platforms,
      telegram_review: false,
    }));
  };

  const removeChannelFromCanvas = (channelNodeId: number) => {
    const remaining = (form.channel_node_ids ?? []).filter((id) => id !== channelNodeId);
    const nextPrimary = remaining[0];
    const nextPrimaryNode = builder?.nodes.channels.find((entry) => entry.id === nextPrimary);
    setForm((current) => ({
      ...current,
      channel_node_id: nextPrimary,
      channel_node_ids: remaining,
      channel_node_name: nextPrimaryNode?.name ?? current.channel_node_name,
      platforms: nextPrimaryNode?.platforms ?? current.platforms,
      telegram_review: false,
    }));
  };

  useEffect(() => {
    getScoutBuilder()
      .then(setBuilder)
      .catch((builderError) => {
        setError(
          builderError instanceof Error
            ? builderError.message
            : "Failed to load scout builder",
        );
      });
  }, []);

  useEffect(() => {
    if (initialSnapshot) {
      return;
    }

    refresh().catch((refreshError) => {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "Failed to load flows",
      );
    });
  }, [initialSnapshot]);

  useEffect(() => {
    if (selectedScoutId !== "new" || !builder || form.tools.length > 0) {
      return;
    }

    setForm((current) => ({
      ...current,
      tools: [primaryScoutTool(current.type, builder)],
    }));
  }, [builder, form.tools.length, form.type, selectedScoutId]);

  const addScoutToCanvas = (scoutNodeId: number) => {
    const node = builder?.nodes.scouts.find((entry) => entry.id === scoutNodeId);
    if (!node) return;
    setScoutPreview(null);
    setForm((current) =>
      applyScoutNodeToForm(current, node, builder, {
        preserveSelection: true,
        addToSelection: true,
      }),
    );
  };

  const removeScoutFromCanvas = (scoutNodeId: number) => {
    const remaining = (form.scout_node_ids ?? []).filter((id) => id !== scoutNodeId);
    const nextPrimary = remaining[0];
    const nextPrimaryNode = builder?.nodes.scouts.find((entry) => entry.id === nextPrimary);
    setScoutPreview(null);
    setForm((current) => ({
      ...current,
      scout_node_id: current.scout_node_id === scoutNodeId ? nextPrimary : current.scout_node_id,
      scout_node_ids: remaining,
      scout_node_name:
        current.scout_node_id === scoutNodeId
          ? nextPrimaryNode?.name ?? current.scout_node_name
          : current.scout_node_name,
      type:
        current.scout_node_id === scoutNodeId
          ? nextPrimaryNode?.type ?? current.type
          : current.type,
      schedule_cron:
        current.scout_node_id === scoutNodeId
          ? nextPrimaryNode?.schedule_cron ?? current.schedule_cron
          : current.schedule_cron,
      tools:
        current.scout_node_id === scoutNodeId && nextPrimaryNode
          ? [primaryScoutTool(nextPrimaryNode.type, builder)]
          : current.tools,
    }));
  };

  useEffect(() => {
    if (selectedScoutId === null) {
      return;
    }
    setScoutPreview(null);
    setActiveNode("scout");
    setInspectorNode(null);
    setSelectedGraphBlockId(null);
    if (selectedScoutId === "new") {
      setForm(scoutToPayload(null));
      return;
    }
    setForm(scoutToPayload(selectedScout));
  }, [selectedScout, selectedScoutId]);

  const refresh = async () => {
    const { getDashboardSnapshot } = await import("../lib/api");
    const data = await getDashboardSnapshot();
    setSnapshot(data);
    const nextBuilder = await getScoutBuilder();
    setBuilder(nextBuilder);
  };

  const saveScoutNode = () => {
    startTransition(() => {
      const action = form.scout_node_id
        ? updateScoutNode(form.scout_node_id, form)
        : createScoutNode(form);

      action
        .then((node) => {
          setError(null);
          setNotice(form.scout_node_id ? "Scout node updated" : "Scout node created");
          setScoutPreview(null);
          setBuilder((current) =>
            current
              ? {
                  ...current,
                  nodes: {
                    ...current.nodes,
                    scouts: [
                      node,
                      ...current.nodes.scouts.filter((entry) => entry.id !== node.id),
                    ],
                  },
                }
              : current,
          );
          setForm((current) =>
            applyScoutNodeToForm(current, node, builder, {
              preserveSelection: true,
              addToSelection: true,
            }),
          );
        })
        .catch((submitError) => {
          setError(
            submitError instanceof Error
              ? submitError.message
              : "Failed to save scout node",
          );
        });
    });
  };

  const testScoutNode = () => {
    startTransition(() => {
      previewScoutNode(form)
        .then((preview) => {
          setScoutPreview(preview);
          setError(null);
          setNotice(`Scout test completed with ${preview.items_found} items`);
        })
        .catch((previewError) => {
          setError(
            previewError instanceof Error
              ? previewError.message
              : "Failed to preview scout node",
          );
        });
    });
  };

  const submit = () => {
    if (selectedScoutId === null) {
      return;
    }
    if ((form.scout_node_ids ?? []).length === 0) {
      setError("Add at least one saved scout node to the flow before saving.");
      return;
    }
    if ((form.channel_node_ids ?? []).length === 0) {
      setError("Add at least one final output node before saving.");
      return;
    }
    startTransition(() => {
      const payload = {
        ...form,
        scout_node_id: form.scout_node_ids?.[0],
        channel_node_id: form.channel_node_ids?.[0],
      };
      const action =
        selectedScoutId === "new"
          ? createScout(payload)
          : updateScout(selectedScoutId, payload);

      action
        .then(async (scout) => {
          setNotice(selectedScoutId === "new" ? "Flow created" : "Flow updated");
          setError(null);
          await refresh();
          setSelectedScoutId(scout.id);
        })
        .catch((submitError) => {
          setError(
            submitError instanceof Error
              ? submitError.message
              : "Failed to save flow",
          );
        });
    });
  };

  const handleRunScout = (scoutId: number, scoutName: string) => {
    startTransition(() => {
      runScout(scoutId)
        .then(async () => {
          setNotice(`${scoutName} started`);
          await refresh();
        })
        .catch((actionError) => {
          setError(
            actionError instanceof Error
              ? actionError.message
              : "Flow run failed",
          );
        });
    });
  };

  const handleDelete = () => {
    if (selectedScoutId === null || selectedScoutId === "new") return;
    startTransition(() => {
      deleteScout(selectedScoutId)
        .then(async () => {
          setNotice("Flow deleted");
          setSelectedScoutId(null);
          await refresh();
        })
        .catch((deleteError) => {
          setError(
            deleteError instanceof Error
              ? deleteError.message
              : "Flow delete failed",
          );
        });
    });
  };

  if (!snapshot) {
    return (
      <section className="empty-page">
        <h2>Loading flows</h2>
        <p>{error ?? "Connecting to the local dashboard API."}</p>
      </section>
    );
  }

  const savedFlows = snapshot.scouts;
  const hasSavedFlows = savedFlows.length > 0;
  const canvasScoutNodes =
    linkedScouts.length > 0
      ? linkedScouts
      : [
          {
            id: 0,
            name: form.scout_node_name || form.name || "Listening layer",
            type: form.type,
            schedule_cron: form.schedule_cron,
            last_run: null,
            created_at: null,
            config: {},
          },
        ];
  const canvasChannelNodes =
    linkedChannels.length > 0
      ? linkedChannels
      : [
          {
            id: 0,
            name: form.channel_node_name || "Output channel",
            platforms: form.platforms,
            telegram_review: form.telegram_review,
            kind: "channel" as const,
            created_at: null,
            config: {},
          },
        ];

  const graphLayout = (() => {
    const blockWidth = 220;
    const blockHeight = 132;
    const scoutX = 56;
    const policyX = 356;
    const agentX = hasMultipleScouts ? 656 : 456;
    const verifierX = form.verifier_enabled ? agentX + 300 : agentX;
    const channelX = form.verifier_enabled ? verifierX + 300 : agentX + 300;
    const scoutGap = 170;
    const channelGap = 170;
    const baseY = 110;
    const scoutStartY = baseY;
    const scoutCenterY =
      scoutStartY + ((canvasScoutNodes.length - 1) * scoutGap) / 2;
    const policyY = scoutCenterY;
    const agentY = scoutCenterY;
    const verifierY = agentY;
    const channelStartY =
      agentY - ((canvasChannelNodes.length - 1) * channelGap) / 2;

    const blocks: GraphBlock[] = canvasScoutNodes.map((node, index) => ({
      id: `scout-${node.id || index}`,
      kind: "scout",
      title: node.name,
      subtitle: `${prettyLabel(primaryScoutTool(node.type, builder))} scout`,
      badges: [node.id ? "Reusable" : "New node", node.schedule_cron ? "Scheduled" : "Manual"],
      x: scoutX,
      y: scoutStartY + scoutGap * index,
      removable: Boolean(node.id && (form.scout_node_ids ?? []).length > 1),
      removeLabel: "Remove",
      removeAction: node.id ? () => removeScoutFromCanvas(node.id) : undefined,
    }));

    if (hasMultipleScouts) {
      blocks.push({
        id: "policy",
        kind: "policy",
        title:
          form.flow_policy === "as_it_comes"
            ? "As It Comes"
            : "Pool Aggregation",
        subtitle:
          form.flow_policy === "as_it_comes"
            ? "First usable scout signal continues the run."
            : "All scout signals pool before the agent runs.",
        badges: ["Routing", "Graph policy"],
        x: policyX,
        y: policyY,
      });
    }

    blocks.push({
      id: "agent",
      kind: "agent",
      title:
        form.agent_node_name ||
        (form.intent === "generation" ? "Draft creator" : "Signal analyst"),
      subtitle: `${form.model_id || "Gemini"} at ${form.temperature.toFixed(1)} creativity`,
      badges: [isReusingAgentNode ? "Reusable" : "New node", prettyLabel(form.intent)],
      x: agentX,
      y: agentY,
    });

    if (form.verifier_enabled) {
      blocks.push({
        id: "verifier",
        kind: "verifier",
        title: verifierLabel,
        subtitle: `Review in ${prettyLabel(form.verifier_platform)} before delivery`,
        badges: [isReusingVerifierNode ? "Reusable" : "New node", "Optional gate"],
        x: verifierX,
        y: verifierY,
      });
    }

    canvasChannelNodes.forEach((node, index) => {
      blocks.push({
        id: `channel-${node.id || index}`,
        kind: "channel",
        title: node.name,
        subtitle: node.platforms.map(prettyLabel).join(", ") || "No outputs selected",
        badges: [node.id ? "Reusable" : "New node", "Final delivery"],
        x: channelX,
        y: channelStartY + channelGap * index,
        removable: Boolean(node.id && (form.channel_node_ids ?? []).length > 1),
        removeLabel: "Remove",
        removeAction: node.id ? () => removeChannelFromCanvas(node.id) : undefined,
      });
    });

    const portRadius = 6;
    const centers = new Map(
      blocks.map((block) => [
        block.id,
        {
          outX: block.x + blockWidth + portRadius,
          inX: block.x - portRadius,
          y: block.y + blockHeight / 2,
        },
      ]),
    );

    const edges: GraphEdge[] = [];
    const targetForScouts = hasMultipleScouts ? "policy" : "agent";
    blocks
      .filter((block) => block.kind === "scout")
      .forEach((block) => {
        const from = centers.get(block.id);
        const to = centers.get(targetForScouts);
        if (from && to) {
          edges.push({
            id: `${block.id}-${targetForScouts}`,
            fromX: from.outX,
            fromY: from.y,
            toX: to.inX,
            toY: to.y,
          });
        }
      });

    if (hasMultipleScouts) {
      const from = centers.get("policy");
      const to = centers.get("agent");
      if (from && to) {
        edges.push({
          id: "policy-agent",
          fromX: from.outX,
          fromY: from.y,
          toX: to.inX,
          toY: to.y,
        });
      }
    }

    if (form.verifier_enabled) {
      const from = centers.get("agent");
      const to = centers.get("verifier");
      if (from && to) {
        edges.push({
          id: "agent-verifier",
          fromX: from.outX,
          fromY: from.y,
          toX: to.inX,
          toY: to.y,
        });
      }
    }

    blocks
      .filter((block) => block.kind === "channel")
      .forEach((block) => {
        const from = centers.get(form.verifier_enabled ? "verifier" : "agent");
        const to = centers.get(block.id);
        if (from && to) {
          edges.push({
            id: `${form.verifier_enabled ? "verifier" : "agent"}-${block.id}`,
            fromX: from.outX,
            fromY: from.y,
            toX: to.inX,
            toY: to.y,
          });
        }
      });

    const width = Math.max(channelX + blockWidth + 80, 1100);
    const maxNodeY = Math.max(...blocks.map((block) => block.y), baseY);
    const height = Math.max(maxNodeY + blockHeight + 120, 520);

    return { blocks, edges, width, height, blockWidth, blockHeight };
  })();

  return (
    <section className="page-stack workflow-studio-page">
      {notice ? <p className="feedback-banner success">{notice}</p> : null}
      {error ? <p className="feedback-banner error">{error}</p> : null}

      <section
        className={`workflow-studio ${inspectorNode ? "workflow-studio-with-inspector" : "workflow-studio-board-only"}`}
      >
        <section className={`panel studio-board ${selectedScoutId !== null ? "studio-board-active" : ""}`}>
          <div className={`studio-browser-bar ${selectedScoutId !== null ? "compact" : ""}`}>
            <div className="studio-browser-copy">
              <p className="eyebrow">Flow Browser</p>
              <strong>
                {hasSavedFlows
                  ? "Pick a workflow or start a fresh one."
                  : "Start your first workflow."}
              </strong>
            </div>
            <div className="studio-browser-meta">
              {hasSavedFlows
                ? `${savedFlows.length} saved ${savedFlows.length === 1 ? "flow" : "flows"}`
                : "No flows yet"}
            </div>
            <div className="flow-browser-tray">
              <button
                className={`flow-browser-pill flow-browser-create ${selectedScoutId === "new" ? "active" : ""}`}
                onClick={() => setSelectedScoutId("new")}
                type="button"
              >
                <PlusIcon className="micro-icon" />
                <div>
                  <strong>New flow</strong>
                  <span>Fresh workflow graph</span>
                </div>
              </button>
              {savedFlows.map((scout) => (
                <button
                  className={`flow-browser-pill ${selectedScoutId === scout.id ? "active" : ""}`}
                  key={scout.id}
                  onClick={() => setSelectedScoutId(scout.id)}
                  type="button"
                >
                  <strong>{scout.name}</strong>
                  <span>{formatTime(scout.last_run)}</span>
                </button>
              ))}
            </div>
          </div>

          {selectedScoutId === null ? (
            <div className="studio-empty-shell">
              <div className="studio-empty-orb studio-empty-orb-a" />
              <div className="studio-empty-orb studio-empty-orb-b" />
              <section className="studio-empty-hero">
                <p className="eyebrow">Workflow Studio</p>
                <h3>Build a flow from signal to delivery.</h3>
                <p>
                  Create scouts that listen, route them through one agent, and
                  deliver approved output into one or more channels.
                </p>
                <div className="studio-empty-highlights">
                  <span>Reusable nodes</span>
                  <span>Live canvas</span>
                  <span>Multi-output delivery</span>
                </div>
                <div className="button-row">
                  <button
                    className="button button-primary"
                    onClick={() => setSelectedScoutId("new")}
                    type="button"
                  >
                    Create flow
                  </button>
                  {hasSavedFlows ? (
                    <button
                      className="button button-secondary"
                      onClick={() => setSelectedScoutId(savedFlows[0]?.id ?? null)}
                      type="button"
                    >
                      Open latest
                    </button>
                  ) : null}
                </div>
                <div className="studio-empty-steps">
                  <div className="studio-step-card">
                    <span>1</span>
                    <strong>Listen</strong>
                    <p>Use scout nodes to watch RSS, Reddit, Search, Substack, or the browser.</p>
                  </div>
                  <div className="studio-step-card">
                    <span>2</span>
                    <strong>Shape</strong>
                    <p>Use one agent to choose what matters and turn it into structured output.</p>
                  </div>
                  <div className="studio-step-card">
                    <span>3</span>
                    <strong>Deliver</strong>
                    <p>Route drafts through review and fan them out to your final channels.</p>
                  </div>
                </div>
              </section>

              <aside className="studio-empty-preview">
                <div className="studio-preview-card">
                  <div className="studio-preview-stage">
                    <div className="preview-connection preview-connection-left" />
                    <div className="preview-connection preview-connection-right" />
                    <div className="preview-connection preview-connection-bottom" />

                    <div className="preview-node preview-node-scout">
                      <RadarIcon className="shortcut-icon" />
                      <span>Scout</span>
                      <strong>Signal feed</strong>
                    </div>

                    <div className="preview-node preview-node-agent">
                      <ComposeIcon className="shortcut-icon" />
                      <span>Agent</span>
                      <strong>Signal analyst</strong>
                    </div>

                    <div className="preview-node preview-node-output">
                      <ReviewIcon className="shortcut-icon" />
                      <span>Output</span>
                      <strong>Telegram, X</strong>
                    </div>

                    <div className="preview-node preview-node-review">
                      <BranchIcon className="shortcut-icon" />
                      <span>Policy</span>
                      <strong>Pooled context</strong>
                    </div>

                    <div className="preview-signal-chip preview-signal-chip-a">RSS</div>
                    <div className="preview-signal-chip preview-signal-chip-b">Reddit</div>
                    <div className="preview-signal-chip preview-signal-chip-c">Substack</div>
                  </div>
                  <div className="studio-preview-caption">
                    <strong>One visual graph, reusable everywhere.</strong>
                    <p>
                      Connect scouts, shared agents, policy logic, and outputs in one interactive workspace.
                    </p>
                  </div>
                </div>
              </aside>
            </div>
          ) : (
            <>
              <div className="studio-topbar compact">
                <div>
                  <p className="eyebrow">Workflow Studio</p>
                  <input
                    className="studio-flow-name"
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="Untitled flow"
                    value={form.name}
                  />
                  <p className="board-subtle">
                    {flowScoutCount} scout nodes, {form.verifier_enabled ? "verification enabled" : "no verifier"},{" "}
                    {linkedChannels.length || 1} final output nodes
                  </p>
                </div>
                <div className="button-row studio-actions">
                  <button
                    className="button button-secondary"
                    onClick={() => setSelectedScoutId("new")}
                    type="button"
                  >
                    <ComposeIcon className="button-icon" />
                    New flow
                  </button>
                  {selectedScoutId !== "new" ? (
                    <button
                      className="button button-secondary"
                      disabled={isPending}
                      onClick={() => handleRunScout(selectedScoutId, form.name)}
                      type="button"
                    >
                      <RadarIcon className="button-icon" />
                      Run
                    </button>
                  ) : null}
                  {selectedScoutId !== "new" ? (
                    <button
                      className="button button-secondary"
                      disabled={isPending}
                      onClick={handleDelete}
                      type="button"
                    >
                      Delete
                    </button>
                  ) : null}
                  <button
                    className="button button-primary"
                    disabled={isPending}
                    onClick={submit}
                    type="button"
                  >
                    {selectedScoutId === "new" ? "Create flow" : "Save changes"}
                  </button>
                </div>
              </div>

              <div className="flow-overview-strip compact">
                <div className="flow-overview-card">
                  <span className="flow-overview-label">Sources</span>
                  <strong>{flowScoutCount} scout node{flowScoutCount === 1 ? "" : "s"}</strong>
                  <p>{hasMultipleScouts ? "Multiple inputs feed one shared agent." : "Single input flows directly to the agent."}</p>
                </div>
                <div className="flow-overview-card">
                  <span className="flow-overview-label">Verifier</span>
                  <strong>{form.verifier_enabled ? prettyLabel(form.verifier_platform) : "Skipped"}</strong>
                  <p>{form.verifier_enabled ? `${verifierLabel} reviews drafts before final delivery.` : "Drafts go straight to final output approvals."}</p>
                </div>
                <div className="flow-overview-card">
                  <span className="flow-overview-label">Delivery</span>
                  <strong>{linkedChannels.length || form.platforms.length || 1} target{(linkedChannels.length || form.platforms.length || 1) === 1 ? "" : "s"}</strong>
                  <p>{outputLabel}</p>
                </div>
              </div>

              <div className="board-stage">
                <div className="board-header">
                  <div>
                    <p className="eyebrow">Pipeline</p>
                    <strong>Build the graph from scouting to delivery</strong>
                  </div>
                  <div className="canvas-palette">
                    <button className="palette-chip" onClick={startNewScoutNode} type="button">
                      Add scout
                    </button>
                    <button className="palette-chip" onClick={startNewAgentNode} type="button">
                      Add agent
                    </button>
                    <button className="palette-chip" onClick={startNewVerifierNode} type="button">
                      Add verifier
                    </button>
                    <button className="palette-chip" onClick={startNewChannelNode} type="button">
                      Add output
                    </button>
                  </div>
                </div>

                <div className="flow-canvas studio-canvas-surface">
                  <div className="graph-canvas-shell">
                    <div
                      className="graph-canvas"
                      onDragOver={(e) => {
                        if (draggingKind === "scout") e.preventDefault();
                      }}
                      onDrop={(e) => {
                        e.preventDefault();
                        if (draggingKind === "scout" && draggedScoutNodeId) {
                          addScoutToCanvas(draggedScoutNodeId);
                        }
                        setDraggedScoutNodeId(null);
                        setDraggingKind(null);
                      }}
                      style={{
                        minWidth: `${graphLayout.width}px`,
                        height: `${graphLayout.height}px`,
                      }}
                    >
                      <svg
                        aria-hidden="true"
                        className="graph-edges"
                        height={graphLayout.height}
                        viewBox={`0 0 ${graphLayout.width} ${graphLayout.height}`}
                        width={graphLayout.width}
                      >
                        {graphLayout.edges.map((edge) => {
                          return (
                            <path
                              className="graph-edge-path"
                              d={buildGraphPath(edge)}
                              key={edge.id}
                            />
                          );
                        })}
                      </svg>

                      {graphLayout.blocks.map((block, index) => (
                        <button
                          className={`graph-block ${selectedGraphBlockId === block.id ? "active" : ""}`}
                          key={block.id}
                          onClick={() => {
                            openInspectorFor(block.kind, block.id);
                            if (block.kind === "scout" && block.id.startsWith("scout-")) {
                              const nodeId = Number(block.id.replace("scout-", ""));
                              if (nodeId) handleScoutNodeSelect(String(nodeId));
                            }
                            if (block.kind === "channel" && block.id.startsWith("channel-")) {
                              const nodeId = Number(block.id.replace("channel-", ""));
                              if (nodeId) handleChannelNodeSelect(String(nodeId));
                            }
                          }}
                          style={{ left: `${block.x}px`, top: `${block.y}px` }}
                          type="button"
                        >
                          <span className="graph-port graph-port-in" />
                          <span className="graph-port graph-port-out" />
                          <span className="canvas-node-badge">{index + 1}</span>
                          <div className="flow-node-head">
                            {block.kind === "scout" ? (
                              <RadarIcon className="shortcut-icon" />
                            ) : block.kind === "policy" ? (
                              <BranchIcon className="shortcut-icon" />
                            ) : block.kind === "agent" ? (
                              <ComposeIcon className="shortcut-icon" />
                            ) : (
                              <ReviewIcon className="shortcut-icon" />
                            )}
                            <div>
                              <p className="eyebrow">{prettyLabel(block.kind)}</p>
                              <strong>{block.title}</strong>
                            </div>
                          </div>
                          <p>{block.subtitle}</p>
                          <div className="node-meta-row">
                            {block.badges.map((badge) => (
                              <span
                                className="node-meta-pill subtle"
                                key={`${block.id}-${badge}`}
                              >
                                {badge}
                              </span>
                            ))}
                          </div>
                          {block.removable && block.removeAction ? (
                            <span
                              className="node-remove"
                              onClick={(e) => {
                                e.stopPropagation();
                                block.removeAction?.();
                              }}
                            >
                              {block.removeLabel}
                            </span>
                          ) : null}
                        </button>
                      ))}

                      <div className="graph-add-rail">
                        <button
                          className="canvas-add-node"
                          onClick={startNewScoutNode}
                          type="button"
                        >
                          <PlusIcon className="micro-icon" />
                          Add scout
                        </button>
                        <button
                          className="canvas-add-node"
                          onClick={startNewAgentNode}
                          type="button"
                        >
                          <PlusIcon className="micro-icon" />
                          Add agent
                        </button>
                        <button
                          className="canvas-add-node"
                          onClick={startNewVerifierNode}
                          type="button"
                        >
                          <PlusIcon className="micro-icon" />
                          Add verifier
                        </button>
                        <button
                          className="canvas-add-node"
                          onClick={startNewChannelNode}
                          type="button"
                        >
                          <PlusIcon className="micro-icon" />
                          Add output
                        </button>
                      </div>
                    </div>
                  </div>

                  <div className="board-footer">
                    <div className="flow-canvas-note">
                      <strong>Execution path</strong>
                      <p>
                        {hasMultipleScouts
                          ? `Scout sources pass through ${form.flow_policy === "as_it_comes" ? "an as-it-comes policy" : "a pooled aggregation policy"} before the agent transforms the result${form.verifier_enabled ? ` and sends it to ${verifierLabel} for verification` : ""}.`
                          : `Scout sources feed the agent directly${form.verifier_enabled ? `, then ${verifierLabel} reviews the draft` : ""}, before final delivery.`}
                      </p>
                    </div>
                    <div className="flow-canvas-note">
                      <strong>Review and delivery</strong>
                      <p>
                        {form.verifier_enabled ? `${verifierLabel} -> ` : ""}
                        {outputLabel}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </section>

        {inspectorNode ? (
          <aside className="panel studio-inspector">
            <>
              <div className="panel-header">
                <div>
                  <p className="eyebrow">Inspector</p>
                  <h2>
                      {inspectorNode === "scout"
                        ? "Scout node"
                        : inspectorNode === "policy"
                          ? "Policy node"
                        : inspectorNode === "agent"
                          ? "Agent node"
                          : inspectorNode === "verifier"
                            ? "Verifier node"
                          : "Channel node"}
                  </h2>
                </div>
                <div className="button-row compact">
                  <div className="topbar-chip">
                  {inspectorNode === "scout"
                    ? "Listening"
                    : inspectorNode === "policy"
                      ? "Route logic"
                    : inspectorNode === "agent"
                      ? "Transform"
                      : inspectorNode === "verifier"
                        ? "Review gate"
                      : "Deliver"}
                  </div>
                  <button
                    className="button button-secondary"
                    onClick={closeInspector}
                    type="button"
                  >
                    Close
                  </button>
                </div>
              </div>

              {inspectorNode === "scout" ? (
                  <article className="canvas-card inspector-card">
                  <div className="canvas-card-head">
                    <RadarIcon className="shortcut-icon" />
                    <div>
                      <p className="eyebrow">Scout</p>
                      <h3>Listen for signals</h3>
                    </div>
                  </div>
                  <p className="canvas-card-copy">
                    Set up the selected listening node here.
                  </p>

                  <div className="settings-stack">
                    <label className="field">
                      <span>Reuse scout node</span>
                      <select
                        className="input"
                        onChange={(e) => handleScoutNodeSelect(e.target.value)}
                        value={form.scout_node_id ?? ""}
                      >
                        <option value="">Create a unique scout node</option>
                        {(builder?.nodes.scouts ?? []).map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Scout node name</span>
                      <input
                        className="input"
                        onChange={(e) =>
                          setForm({ ...form, scout_node_name: e.target.value })
                        }
                        value={form.scout_node_name ?? ""}
                      />
                    </label>
                    <label className="field">
                      <span>Scout tool</span>
                      <select
                        className="input"
                        onChange={(e) => handleTypeChange(e.target.value)}
                        value={form.type}
                      >
                        <option value="rss">RSS</option>
                        <option value="reddit">Reddit</option>
                        <option value="search">Search</option>
                        <option value="substack">Substack</option>
                        <option value="browser">Browser</option>
                        <option value="arxiv">Arxiv</option>
                      </select>
                    </label>
                    <label className="field">
                      <span>Scout schedule</span>
                      <div className="schedule-card">
                        <div className="schedule-head">
                          <div className="schedule-clock">
                            <ClockIcon className="schedule-clock-icon" />
                          </div>
                          <div>
                            <strong>
                              {scheduleState.mode === "manual"
                                ? "Run manually"
                                : "Automatic schedule"}
                            </strong>
                            <p>
                              {scheduleState.mode === "manual"
                                ? "This scout only runs when you trigger it."
                                : scheduleState.mode === "daily"
                                  ? `Every day at ${scheduleState.time}`
                                  : scheduleState.mode === "weekdays"
                                    ? `Weekdays at ${scheduleState.time}`
                                    : scheduleState.mode === "weekly"
                                      ? `${weekdayLabel(scheduleState.dayOfWeek)} at ${scheduleState.time}`
                                      : "Custom cron expression"}
                            </p>
                          </div>
                        </div>

                        <div
                          className="schedule-options"
                          role="tablist"
                          aria-label="Scout schedule"
                        >
                          {[
                            { value: "manual", label: "Manual" },
                            { value: "daily", label: "Daily" },
                            { value: "weekdays", label: "Weekdays" },
                            { value: "weekly", label: "Weekly" },
                            { value: "custom", label: "Custom" },
                          ].map((option) => (
                            <button
                              key={option.value}
                              className={`schedule-chip ${scheduleState.mode === option.value ? "active" : ""}`}
                              onClick={() =>
                                updateScheduleState({
                                  mode: option.value as ScheduleMode,
                                })
                              }
                              type="button"
                            >
                              {option.label}
                            </button>
                          ))}
                        </div>

                        {scheduleState.mode !== "manual" &&
                        scheduleState.mode !== "custom" ? (
                          <div className="schedule-detail-grid">
                            <label className="field">
                              <span>Time</span>
                              <input
                                className="input"
                                onChange={(e) =>
                                  updateScheduleState({ time: e.target.value })
                                }
                                type="time"
                                value={scheduleState.time}
                              />
                            </label>

                            {scheduleState.mode === "weekly" ? (
                              <label className="field">
                                <span>Day</span>
                                <select
                                  className="input"
                                  onChange={(e) =>
                                    updateScheduleState({
                                      dayOfWeek: e.target.value,
                                    })
                                  }
                                  value={scheduleState.dayOfWeek}
                                >
                                  <option value="1">Monday</option>
                                  <option value="2">Tuesday</option>
                                  <option value="3">Wednesday</option>
                                  <option value="4">Thursday</option>
                                  <option value="5">Friday</option>
                                  <option value="6">Saturday</option>
                                  <option value="0">Sunday</option>
                                </select>
                              </label>
                            ) : null}
                          </div>
                        ) : null}

                        {scheduleState.mode === "custom" ? (
                          <label className="field">
                            <span>Cron expression</span>
                            <input
                              className="input"
                              onChange={(e) =>
                                updateScheduleState({ custom: e.target.value })
                              }
                              placeholder="0 9 * * *"
                              value={scheduleState.custom}
                            />
                          </label>
                        ) : null}
                      </div>
                    </label>

                    {(form.type === "search" || form.type === "arxiv") && (
                      <label className="field">
                        <span>Focus topic</span>
                        <input
                          className="input"
                          onChange={(e) =>
                            setForm({ ...form, query: e.target.value })
                          }
                          value={form.query ?? ""}
                        />
                      </label>
                    )}
                    {form.type === "rss" && (
                      <label className="field">
                        <span>Feeds</span>
                        <textarea
                          className="input textarea compact"
                          onChange={(e) =>
                            setForm({
                              ...form,
                              feeds: e.target.value.split("\n"),
                            })
                          }
                          placeholder="One RSS URL per line"
                          rows={6}
                          value={(form.feeds ?? []).join("\n")}
                        />
                      </label>
                    )}
                    {form.type === "reddit" && (
                      <>
                        <label className="field">
                          <span>Subreddits</span>
                          <textarea
                            className="input textarea compact"
                            onChange={(e) =>
                              setForm({
                                ...form,
                                subreddits: e.target.value.split("\n"),
                              })
                            }
                            placeholder="One subreddit per line"
                            rows={5}
                            value={(form.subreddits ?? []).join("\n")}
                          />
                        </label>
                        <label className="field">
                          <span>Scout sort</span>
                          <select
                            className="input"
                            onChange={(e) =>
                              setForm({
                                ...form,
                                reddit_sort: e.target.value,
                              })
                            }
                            value={form.reddit_sort ?? "hot"}
                          >
                            <option value="hot">Hot</option>
                            <option value="new">New</option>
                            <option value="top">Top</option>
                            <option value="rising">Rising</option>
                          </select>
                        </label>
                      </>
                    )}
                    {form.type === "substack" && (
                      <label className="field">
                        <span>Newsletter URL</span>
                        <input
                          className="input"
                          onChange={(e) =>
                            setForm({
                              ...form,
                              newsletter_url: e.target.value,
                            })
                          }
                          value={form.newsletter_url ?? ""}
                        />
                      </label>
                    )}
                    {form.type === "browser" && (
                      <label className="field">
                        <span>Target URL</span>
                        <input
                          className="input"
                          onChange={(e) =>
                            setForm({ ...form, url: e.target.value })
                          }
                          value={form.url ?? ""}
                        />
                      </label>
                    )}

                    <div className="button-row">
                      <button
                        className="button button-secondary"
                        disabled={isPending}
                        onClick={testScoutNode}
                        type="button"
                      >
                        Test scout
                      </button>
                      <button
                        className="button button-primary"
                        disabled={isPending}
                        onClick={saveScoutNode}
                        type="button"
                      >
                        {form.scout_node_id ? "Save scout" : "Create scout"}
                      </button>
                    </div>

                    {scoutPreview ? (
                      <div className="helper-note preview-note">
                        <span>Scout preview</span>
                        <p>
                          Found {scoutPreview.items_found} item
                          {scoutPreview.items_found === 1 ? "" : "s"}.
                        </p>
                        {scoutPreview.items.map((item) => (
                          <div className="preview-item" key={item.url}>
                            <strong>{item.title}</strong>
                            <p>{item.summary ?? item.url}</p>
                          </div>
                        ))}
                      </div>
                    ) : null}

                    <div className="field helper-note">
                      <span>Pattern</span>
                      <p>
                        One scout equals one listening tool. Save scout nodes
                        independently, then add as many as you need to the flow.
                      </p>
                    </div>
                  </div>
                  </article>
              ) : null}

              {inspectorNode === "agent" ? (
                  <article className="canvas-card inspector-card">
                  <div className="canvas-card-head">
                    <ComposeIcon className="shortcut-icon" />
                    <div>
                      <p className="eyebrow">Agent</p>
                      <h3>Transform what the scout finds</h3>
                    </div>
                  </div>
                  <p className="canvas-card-copy">
                    Tell the agent how to interpret incoming content, what shape
                    to produce, and which model to use.
                  </p>

                  <div className="settings-stack">
                    <label className="field">
                      <span>Reuse agent node</span>
                      <select
                        className="input"
                        onChange={(e) => handleAgentNodeSelect(e.target.value)}
                        value={form.agent_node_id ?? ""}
                      >
                        <option value="">Create a unique agent node</option>
                        {(builder?.nodes.agents ?? []).map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Agent node name</span>
                      <input
                        className="input"
                        onChange={(e) =>
                          setForm({ ...form, agent_node_name: e.target.value })
                        }
                        value={form.agent_node_name ?? ""}
                      />
                    </label>
                    <label className="field">
                      <span>Agent mode</span>
                      <select
                        className="input"
                        onChange={(e) =>
                          setForm({ ...form, intent: e.target.value })
                        }
                        value={form.intent}
                      >
                        <option value="scouting">Briefing or digest</option>
                        <option value="generation">Publish-ready draft</option>
                      </select>
                    </label>

                    <label className="field">
                      <span>Agent instructions</span>
                      <textarea
                        className="input textarea compact"
                        onChange={(e) =>
                          setForm({
                            ...form,
                            prompt_template: e.target.value,
                          })
                        }
                        rows={6}
                        value={form.prompt_template ?? ""}
                      />
                    </label>
                    <label className="field">
                      <span>Gemini model</span>
                      <select
                        className="input"
                        onChange={(e) =>
                          setForm({ ...form, model_id: e.target.value })
                        }
                        value={form.model_id}
                      >
                        {modelOptions.map((modelId) => (
                          <option key={modelId} value={modelId}>
                            {modelId}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Creativity</span>
                      <input
                        className="input"
                        max="1"
                        min="0"
                        onChange={(e) =>
                          setForm({
                            ...form,
                            temperature: Number(e.target.value),
                          })
                        }
                        step="0.1"
                        type="number"
                        value={form.temperature}
                      />
                    </label>
                    <label className="toggle-row">
                      <input
                        checked={form.image_generation}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            image_generation: e.target.checked,
                          })
                        }
                        type="checkbox"
                      />
                      <span>Image generation</span>
                    </label>
                    <div className="field helper-note">
                      <span>Agent role</span>
                      <p>
                        Agents do not fetch sources. They receive context from
                        scout nodes, decide what matters, and turn it into a
                        briefing or a publishable draft.
                      </p>
                    </div>
                  </div>
                  </article>
              ) : null}

              {inspectorNode === "policy" ? (
                  <article className="canvas-card inspector-card">
                    <div className="canvas-card-head">
                      <BranchIcon className="shortcut-icon" />
                      <div>
                        <p className="eyebrow">Policy</p>
                        <h3>Decide how scout results reach the agent</h3>
                      </div>
                    </div>
                    <p className="canvas-card-copy">
                      When more than one scout feeds the same agent, choose
                      whether the first usable result should trigger the agent
                      immediately or whether all scout context should be pooled.
                    </p>

                    <div className="tool-picker">
                      {(builder?.flow_policies ?? []).map((policy) => {
                        const active = form.flow_policy === policy.id;
                        return (
                          <button
                            className={`tool-chip policy-card ${active ? "active" : ""}`}
                            key={policy.id}
                            onClick={() =>
                              setForm({ ...form, flow_policy: policy.id })
                            }
                            type="button"
                          >
                            <div>
                              <strong>{policy.label}</strong>
                              <p>{policy.description}</p>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </article>
              ) : null}

              {inspectorNode === "verifier" ? (
                  <article className="canvas-card inspector-card">
                  <div className="canvas-card-head">
                    <ReviewIcon className="shortcut-icon" />
                    <div>
                      <p className="eyebrow">Verifier</p>
                      <h3>Add an optional approval step</h3>
                    </div>
                  </div>
                  <p className="canvas-card-copy">
                    A verifier sits between the agent and final channels. Use it when one place
                    should approve drafts before they fan out to destinations.
                  </p>

                  <div className="settings-stack">
                    <label className="toggle-row">
                      <input
                        checked={form.verifier_enabled}
                        onChange={(e) =>
                          setForm({
                            ...form,
                            verifier_enabled: e.target.checked,
                            verifier_node_id: e.target.checked ? form.verifier_node_id : undefined,
                            verifier_node_name: e.target.checked ? form.verifier_node_name : "",
                            verifier_platform: e.target.checked ? form.verifier_platform : "telegram",
                          })
                        }
                        type="checkbox"
                      />
                      <span>Enable verifier stage</span>
                    </label>

                    {form.verifier_enabled ? (
                      <>
                        <label className="field">
                          <span>Reuse verifier node</span>
                          <select
                            className="input"
                            onChange={(e) => handleVerifierNodeSelect(e.target.value)}
                            value={form.verifier_node_id ?? ""}
                          >
                            <option value="">Create a unique verifier node</option>
                            {(builder?.nodes.verifiers ?? []).map((node) => (
                              <option key={node.id} value={node.id}>
                                {node.name}
                              </option>
                            ))}
                          </select>
                        </label>
                        <label className="field">
                          <span>Verifier node name</span>
                          <input
                            className="input"
                            onChange={(e) =>
                              setForm({ ...form, verifier_node_name: e.target.value })
                            }
                            value={form.verifier_node_name ?? ""}
                          />
                        </label>
                        <label className="field">
                          <span>Verifier platform</span>
                          <select
                            className="input"
                            onChange={(e) =>
                              setForm({ ...form, verifier_platform: e.target.value })
                            }
                            value={form.verifier_platform}
                          >
                            <option value="telegram">Telegram</option>
                          </select>
                        </label>
                      </>
                    ) : null}

                    <div className="field helper-note">
                      <span>Verifier behavior</span>
                      <p>
                        Telegram can be used here as a review inbox and can also still appear in
                        your final output channels.
                      </p>
                    </div>
                  </div>
                  </article>
              ) : null}

              {inspectorNode === "channel" ? (
                  <article className="canvas-card inspector-card">
                  <div className="canvas-card-head">
                    <ReviewIcon className="shortcut-icon" />
                    <div>
                      <p className="eyebrow">Channel</p>
                      <h3>Route the output</h3>
                    </div>
                  </div>
                  <p className="canvas-card-copy">
                    Choose the final destinations for agent output after any optional verifier step.
                  </p>

                  <div className="settings-stack">
                    <label className="field">
                      <span>Reuse channel node</span>
                      <select
                        className="input"
                        onChange={(e) => handleChannelNodeSelect(e.target.value)}
                        value={form.channel_node_id ?? ""}
                      >
                        <option value="">Create a unique channel node</option>
                        {(builder?.nodes.channels ?? []).map((node) => (
                          <option key={node.id} value={node.id}>
                            {node.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="field">
                      <span>Channel node name</span>
                      <input
                        className="input"
                        onChange={(e) =>
                          setForm({ ...form, channel_node_name: e.target.value })
                        }
                        value={form.channel_node_name ?? ""}
                      />
                    </label>
                    <div className="field">
                      <span>Output channels</span>
                      <div className="tool-picker">
                        {[
                          {
                            id: "telegram",
                            label: "Telegram",
                            description:
                              "Send the output into your Telegram workflow.",
                          },
                          {
                            id: "x",
                            label: "X",
                            description:
                              "Prepare or publish output for X.",
                          },
                          {
                            id: "substack",
                            label: "Substack",
                            description:
                              "Create a Substack draft from the agent output.",
                          },
                        ].map((platform) => {
                          const active = form.platforms.includes(platform.id);
                          return (
                            <label
                              className={`tool-chip ${active ? "active" : ""}`}
                              key={platform.id}
                            >
                              <input
                                checked={active}
                                onChange={(e) =>
                                  setForm({
                                    ...form,
                                    platforms: toggleValue(
                                      form.platforms,
                                      platform.id,
                                      e.target.checked,
                                    ),
                                  })
                                }
                                type="checkbox"
                              />
                              <div>
                                <strong>{platform.label}</strong>
                                <p>{platform.description}</p>
                              </div>
                            </label>
                          );
                        })}
                      </div>
                    </div>

                    <div className="field helper-note">
                      <span>Delivery note</span>
                      <p>
                        Final channels are where approved drafts land. If you need a review gate,
                        configure it in the verifier step instead of mixing it into delivery.
                      </p>
                    </div>
                  </div>
                  </article>
              ) : null}
            </>
          </aside>
        ) : null}
      </section>
    </section>
  );
}
