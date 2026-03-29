import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime
from typing import Any

from dotenv import dotenv_values, load_dotenv, set_key
import requests
from sqlmodel import func, select
import tweepy

from influencerpy.config import CONFIG_FILE, ENV_FILE, ConfigManager
from influencerpy.core.scouts import ScoutManager
from influencerpy.database import get_session
from influencerpy.logger import LOGS_DIR
from influencerpy.platforms.substack.auth import SubstackAuth
from influencerpy.platforms.substack_platform import SubstackProvider
from influencerpy.platforms.x_platform import XProvider
from influencerpy.providers.gemini import GeminiProvider
from influencerpy.tools.rss import RSSManager
from influencerpy.types.models import ContentItem
from influencerpy.types.rss import RSSFeedModel, RSSEntryModel
from influencerpy.types.schema import (
    AgentNodeModel,
    ChannelNodeModel,
    FlowChannelLinkModel,
    FlowModel,
    FlowScoutLinkModel,
    PostModel,
    ScoutModel,
    ScoutCalibrationModel,
    ScoutFeedbackModel,
    ScoutNodeModel,
)
from influencerpy.web.runtime import is_bot_running

SCOUT_TYPE_TOOL_DEFAULTS: dict[str, list[str]] = {
    "search": ["google_search"],
    "rss": ["rss"],
    "reddit": ["reddit"],
    "substack": ["substack"],
    "browser": ["browser"],
    "arxiv": ["arxiv"],
}

SCOUT_TOOL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "google_search",
        "label": "Google Search",
        "description": "Search the web for recent articles, launches, and news.",
        "recommended_for": ["search"],
    },
    {
        "id": "rss",
        "label": "RSS",
        "description": "Read subscribed feeds and scan multiple sources quickly.",
        "recommended_for": ["rss"],
    },
    {
        "id": "reddit",
        "label": "Reddit",
        "description": "Browse subreddit threads and surface discussions with traction.",
        "recommended_for": ["reddit"],
    },
    {
        "id": "substack",
        "label": "Substack",
        "description": "Pull posts from a specific Substack newsletter.",
        "recommended_for": ["substack"],
    },
    {
        "id": "browser",
        "label": "Browser",
        "description": "Open a page and navigate it when static fetches are not enough.",
        "recommended_for": ["browser"],
    },
    {
        "id": "http_request",
        "label": "HTTP Request",
        "description": "Fetch and extract article text directly from URLs.",
        "recommended_for": ["search", "browser", "substack"],
    },
    {
        "id": "arxiv",
        "label": "Arxiv",
        "description": "Search research papers and technical publications.",
        "recommended_for": ["arxiv"],
    },
]

SUPPORTED_FLOW_CHANNELS = {"telegram", "x", "substack"}
SUPPORTED_SCOUT_TYPES = {"search", "rss", "reddit", "substack", "browser", "arxiv"}
SUPPORTED_FLOW_POLICIES = {"as_it_comes", "pool"}
SUPPORTED_AGENT_INTENTS = {"scouting", "generation"}
CURATED_GEMINI_MODELS = [
    "gemini-3.1-pro-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]

GEMINI_VERIFIED_KEY = "ai.providers.gemini.connection_verified"
GEMINI_VERIFIED_AT_KEY = "ai.providers.gemini.connection_verified_at"


def _safe_json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return fallback


def _dedupe_keep_order(values: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _extract_json_object(raw: str) -> dict[str, Any]:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = candidate.strip("`")
        if candidate.startswith("json"):
            candidate = candidate[4:].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Flow planner returned invalid JSON.")
        parsed = json.loads(raw[start : end + 1])

    if not isinstance(parsed, dict):
        raise ValueError("Flow planner returned an unexpected response shape.")
    return parsed


def _flow_generator_status() -> dict[str, Any]:
    config_manager = ConfigManager()
    config_manager.ensure_config_exists()
    env_readable = True
    if ENV_FILE.exists():
        if os.access(ENV_FILE, os.R_OK):
            try:
                load_dotenv(dotenv_path=ENV_FILE, override=True)
            except OSError:
                env_readable = False
        else:
            env_readable = False

    provider = config_manager.get("ai.default_provider", "gemini")
    model_id = (config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash") or "").strip()
    connection_verified = bool(config_manager.get(GEMINI_VERIFIED_KEY, False))
    verified_at = config_manager.get(GEMINI_VERIFIED_AT_KEY)
    gemini_api_key = _get_effective_gemini_api_key()
    missing_requirements: list[str] = []

    if provider != "gemini":
        missing_requirements.append("Set Gemini as the default AI provider in Settings.")
    if not gemini_api_key:
        missing_requirements.append("Add a Gemini API key in Settings.")
    if not env_readable and not gemini_api_key:
        missing_requirements.append(
            "The settings .env file is not readable in this runtime. Fix storage permissions in Settings before using the AI flow builder."
        )
    if not model_id:
        missing_requirements.append("Choose a Gemini model in Settings.")
    if gemini_api_key and not connection_verified:
        missing_requirements.append("Save and test Gemini in Settings before using the AI flow builder.")

    return {
        "enabled": not missing_requirements,
        "provider": provider,
        "model_id": model_id or "gemini-2.5-flash",
        "connection_verified": connection_verified,
        "connection_verified_at": verified_at,
        "env_readable": env_readable,
        "missing_requirements": missing_requirements,
        "settings_path": "settings",
    }


def _get_effective_gemini_api_key() -> str:
    env_file_key = ""
    if ENV_FILE.exists() and os.access(ENV_FILE, os.R_OK):
        try:
            env_file_key = str(dotenv_values(ENV_FILE).get("GEMINI_API_KEY") or "").strip()
        except OSError:
            env_file_key = ""
    runtime_key = str(os.getenv("GEMINI_API_KEY") or "").strip()
    return env_file_key or runtime_key


def _set_gemini_verification_state(
    config_manager: ConfigManager,
    *,
    verified: bool,
    verified_at: str | None = None,
) -> None:
    config_manager.set(GEMINI_VERIFIED_KEY, verified)
    config_manager.set(GEMINI_VERIFIED_AT_KEY, verified_at if verified else None)


def _friendly_gemini_error(exc: Exception) -> str:
    raw = str(exc)
    if "API_KEY_INVALID" in raw or "API key not valid" in raw:
        return "Gemini rejected the saved API key. Open Settings and use Save and test Gemini to store a valid key."
    if "GEMINI_API_KEY not found" in raw:
        return "Add a Gemini API key in Settings before using the AI flow builder."
    return f"Gemini could not generate the flow right now: {raw}"


def _safe_load_settings_env() -> bool:
    try:
        if ENV_FILE.exists():
            if not os.access(ENV_FILE, os.R_OK):
                return False
            load_dotenv(dotenv_path=ENV_FILE, override=True)
        return True
    except PermissionError:
        return False


def _ensure_settings_storage_writable() -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists() and not os.access(CONFIG_FILE, os.R_OK):
        raise RuntimeError(
            f"Settings storage is not readable: {CONFIG_FILE}. Fix file permissions and try again."
        )
    if ENV_FILE.exists() and not os.access(ENV_FILE, os.R_OK):
        raise RuntimeError(
            f"Settings storage is not readable: {ENV_FILE}. Fix file permissions and try again."
        )

    config_replacable = os.access(CONFIG_FILE, os.W_OK) if CONFIG_FILE.exists() else False
    env_replacable = os.access(ENV_FILE, os.W_OK) if ENV_FILE.exists() else False

    if CONFIG_FILE.exists() and not config_replacable and not os.access(CONFIG_FILE.parent, os.W_OK):
        raise RuntimeError(
            f"Settings storage is not writable: {CONFIG_FILE}. Fix file permissions and try again."
        )
    if ENV_FILE.exists() and not env_replacable and not os.access(ENV_FILE.parent, os.W_OK):
        raise RuntimeError(
            f"Settings storage is not writable: {ENV_FILE}. Fix file permissions and try again."
        )
    if not ENV_FILE.exists() and not os.access(ENV_FILE.parent, os.W_OK):
        raise RuntimeError(
            f"Settings storage directory is not writable: {ENV_FILE.parent}. Fix file permissions and try again."
        )


def _is_path_effectively_writable(path: Path) -> bool:
    if path.exists():
        return os.access(path, os.W_OK) or os.access(path.parent, os.W_OK)
    return os.access(path.parent, os.W_OK)


def _write_env_file_atomically(values: dict[str, str]) -> None:
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    current = {
        key: "" if value is None else str(value)
        for key, value in dotenv_values(ENV_FILE).items()
    } if ENV_FILE.exists() else {}
    current.update(values)

    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=ENV_FILE.parent,
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
        for key, value in current.items():
            set_key(str(temp_path), key, value)
        os.replace(temp_path, ENV_FILE)
    finally:
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _persist_env_credentials(values: dict[str, str]) -> None:
    if not values:
        return
    _write_env_file_atomically(values)
    for key, value in values.items():
        os.environ[key] = value
    _safe_load_settings_env()


def _effective_credential(payload: dict[str, Any], payload_key: str, env_key: str) -> str:
    return str(payload.get(payload_key) or os.getenv(env_key, "") or "").strip()


def _fetch_gemini_models_for_api_key(api_key: str) -> list[str]:
    response = requests.get(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": api_key},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    models: list[str] = []
    for model in data.get("models", []):
        name = model.get("name", "")
        if not name.startswith("models/gemini"):
            continue
        models.append(name.replace("models/", ""))
    return _dedupe_keep_order(models + CURATED_GEMINI_MODELS)[:20]


def serialize_post(post: PostModel, scout_name: str | None = None) -> dict[str, Any]:
    return {
        "id": post.id,
        "content": post.content,
        "platform": post.platform,
        "status": post.status,
        "scheduled_time": post.scheduled_time.isoformat() if post.scheduled_time else None,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "posted_at": post.posted_at.isoformat() if post.posted_at else None,
        "external_id": post.external_id,
        "scout_id": post.scout_id,
        "scout_name": scout_name,
        "role": post.role or "delivery",
        "delivery_targets": _safe_json_loads(post.delivery_targets_json, []),
    }


def serialize_scout(scout: ScoutModel) -> dict[str, Any]:
    config = _safe_json_loads(scout.config_json, {})
    return {
        "id": scout.id,
        "name": scout.name,
        "type": scout.type,
        "intent": scout.intent,
        "schedule_cron": scout.schedule_cron,
        "last_run": scout.last_run.isoformat() if scout.last_run else None,
        "created_at": scout.created_at.isoformat() if scout.created_at else None,
        "telegram_review": scout.telegram_review,
        "platforms": _safe_json_loads(scout.platforms, []),
        "config": config,
    }


def serialize_scout_node(node: ScoutNodeModel) -> dict[str, Any]:
    config = _safe_json_loads(node.config_json, {})
    return {
        "id": node.id,
        "name": node.name,
        "type": node.type,
        "schedule_cron": node.schedule_cron,
        "last_run": node.last_run.isoformat() if node.last_run else None,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "config": config,
    }


def serialize_agent_node(node: AgentNodeModel) -> dict[str, Any]:
    config = _safe_json_loads(node.config_json, {})
    return {
        "id": node.id,
        "name": node.name,
        "intent": node.intent,
        "prompt_template": node.prompt_template,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "config": config,
    }


def serialize_channel_node(node: ChannelNodeModel) -> dict[str, Any]:
    config = _safe_json_loads(node.config_json, {})
    kind = config.get("kind", "channel")
    return {
        "id": node.id,
        "name": node.name,
        "platforms": _safe_json_loads(node.platforms, []),
        "telegram_review": node.telegram_review,
        "created_at": node.created_at.isoformat() if node.created_at else None,
        "kind": kind,
        "config": config,
    }


def _channel_node_kind(node: ChannelNodeModel) -> str:
    config = _safe_json_loads(node.config_json, {})
    kind = config.get("kind", "channel")
    return kind if kind in {"channel", "verifier"} else "channel"


def _split_delivery_nodes(
    channel_nodes: list[ChannelNodeModel],
) -> tuple[ChannelNodeModel | None, list[ChannelNodeModel]]:
    verifier_node: ChannelNodeModel | None = None
    delivery_nodes: list[ChannelNodeModel] = []
    for node in channel_nodes:
        if _channel_node_kind(node) == "verifier":
            verifier_node = verifier_node or node
            continue
        delivery_nodes.append(node)
    return verifier_node, delivery_nodes


def _serialize_flow(
    flow: FlowModel,
    scout_nodes: list[ScoutNodeModel],
    agent_node: AgentNodeModel,
    channel_nodes: list[ChannelNodeModel],
) -> dict[str, Any]:
    primary_scout = scout_nodes[0]
    verifier_node, delivery_nodes = _split_delivery_nodes(channel_nodes)
    primary_channel = delivery_nodes[0] if delivery_nodes else channel_nodes[0]
    scout_config = _safe_json_loads(primary_scout.config_json, {})
    agent_config = _safe_json_loads(agent_node.config_json, {})
    channel_platforms = sorted(
        {
            platform
            for node in delivery_nodes
            for platform in _safe_json_loads(node.platforms, [])
        }
    )
    config = {
        **scout_config,
        **agent_config,
    }
    return {
        "id": flow.id,
        "name": flow.name,
        "type": primary_scout.type,
        "intent": agent_node.intent,
        "schedule_cron": primary_scout.schedule_cron,
        "last_run": primary_scout.last_run.isoformat() if primary_scout.last_run else None,
        "created_at": flow.created_at.isoformat() if flow.created_at else None,
        "telegram_review": verifier_node is not None,
        "platforms": channel_platforms,
        "delivery_platforms": channel_platforms,
        "verifier_platform": (
            _safe_json_loads(verifier_node.platforms, [None])[0] if verifier_node else None
        ),
        "config": config,
        "flow": {
            "id": flow.id,
            "legacy_scout_id": flow.legacy_scout_id,
            "updated_at": flow.updated_at.isoformat() if flow.updated_at else None,
        },
        "nodes": {
            "scout": serialize_scout_node(primary_scout),
            "scouts": [serialize_scout_node(node) for node in scout_nodes],
            "agent": serialize_agent_node(agent_node),
            "verifier": serialize_channel_node(verifier_node) if verifier_node else None,
            "channel": serialize_channel_node(primary_channel),
            "channels": [serialize_channel_node(node) for node in delivery_nodes],
        },
    }


def _build_flow_name_map(session) -> dict[int, str]:
    flows = session.exec(select(FlowModel)).all()
    return {
        flow.legacy_scout_id: flow.name
        for flow in flows
        if flow.legacy_scout_id is not None
    }


def _get_flow_scout_nodes(session, flow_ids: list[int]) -> dict[int, list[ScoutNodeModel]]:
    if not flow_ids:
        return {}
    links = session.exec(
        select(FlowScoutLinkModel).where(FlowScoutLinkModel.flow_id.in_(flow_ids))
    ).all()
    scout_nodes = {
        node.id: node
        for node in session.exec(select(ScoutNodeModel)).all()
        if node.id is not None
    }
    grouped: dict[int, list[tuple[int, ScoutNodeModel]]] = {}
    for link in links:
        node = scout_nodes.get(link.scout_node_id)
        if not node:
            continue
        grouped.setdefault(link.flow_id, []).append((link.position, node))
    return {
        flow_id: [node for _, node in sorted(entries, key=lambda item: item[0])]
        for flow_id, entries in grouped.items()
    }


def _get_flow_channel_nodes(session, flow_ids: list[int]) -> dict[int, list[ChannelNodeModel]]:
    if not flow_ids:
        return {}
    links = session.exec(
        select(FlowChannelLinkModel).where(FlowChannelLinkModel.flow_id.in_(flow_ids))
    ).all()
    channel_nodes = {
        node.id: node
        for node in session.exec(select(ChannelNodeModel)).all()
        if node.id is not None
    }
    grouped: dict[int, list[tuple[int, ChannelNodeModel]]] = {}
    for link in links:
        node = channel_nodes.get(link.channel_node_id)
        if not node:
            continue
        grouped.setdefault(link.flow_id, []).append((link.position, node))
    return {
        flow_id: [node for _, node in sorted(entries, key=lambda item: item[0])]
        for flow_id, entries in grouped.items()
    }


def get_dashboard_snapshot() -> dict[str, Any]:
    with next(get_session()) as session:
        flows = session.exec(select(FlowModel).order_by(FlowModel.created_at.desc())).all()
        flow_scout_nodes = _get_flow_scout_nodes(session, [flow.id for flow in flows if flow.id is not None])
        flow_channel_nodes = _get_flow_channel_nodes(session, [flow.id for flow in flows if flow.id is not None])
        agent_nodes = {
            node.id: node for node in session.exec(select(AgentNodeModel)).all() if node.id is not None
        }
        scout_names = _build_flow_name_map(session)

        recent_posts = session.exec(
            select(PostModel).order_by(PostModel.created_at.desc()).limit(10)
        ).all()
        pending_posts = session.exec(
            select(PostModel)
            .where(PostModel.status.in_(("pending_review", "reviewing")))
            .order_by(PostModel.created_at.desc())
            .limit(8)
        ).all()

        rss_feed_count = session.exec(select(func.count()).select_from(RSSFeedModel)).one()
        rss_entry_count = session.exec(select(func.count()).select_from(RSSEntryModel)).one()
        processed_entry_count = session.exec(
            select(func.count()).select_from(RSSEntryModel).where(RSSEntryModel.is_processed)
        ).one()

        post_status_counts = dict(
            session.exec(select(PostModel.status, func.count()).group_by(PostModel.status)).all()
        )

        return {
            "system": {
                "bot_running": is_bot_running(),
                "updated_at": datetime.utcnow().isoformat(),
            },
            "stats": {
                "scouts_total": len(flows),
                "scheduled_scouts": len(
                    [
                        flow
                        for flow in flows
                        if flow.id in flow_scout_nodes
                        and flow_scout_nodes[flow.id]
                        and flow_scout_nodes[flow.id][0].schedule_cron
                    ]
                ),
                "posts_total": sum(post_status_counts.values()),
                "posts_by_status": post_status_counts,
                "pending_reviews": len(pending_posts),
                "rss_feeds": rss_feed_count,
                "rss_entries": rss_entry_count,
                "rss_processed_entries": processed_entry_count,
            },
            "scouts": [
                _serialize_flow(
                    flow,
                    flow_scout_nodes[flow.id],
                    agent_nodes[flow.agent_node_id],
                    flow_channel_nodes[flow.id],
                )
                for flow in flows
                if flow.id in flow_scout_nodes
                and flow.id in flow_channel_nodes
                and flow_scout_nodes[flow.id]
                and flow_channel_nodes[flow.id]
                and flow.agent_node_id in agent_nodes
            ],
            "recent_posts": [
                serialize_post(post, scout_names.get(post.scout_id)) for post in recent_posts
            ],
            "pending_posts": [
                serialize_post(post, scout_names.get(post.scout_id)) for post in pending_posts
            ],
        }


def list_posts(status: str | None = None, limit: int = 25) -> list[dict[str, Any]]:
    with next(get_session()) as session:
        statement = select(PostModel).order_by(PostModel.created_at.desc())
        if status:
            statement = statement.where(PostModel.status == status)

        scout_names = _build_flow_name_map(session)
        posts = session.exec(statement.limit(limit)).all()
        return [serialize_post(post, scout_names.get(post.scout_id)) for post in posts]


def search_posts(query: str = "", status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    posts = list_posts(status=status, limit=max(limit, 250))
    if not query.strip():
        return posts[:limit]

    needle = query.lower()
    return [
        post
        for post in posts
        if needle in (post["content"] or "").lower()
        or needle in (post["platform"] or "").lower()
        or needle in (post["status"] or "").lower()
        or needle in (post["scout_name"] or "").lower()
    ][:limit]


def list_scouts() -> list[dict[str, Any]]:
    with next(get_session()) as session:
        flows = session.exec(select(FlowModel).order_by(FlowModel.created_at.desc())).all()
        flow_scout_nodes = _get_flow_scout_nodes(session, [flow.id for flow in flows if flow.id is not None])
        flow_channel_nodes = _get_flow_channel_nodes(session, [flow.id for flow in flows if flow.id is not None])
        agent_nodes = {
            node.id: node for node in session.exec(select(AgentNodeModel)).all() if node.id is not None
        }
        return [
            _serialize_flow(
                flow,
                flow_scout_nodes[flow.id],
                agent_nodes[flow.agent_node_id],
                flow_channel_nodes[flow.id],
            )
            for flow in flows
            if flow.id in flow_scout_nodes
            and flow.id in flow_channel_nodes
            and flow_scout_nodes[flow.id]
            and flow_channel_nodes[flow.id]
            and flow.agent_node_id in agent_nodes
        ]


def _build_scout_config(payload: dict[str, Any]) -> dict[str, Any]:
    scout_type = payload["type"]
    config: dict[str, Any] = {}
    base_tools = SCOUT_TYPE_TOOL_DEFAULTS.get(scout_type, [])
    tools = base_tools[:1]

    if scout_type == "search":
        config["query"] = payload.get("query", "")
    elif scout_type == "rss":
        feeds = [item.strip() for item in payload.get("feeds", []) if item.strip()]
        config["feeds"] = feeds
    elif scout_type == "reddit":
        subreddits = [item.strip() for item in payload.get("subreddits", []) if item.strip()]
        config["subreddits"] = subreddits
        config["reddit_sort"] = payload.get("reddit_sort", "hot")
    elif scout_type == "substack":
        config["newsletter_url"] = payload.get("newsletter_url", "")
        config["substack_sort"] = payload.get("substack_sort", "new")
    elif scout_type == "browser":
        config["url"] = payload.get("url", "")
    elif scout_type == "arxiv":
        config["query"] = payload.get("query", "")
        if payload.get("date_filter"):
            config["date_filter"] = payload["date_filter"]
    else:
        raise RuntimeError(f"Unsupported scout type '{scout_type}'")

    config["tools"] = tools

    return config


def _build_agent_config(payload: dict[str, Any]) -> dict[str, Any]:
    provider = payload.get("provider", "gemini")
    model_id = payload.get("model_id")
    temperature = payload.get("temperature")
    config: dict[str, Any] = {
        "flow_policy": payload.get("flow_policy", "pool"),
        "generation_config": {
            "provider": provider,
            "model_id": model_id or "gemini-2.5-flash",
            "temperature": float(temperature if temperature is not None else 0.7),
        }
    }
    if payload.get("image_generation"):
        config["image_generation"] = True
    return config


def _upsert_legacy_scout_for_flow(
    session,
    flow_name: str,
    scout_node: ScoutNodeModel,
    agent_node: AgentNodeModel,
    delivery_nodes: list[ChannelNodeModel],
    verifier_node: ChannelNodeModel | None = None,
    legacy_scout: ScoutModel | None = None,
) -> ScoutModel:
    scout_config = _safe_json_loads(scout_node.config_json, {})
    agent_config = _safe_json_loads(agent_node.config_json, {})
    merged_config = {**scout_config, **agent_config}
    merged_platforms = sorted(
        {
            platform
            for channel_node in delivery_nodes
            for platform in _safe_json_loads(channel_node.platforms, [])
        }
    )
    telegram_review = verifier_node is not None

    if legacy_scout is None:
        legacy_scout = ScoutModel(
            name=flow_name,
            type=scout_node.type,
            config_json=json.dumps(merged_config),
            intent=agent_node.intent,
            prompt_template=agent_node.prompt_template,
            schedule_cron=scout_node.schedule_cron,
            platforms=json.dumps(merged_platforms),
            telegram_review=telegram_review,
            last_run=scout_node.last_run,
        )
    else:
        legacy_scout.name = flow_name
        legacy_scout.type = scout_node.type
        legacy_scout.config_json = json.dumps(merged_config)
        legacy_scout.intent = agent_node.intent
        legacy_scout.prompt_template = agent_node.prompt_template
        legacy_scout.schedule_cron = scout_node.schedule_cron
        legacy_scout.platforms = json.dumps(merged_platforms)
        legacy_scout.telegram_review = telegram_review
        legacy_scout.last_run = scout_node.last_run

    session.add(legacy_scout)
    session.flush()
    return legacy_scout


def _subscribe_rss_feeds_for_legacy_scout(legacy_scout_id: int | None, scout_node: ScoutNodeModel) -> None:
    if legacy_scout_id is None:
        return
    config = _safe_json_loads(scout_node.config_json, {})
    feeds = config.get("feeds", [])
    if scout_node.type == "rss" and feeds:
        rss_manager = RSSManager()
        for feed_url in feeds:
            rss_manager.subscribe(feed_url, scout_id=legacy_scout_id)


def _subscribe_rss_feeds_for_flow(legacy_scout_id: int | None, scout_nodes: list[ScoutNodeModel]) -> None:
    for scout_node in scout_nodes:
        _subscribe_rss_feeds_for_legacy_scout(legacy_scout_id, scout_node)


def _cleanup_preview_scout(manager: ScoutManager, scout_id: int | None) -> None:
    if scout_id is None:
        return
    feeds = manager.session.exec(
        select(RSSFeedModel).where(RSSFeedModel.scout_id == scout_id)
    ).all()
    for feed in feeds:
        entries = manager.session.exec(
            select(RSSEntryModel).where(RSSEntryModel.feed_id == feed.id)
        ).all()
        for entry in entries:
            manager.session.delete(entry)
        manager.session.delete(feed)
    scout = manager.session.get(ScoutModel, scout_id)
    if scout:
        manager.session.delete(scout)
    manager.session.commit()


def _get_flow_bundle(session, flow_id: int) -> tuple[FlowModel, ScoutNodeModel, AgentNodeModel, ChannelNodeModel]:
    flow = session.get(FlowModel, flow_id)
    if not flow:
        raise KeyError(f"Flow {flow_id} not found")
    scout_node = session.get(ScoutNodeModel, flow.scout_node_id)
    agent_node = session.get(AgentNodeModel, flow.agent_node_id)
    channel_node = session.get(ChannelNodeModel, flow.channel_node_id)
    if not scout_node or not agent_node or not channel_node:
        raise RuntimeError(f"Flow {flow_id} has missing nodes")
    return flow, scout_node, agent_node, channel_node


def _sync_flow_scout_links(session, flow: FlowModel, scout_node_ids: list[int]) -> None:
    existing_links = session.exec(
        select(FlowScoutLinkModel).where(FlowScoutLinkModel.flow_id == flow.id)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.flush()
    for position, scout_node_id in enumerate(scout_node_ids):
        session.add(
            FlowScoutLinkModel(
                flow_id=flow.id,
                scout_node_id=scout_node_id,
                position=position,
            )
        )


def _sync_flow_channel_links(session, flow: FlowModel, channel_node_ids: list[int]) -> None:
    existing_links = session.exec(
        select(FlowChannelLinkModel).where(FlowChannelLinkModel.flow_id == flow.id)
    ).all()
    for link in existing_links:
        session.delete(link)
    session.flush()
    for position, channel_node_id in enumerate(channel_node_ids):
        session.add(
            FlowChannelLinkModel(
                flow_id=flow.id,
                channel_node_id=channel_node_id,
                position=position,
            )
        )


def _extract_flow_scout_ids(payload: dict[str, Any], primary_scout_id: int | None = None) -> list[int]:
    selected = [int(item) for item in payload.get("scout_node_ids", []) if item]
    if payload.get("scout_node_id"):
        selected.insert(0, int(payload["scout_node_id"]))
    if primary_scout_id is not None:
        selected.insert(0, int(primary_scout_id))
    ordered_unique: list[int] = []
    for value in selected:
        if value not in ordered_unique:
            ordered_unique.append(value)
    return ordered_unique


def _extract_flow_channel_ids(
    payload: dict[str, Any],
    primary_channel_id: int | None = None,
    verifier_node_id: int | None = None,
) -> list[int]:
    selected = [int(item) for item in payload.get("channel_node_ids", []) if item]
    if payload.get("channel_node_id"):
        selected.insert(0, int(payload["channel_node_id"]))
    if primary_channel_id is not None:
        selected.insert(0, int(primary_channel_id))
    if verifier_node_id is not None:
        selected.append(int(verifier_node_id))
    ordered_unique: list[int] = []
    for value in selected:
        if value not in ordered_unique:
            ordered_unique.append(value)
    return ordered_unique


def _apply_runtime_scout_config(
    scout: ScoutModel,
    flow_name: str,
    scout_node: ScoutNodeModel,
    agent_node: AgentNodeModel,
    delivery_nodes: list[ChannelNodeModel],
    verifier_node: ChannelNodeModel | None = None,
    *,
    runtime_name: str | None = None,
) -> ScoutModel:
    scout_config = _safe_json_loads(scout_node.config_json, {})
    agent_config = _safe_json_loads(agent_node.config_json, {})
    scout.name = runtime_name or flow_name
    scout.type = scout_node.type
    scout.config_json = json.dumps({**scout_config, **agent_config})
    scout.intent = agent_node.intent
    scout.prompt_template = agent_node.prompt_template
    scout.schedule_cron = scout_node.schedule_cron
    scout.platforms = json.dumps(
        sorted(
            {
                platform
                for channel_node in delivery_nodes
                for platform in _safe_json_loads(channel_node.platforms, [])
            }
        )
    )
    scout.telegram_review = verifier_node is not None
    return scout


def _sort_content_items(items: list[ContentItem]) -> list[ContentItem]:
    return sorted(
        items,
        key=lambda item: item.published_at or datetime.min,
        reverse=True,
    )


def _content_dedupe_key(item: ContentItem) -> str:
    if item.url:
        return f"url:{item.url.strip().lower()}"
    if item.source_id:
        return f"source:{item.source_id.strip().lower()}"
    return f"title:{item.title.strip().lower()}"


def _tag_content_item_origin(item: ContentItem, scout_node: ScoutNodeModel) -> ContentItem:
    metadata = dict(item.metadata or {})
    matched_scouts = list(metadata.get("matched_scouts", []))
    if scout_node.name not in matched_scouts:
        matched_scouts.append(scout_node.name)
    metadata["matched_scouts"] = matched_scouts
    metadata["scout_node_id"] = scout_node.id
    metadata["scout_node_name"] = scout_node.name
    item.metadata = metadata
    return item


def _dedupe_content_items(items: list[ContentItem]) -> list[ContentItem]:
    deduped: list[ContentItem] = []
    index_by_key: dict[str, int] = {}

    for item in _sort_content_items(items):
        key = _content_dedupe_key(item)
        existing_index = index_by_key.get(key)
        if existing_index is None:
            index_by_key[key] = len(deduped)
            deduped.append(item)
            continue

        existing = deduped[existing_index]
        existing_metadata = dict(existing.metadata or {})
        existing_scouts = list(existing_metadata.get("matched_scouts", []))
        for scout_name in item.metadata.get("matched_scouts", []):
            if scout_name not in existing_scouts:
                existing_scouts.append(scout_name)
        if existing_scouts:
            existing_metadata["matched_scouts"] = existing_scouts
        if not existing.summary and item.summary:
            existing.summary = item.summary
        existing.metadata = existing_metadata

    return deduped


def get_scout_builder_snapshot() -> dict[str, Any]:
    with next(get_session()) as session:
        channel_nodes = [
            node
            for node in session.exec(select(ChannelNodeModel).order_by(ChannelNodeModel.created_at.desc())).all()
        ]
        return {
            "gemini_models": get_gemini_models(),
            "flow_generator": _flow_generator_status(),
            "flow_policies": [
                {
                    "id": "as_it_comes",
                    "label": "As It Comes",
                    "description": "Stop at the first scout that produces useful signals and send those forward.",
                },
                {
                    "id": "pool",
                    "label": "Pool Aggregation",
                    "description": "Collect signals from every selected scout, merge them, and let the agent choose from the full pool.",
                },
            ],
            "type_defaults": SCOUT_TYPE_TOOL_DEFAULTS,
            "tool_catalog": SCOUT_TOOL_CATALOG,
            "nodes": {
                "scouts": [
                    serialize_scout_node(node)
                    for node in session.exec(select(ScoutNodeModel).order_by(ScoutNodeModel.created_at.desc())).all()
                ],
                "agents": [
                    serialize_agent_node(node)
                    for node in session.exec(select(AgentNodeModel).order_by(AgentNodeModel.created_at.desc())).all()
                ],
                "verifiers": [
                    serialize_channel_node(node)
                    for node in channel_nodes
                    if _channel_node_kind(node) == "verifier"
                ],
                "channels": [
                    serialize_channel_node(node)
                    for node in channel_nodes
                    if _channel_node_kind(node) != "verifier"
                ],
            },
        }


def _normalize_generated_scout(spec: dict[str, Any], index: int) -> dict[str, Any]:
    scout_type = spec.get("type", "rss")
    if scout_type not in SUPPORTED_SCOUT_TYPES:
        scout_type = "rss"

    name = str(spec.get("name") or f"Scout {index}").strip() or f"Scout {index}"
    schedule_cron = str(spec.get("schedule_cron") or "").strip() or None

    normalized = {
        "name": name,
        "type": scout_type,
        "schedule_cron": schedule_cron,
        "tools": SCOUT_TYPE_TOOL_DEFAULTS.get(scout_type, [scout_type]),
        "query": str(spec.get("query") or "").strip(),
        "feeds": [str(feed).strip() for feed in spec.get("feeds", []) if str(feed).strip()],
        "subreddits": [str(item).strip() for item in spec.get("subreddits", []) if str(item).strip()],
        "reddit_sort": str(spec.get("reddit_sort") or "hot").strip() or "hot",
        "newsletter_url": str(spec.get("newsletter_url") or "").strip(),
        "substack_sort": str(spec.get("substack_sort") or "new").strip() or "new",
        "url": str(spec.get("url") or "").strip(),
        "date_filter": str(spec.get("date_filter") or "").strip(),
    }

    if scout_type == "rss" and not normalized["feeds"]:
        normalized["feeds"] = ["https://example.com/feed.xml"]
    if scout_type == "reddit" and not normalized["subreddits"]:
        normalized["subreddits"] = ["technology"]
    if scout_type in {"search", "arxiv"} and not normalized["query"]:
        normalized["query"] = "AI"
    if scout_type == "substack" and not normalized["newsletter_url"]:
        normalized["newsletter_url"] = "https://www.example.com"
    if scout_type == "browser" and not normalized["url"]:
        normalized["url"] = "https://example.com"

    return normalized


def _normalize_generated_channel(spec: dict[str, Any], index: int) -> dict[str, Any]:
    platforms = [
        platform
        for platform in [str(item).strip().lower() for item in spec.get("platforms", [])]
        if platform in SUPPORTED_FLOW_CHANNELS
    ]
    if not platforms:
        platforms = ["telegram"]
    return {
        "name": str(spec.get("name") or f"Output {index}").strip() or f"Output {index}",
        "platforms": platforms,
    }


def _build_flow_planner_prompt(user_prompt: str, model_id: str) -> str:
    return f"""
You are planning an InfluencerPy workflow graph.

The user will describe the automation they want. Produce only valid JSON.

If the request is missing important information, respond with:
{{
  "mode": "clarify",
  "assistant_message": "short helpful response",
  "questions": ["question 1", "question 2"]
}}

If the request is specific enough, respond with:
{{
  "mode": "plan",
  "assistant_message": "short helpful summary of what you built",
  "name": "short flow name",
  "summary": "one sentence summary",
  "scouts": [
    {{
      "name": "node name",
      "type": "rss|reddit|search|substack|browser|arxiv",
      "schedule_cron": "cron string or empty string for manual",
      "query": "optional",
      "feeds": ["rss feed urls"],
      "subreddits": ["subreddit names"],
      "reddit_sort": "hot|new|top|rising",
      "newsletter_url": "optional",
      "substack_sort": "new|top",
      "url": "optional",
      "date_filter": "today|week|month"
    }}
  ],
  "policy": {{
    "flow_policy": "pool|as_it_comes"
  }},
  "agent": {{
    "name": "agent name",
    "intent": "scouting|generation",
    "prompt_template": "clear instructions for the agent",
    "temperature": 0.0,
    "image_generation": false
  }},
  "channels": [
    {{
      "name": "channel name",
      "platforms": ["telegram|x|substack"]
    }}
  ],
  "verifier": {{
    "enabled": false,
    "name": "optional verifier name",
    "platform": "telegram"
  }}
}}

Rules:
- One scout node must use exactly one scout type.
- If there is more than one scout, include a policy.
- Agents transform scout outputs into content. Agents do not own scout sources.
- Channels are final outputs. A flow can have multiple channels.
- Use manual scheduling unless the request clearly asks for a schedule.
- Ask for clarification when the user did not make the sources, transformation goal, or outputs clear enough to build a good flow.
- Be practical and concise. Keep names product-like.
- The configured model for generation is {model_id}.
- Return JSON only. No markdown fences.

Conversation:
{user_prompt.strip()}
""".strip()


def generate_flow_suggestion(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        prompt = "\n".join(
            f"{str(message.get('role') or 'user').strip().upper()}: {str(message.get('content') or '').strip()}"
            for message in messages
            if isinstance(message, dict) and str(message.get("content") or "").strip()
        ).strip()
    else:
        prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        raise ValueError("Describe the workflow you want to build.")

    status = _flow_generator_status()
    if not status["enabled"]:
        raise ValueError(" ".join(status["missing_requirements"]))

    provider = GeminiProvider(
        model_id=status["model_id"],
        temperature=0.35,
        api_key=_get_effective_gemini_api_key(),
    )
    try:
        raw_response = provider.generate(_build_flow_planner_prompt(prompt, status["model_id"]))
    except Exception as exc:
        friendly_error = _friendly_gemini_error(exc)
        if "Gemini rejected the saved API key" in friendly_error:
            config_manager = ConfigManager()
            config_manager.ensure_config_exists()
            _set_gemini_verification_state(config_manager, verified=False)
        raise ValueError(friendly_error) from exc
    planned = _extract_json_object(raw_response)

    mode = str(planned.get("mode") or "plan").strip().lower()
    assistant_message = str(planned.get("assistant_message") or "").strip()
    if mode == "clarify":
        questions = [
            str(item).strip()
            for item in planned.get("questions", [])
            if str(item).strip()
        ][:3]
        if not assistant_message:
            assistant_message = "I need a bit more context before I can draft a strong flow."
        if not questions:
            questions = ["Which sources should this flow listen to?", "Where should the output go?"]
        return {
            "mode": "clarify",
            "assistant_message": assistant_message,
            "questions": questions,
        }

    scouts = planned.get("scouts", [])
    channels = planned.get("channels", [])
    agent = planned.get("agent", {})
    policy = planned.get("policy", {})
    verifier = planned.get("verifier", {})

    if not isinstance(scouts, list) or not scouts:
        raise ValueError("Flow planner did not produce any scout nodes.")
    if not isinstance(channels, list) or not channels:
        raise ValueError("Flow planner did not produce any output channels.")
    if not isinstance(agent, dict):
        raise ValueError("Flow planner did not produce an agent configuration.")

    normalized_scouts = [
        _normalize_generated_scout(item if isinstance(item, dict) else {}, index + 1)
        for index, item in enumerate(scouts[:4])
    ]
    normalized_channels = [
        _normalize_generated_channel(item if isinstance(item, dict) else {}, index + 1)
        for index, item in enumerate(channels[:4])
    ]
    flow_name = str(planned.get("name") or "AI-generated flow").strip() or "AI-generated flow"
    summary = str(planned.get("summary") or "").strip()
    flow_policy = str(policy.get("flow_policy") or "pool")
    if flow_policy not in SUPPORTED_FLOW_POLICIES:
        flow_policy = "pool"

    agent_intent = str(agent.get("intent") or "generation")
    if agent_intent not in SUPPORTED_AGENT_INTENTS:
        agent_intent = "generation"

    temperature = agent.get("temperature", 0.7)
    try:
        temperature = float(temperature)
    except (TypeError, ValueError):
        temperature = 0.7
    temperature = max(0.0, min(1.0, temperature))

    verifier_enabled = bool(verifier.get("enabled"))
    verifier_platform = str(verifier.get("platform") or "telegram").strip().lower() or "telegram"
    if verifier_platform not in SUPPORTED_FLOW_CHANNELS:
        verifier_platform = "telegram"

    agent_payload = {
        "provider": "gemini",
        "model_id": status["model_id"],
        "temperature": temperature,
        "flow_policy": flow_policy,
        "image_generation": bool(agent.get("image_generation")),
    }
    agent_name = str(agent.get("name") or f"{flow_name} Agent").strip() or f"{flow_name} Agent"
    agent_prompt = str(
        agent.get("prompt_template")
        or (
            "Turn the incoming scout context into a concise, useful digest."
            if agent_intent == "scouting"
            else "Turn the incoming scout context into a publish-ready draft."
        )
    ).strip()
    verifier_name = (
        str(verifier.get("name") or f"{flow_name} Verifier").strip() or f"{flow_name} Verifier"
    )

    draft_scout_nodes = [
        {
            "id": -(index + 1),
            "name": scout_spec["name"],
            "type": scout_spec["type"],
            "schedule_cron": scout_spec["schedule_cron"],
            "last_run": None,
            "created_at": None,
            "config": _build_scout_config(scout_spec),
        }
        for index, scout_spec in enumerate(normalized_scouts)
    ]
    draft_channel_nodes = [
        {
            "id": -(100 + index + 1),
            "name": channel_spec["name"],
            "platforms": channel_spec["platforms"],
            "telegram_review": False,
            "kind": "channel",
            "created_at": None,
            "config": {"kind": "channel"},
        }
        for index, channel_spec in enumerate(normalized_channels)
    ]
    draft_agent_node = {
        "id": -200,
        "name": agent_name,
        "intent": agent_intent,
        "prompt_template": agent_prompt,
        "created_at": None,
        "config": _build_agent_config(agent_payload),
    }
    draft_verifier_node = (
        {
            "id": -300,
            "name": verifier_name,
            "platforms": [verifier_platform],
            "telegram_review": False,
            "kind": "verifier",
            "created_at": None,
            "config": {"kind": "verifier"},
        }
        if verifier_enabled
        else None
    )

    primary_scout_config = draft_scout_nodes[0]["config"]

    return {
        "mode": "plan",
        "assistant_message": assistant_message or summary or f"Drafted {flow_name}.",
        "name": flow_name,
        "summary": summary,
        "prompt": prompt,
        "payload": {
            "name": flow_name,
            "scout_node_id": None,
            "scout_node_ids": [],
            "scout_node_name": draft_scout_nodes[0]["name"],
            "agent_node_id": None,
            "agent_node_name": draft_agent_node["name"],
            "channel_node_id": None,
            "channel_node_ids": [],
            "channel_node_name": draft_channel_nodes[0]["name"],
            "verifier_enabled": verifier_enabled,
            "verifier_node_id": None,
            "verifier_node_name": verifier_name if verifier_enabled else "",
            "verifier_platform": verifier_platform,
            "type": draft_scout_nodes[0]["type"],
            "intent": draft_agent_node["intent"],
            "schedule_cron": draft_scout_nodes[0]["schedule_cron"],
            "tools": SCOUT_TYPE_TOOL_DEFAULTS.get(draft_scout_nodes[0]["type"], [draft_scout_nodes[0]["type"]]),
            "prompt_template": draft_agent_node["prompt_template"] or "",
            "telegram_review": False,
            "platforms": normalized_channels[0]["platforms"],
            "image_generation": bool(agent_payload["image_generation"]),
            "provider": "gemini",
            "model_id": status["model_id"],
            "temperature": temperature,
            "flow_policy": flow_policy,
            "query": str(primary_scout_config.get("query") or ""),
            "feeds": list(primary_scout_config.get("feeds") or [""]),
            "subreddits": list(primary_scout_config.get("subreddits") or [""]),
            "reddit_sort": str(primary_scout_config.get("reddit_sort") or "hot"),
            "newsletter_url": str(primary_scout_config.get("newsletter_url") or ""),
            "substack_sort": str(primary_scout_config.get("substack_sort") or "new"),
            "url": str(primary_scout_config.get("url") or ""),
            "date_filter": str(primary_scout_config.get("date_filter") or ""),
        },
        "nodes": {
            "scouts": draft_scout_nodes,
            "agent": draft_agent_node,
            "channels": draft_channel_nodes,
            "verifier": draft_verifier_node,
        },
        "draft_only": True,
    }


def create_scout_node(payload: dict[str, Any]) -> dict[str, Any]:
    with next(get_session()) as session:
        node = ScoutNodeModel(
            name=payload.get("scout_node_name") or payload.get("name") or "Scout node",
            type=payload["type"],
            config_json=json.dumps(_build_scout_config(payload)),
            schedule_cron=payload.get("schedule_cron"),
        )
        session.add(node)
        session.commit()
        session.refresh(node)
        return serialize_scout_node(node)


def update_scout_node(node_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with next(get_session()) as session:
        node = session.get(ScoutNodeModel, node_id)
        if not node:
            raise KeyError(f"Scout node {node_id} not found")
        node.name = payload.get("scout_node_name") or payload.get("name") or node.name
        node.type = payload.get("type", node.type)
        node.config_json = json.dumps(_build_scout_config(payload))
        node.schedule_cron = payload.get("schedule_cron")
        session.add(node)
        session.commit()
        session.refresh(node)
        return serialize_scout_node(node)


def preview_scout_node(payload: dict[str, Any]) -> dict[str, Any]:
    manager = ScoutManager()
    preview_scout: ScoutModel | None = None
    try:
        preview_scout = ScoutModel(
            name=payload.get("scout_node_name") or payload.get("name") or "Scout preview",
            type=payload["type"],
            config_json=json.dumps(_build_scout_config(payload)),
            intent="scouting",
            prompt_template="Preview scouting results only.",
            schedule_cron=payload.get("schedule_cron"),
            platforms=json.dumps(["telegram"]),
            telegram_review=False,
        )
        manager.session.add(preview_scout)
        manager.session.commit()
        manager.session.refresh(preview_scout)
        _subscribe_rss_feeds_for_legacy_scout(preview_scout.id, ScoutNodeModel(
            name=preview_scout.name,
            type=preview_scout.type,
            config_json=preview_scout.config_json,
            schedule_cron=preview_scout.schedule_cron,
        ))
        items = manager.run_scout(preview_scout, limit=8)
        return {
            "items_found": len(items),
            "items": [
                {
                    "title": item.title,
                    "url": item.url,
                    "summary": item.summary,
                    "published_at": item.published_at.isoformat() if item.published_at else None,
                }
                for item in items[:5]
            ],
        }
    finally:
        _cleanup_preview_scout(manager, preview_scout.id if preview_scout else None)
        manager.session.close()


def create_scout(payload: dict[str, Any]) -> dict[str, Any]:
    with next(get_session()) as session:
        existing_flow = session.exec(select(FlowModel).where(FlowModel.name == payload["name"])).first()
        if existing_flow:
            raise RuntimeError(f"Flow '{payload['name']}' already exists")

        primary_scout_id = payload.get("scout_node_id")
        if not primary_scout_id and payload.get("scout_node_ids"):
            primary_scout_id = payload["scout_node_ids"][0]
        scout_node = session.get(ScoutNodeModel, primary_scout_id) if primary_scout_id else None
        if scout_node is None:
            scout_node = ScoutNodeModel(
                name=payload.get("scout_node_name") or f"{payload['name']} Scout",
                type=payload["type"],
                config_json=json.dumps(_build_scout_config(payload)),
                schedule_cron=payload.get("schedule_cron"),
            )
            session.add(scout_node)
            session.flush()

        agent_node = session.get(AgentNodeModel, payload["agent_node_id"]) if payload.get("agent_node_id") else None
        if agent_node is None:
            agent_node = AgentNodeModel(
                name=payload.get("agent_node_name") or f"{payload['name']} Agent",
                intent=payload.get("intent", "scouting"),
                prompt_template=payload.get("prompt_template") or (
                    "Provide a clear summary of each content item found, highlighting why it's interesting and relevant."
                    if payload.get("intent", "scouting") == "scouting"
                    else "Summarize this content and highlight key takeaways for a social media audience."
                ),
                config_json=json.dumps(_build_agent_config(payload)),
            )
            session.add(agent_node)
            session.flush()

        primary_channel_id = payload.get("channel_node_id")
        if not primary_channel_id and payload.get("channel_node_ids"):
            primary_channel_id = payload["channel_node_ids"][0]
        channel_node = session.get(ChannelNodeModel, primary_channel_id) if primary_channel_id else None
        if channel_node is None:
            channel_node = ChannelNodeModel(
                name=payload.get("channel_node_name") or f"{payload['name']} Channel",
                platforms=json.dumps(payload.get("platforms", ["telegram"])),
                telegram_review=False,
                config_json=json.dumps({"kind": "channel"}),
            )
            session.add(channel_node)
            session.flush()
        else:
            channel_node.telegram_review = False
            channel_node.config_json = json.dumps({"kind": "channel"})
            session.add(channel_node)

        verifier_node = None
        if payload.get("verifier_enabled"):
            verifier_node = (
                session.get(ChannelNodeModel, payload["verifier_node_id"])
                if payload.get("verifier_node_id")
                else None
            )
            if verifier_node is None:
                verifier_node = ChannelNodeModel(
                    name=payload.get("verifier_node_name") or f"{payload['name']} Verifier",
                    platforms=json.dumps([payload.get("verifier_platform", "telegram")]),
                    telegram_review=False,
                    config_json=json.dumps({"kind": "verifier"}),
                )
                session.add(verifier_node)
                session.flush()
            else:
                verifier_node.name = payload.get("verifier_node_name") or verifier_node.name
                verifier_node.platforms = json.dumps([payload.get("verifier_platform", "telegram")])
                verifier_node.config_json = json.dumps({"kind": "verifier"})
                session.add(verifier_node)

        delivery_nodes = [channel_node]
        legacy_scout = _upsert_legacy_scout_for_flow(
            session, payload["name"], scout_node, agent_node, delivery_nodes, verifier_node
        )
        flow = FlowModel(
            name=payload["name"],
            scout_node_id=scout_node.id,
            agent_node_id=agent_node.id,
            channel_node_id=channel_node.id,
            legacy_scout_id=legacy_scout.id,
        )
        session.add(flow)
        session.flush()
        _sync_flow_scout_links(session, flow, _extract_flow_scout_ids(payload, scout_node.id))
        _sync_flow_channel_links(
            session,
            flow,
            _extract_flow_channel_ids(
                payload,
                channel_node.id,
                verifier_node.id if verifier_node and verifier_node.id is not None else None,
            ),
        )
        session.commit()
        session.refresh(flow)
        scout_nodes = _get_flow_scout_nodes(session, [flow.id]).get(flow.id, [scout_node])
        linked_channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])
        linked_verifier, linked_delivery_nodes = _split_delivery_nodes(linked_channel_nodes)
        _upsert_legacy_scout_for_flow(
            session,
            payload["name"],
            scout_node,
            agent_node,
            linked_delivery_nodes,
            linked_verifier,
            legacy_scout,
        )
        session.commit()
        _subscribe_rss_feeds_for_flow(legacy_scout.id, scout_nodes)
        return _serialize_flow(flow, scout_nodes, agent_node, linked_channel_nodes)


def update_scout_record(scout_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    with next(get_session()) as session:
        flow, scout_node, agent_node, channel_node = _get_flow_bundle(session, scout_id)
        linked_channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])
        current_verifier_node, _ = _split_delivery_nodes(linked_channel_nodes)

        if payload.get("name") and payload["name"] != flow.name:
            existing_flow = session.exec(select(FlowModel).where(FlowModel.name == payload["name"])).first()
            if existing_flow and existing_flow.id != flow.id:
                raise RuntimeError(f"Flow '{payload['name']}' already exists")
            flow.name = payload["name"]

        primary_scout_id = payload.get("scout_node_id")
        if not primary_scout_id and payload.get("scout_node_ids"):
            primary_scout_id = payload["scout_node_ids"][0]
        replacement_scout = session.get(ScoutNodeModel, primary_scout_id) if primary_scout_id else scout_node
        replacement_agent = session.get(AgentNodeModel, payload["agent_node_id"]) if payload.get("agent_node_id") else agent_node
        primary_channel_id = payload.get("channel_node_id")
        if not primary_channel_id and payload.get("channel_node_ids"):
            primary_channel_id = payload["channel_node_ids"][0]
        replacement_channel = session.get(ChannelNodeModel, primary_channel_id) if primary_channel_id else channel_node

        if replacement_scout is scout_node:
            scout_node.name = payload.get("scout_node_name", scout_node.name)
            scout_node.type = payload.get("type", scout_node.type)
            scout_node.config_json = json.dumps(_build_scout_config(payload))
            scout_node.schedule_cron = payload.get("schedule_cron")
        else:
            flow.scout_node_id = replacement_scout.id
            scout_node = replacement_scout

        if replacement_agent is agent_node:
            agent_node.name = payload.get("agent_node_name", agent_node.name)
            agent_node.intent = payload.get("intent", agent_node.intent)
            if "prompt_template" in payload:
                agent_node.prompt_template = payload.get("prompt_template")
            agent_node.config_json = json.dumps(_build_agent_config(payload))
        else:
            flow.agent_node_id = replacement_agent.id
            agent_node = replacement_agent

        if replacement_channel is channel_node:
            channel_node.name = payload.get("channel_node_name", channel_node.name)
            channel_node.platforms = json.dumps(payload.get("platforms", ["telegram"]))
            channel_node.telegram_review = False
            channel_node.config_json = json.dumps({"kind": "channel"})
        else:
            flow.channel_node_id = replacement_channel.id
            channel_node = replacement_channel
            channel_node.config_json = json.dumps({"kind": "channel"})

        verifier_node = None
        if payload.get("verifier_enabled"):
            verifier_node = (
                session.get(ChannelNodeModel, payload["verifier_node_id"])
                if payload.get("verifier_node_id")
                else current_verifier_node
            )
            if verifier_node is None:
                verifier_node = ChannelNodeModel(
                    name=payload.get("verifier_node_name") or f"{flow.name} Verifier",
                    platforms=json.dumps([payload.get("verifier_platform", "telegram")]),
                    telegram_review=False,
                    config_json=json.dumps({"kind": "verifier"}),
                )
                session.add(verifier_node)
                session.flush()
            else:
                verifier_node.name = payload.get("verifier_node_name") or verifier_node.name
                verifier_node.platforms = json.dumps([payload.get("verifier_platform", "telegram")])
                verifier_node.telegram_review = False
                verifier_node.config_json = json.dumps({"kind": "verifier"})
                session.add(verifier_node)

        flow.updated_at = datetime.utcnow()

        legacy_scout = session.get(ScoutModel, flow.legacy_scout_id) if flow.legacy_scout_id else None
        legacy_scout = _upsert_legacy_scout_for_flow(
            session,
            flow.name,
            scout_node,
            agent_node,
            [channel_node],
            verifier_node,
            legacy_scout,
        )
        flow.legacy_scout_id = legacy_scout.id
        session.add(flow)
        _sync_flow_scout_links(session, flow, _extract_flow_scout_ids(payload, scout_node.id))
        _sync_flow_channel_links(
            session,
            flow,
            _extract_flow_channel_ids(
                payload,
                channel_node.id,
                verifier_node.id if verifier_node and verifier_node.id is not None else None,
            ),
        )
        session.commit()
        session.refresh(flow)
        scout_nodes = _get_flow_scout_nodes(session, [flow.id]).get(flow.id, [scout_node])
        linked_channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])
        linked_verifier, linked_delivery_nodes = _split_delivery_nodes(linked_channel_nodes)
        _upsert_legacy_scout_for_flow(
            session,
            flow.name,
            scout_node,
            agent_node,
            linked_delivery_nodes,
            linked_verifier,
            legacy_scout,
        )
        session.commit()
        _subscribe_rss_feeds_for_flow(legacy_scout.id, scout_nodes)
        return _serialize_flow(flow, scout_nodes, agent_node, linked_channel_nodes)


def delete_scout_record(scout_id: int) -> dict[str, Any]:
    with next(get_session()) as session:
        flow, scout_node, agent_node, channel_node = _get_flow_bundle(session, scout_id)
        name = flow.name
        legacy_scout = session.get(ScoutModel, flow.legacy_scout_id) if flow.legacy_scout_id else None
        channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])

        if legacy_scout:
            feedbacks = session.exec(
                select(ScoutFeedbackModel).where(ScoutFeedbackModel.scout_id == legacy_scout.id)
            ).all()
            calibrations = session.exec(
                select(ScoutCalibrationModel).where(ScoutCalibrationModel.scout_id == legacy_scout.id)
            ).all()
            for item in [*feedbacks, *calibrations]:
                session.delete(item)
            session.delete(legacy_scout)

        session.delete(flow)
        session.commit()

        if not session.exec(select(FlowScoutLinkModel).where(FlowScoutLinkModel.scout_node_id == scout_node.id)).first():
            session.delete(scout_node)
        if not session.exec(select(FlowModel).where(FlowModel.agent_node_id == agent_node.id)).first():
            session.delete(agent_node)
        for current_channel_node in channel_nodes:
            if not session.exec(
                select(FlowChannelLinkModel).where(FlowChannelLinkModel.channel_node_id == current_channel_node.id)
            ).first():
                session.delete(current_channel_node)

        session.commit()
        return {"deleted": True, "name": name}


def run_scout_workflow(scout_id: int) -> dict[str, Any]:
    manager = ScoutManager()
    try:
        with next(get_session()) as session:
            flow, scout_node, agent_node, channel_node = _get_flow_bundle(session, scout_id)
            scout_nodes = _get_flow_scout_nodes(session, [flow.id]).get(flow.id, [scout_node])
            channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])
            verifier_node, delivery_nodes = _split_delivery_nodes(channel_nodes)
            legacy_scout = manager.session.get(ScoutModel, flow.legacy_scout_id) if flow.legacy_scout_id else None
            if not legacy_scout:
                raise KeyError(f"Legacy scout for flow {scout_id} not found")
            _subscribe_rss_feeds_for_flow(legacy_scout.id, scout_nodes)
            agent_config = _safe_json_loads(agent_node.config_json, {})
            flow_policy = agent_config.get("flow_policy", "pool")

            items: list[ContentItem] = []
            flow_errors: list[dict[str, Any]] = []
            for current_scout_node in scout_nodes:
                runtime_name = f"{flow.name} / {current_scout_node.name}"
                _apply_runtime_scout_config(
                    legacy_scout,
                    flow.name,
                    current_scout_node,
                    agent_node,
                    delivery_nodes,
                    verifier_node,
                    runtime_name=runtime_name,
                )
                manager.session.add(legacy_scout)
                manager.session.commit()
                try:
                    scout_items = manager.run_scout(legacy_scout)
                except Exception as exc:
                    flow_errors.append(
                        {
                            "scout_node_id": current_scout_node.id,
                            "scout_node_name": current_scout_node.name,
                            "error": str(exc),
                        }
                    )
                    continue

                items.extend(
                    [
                        _tag_content_item_origin(item, current_scout_node)
                        for item in scout_items
                    ]
                )
                if flow_policy == "as_it_comes" and scout_items:
                    break

            if flow_errors and not items:
                raise RuntimeError(
                    "All scouts in this flow failed: "
                    + "; ".join(
                        f"{entry['scout_node_name']}: {entry['error']}" for entry in flow_errors
                    )
                )

            _apply_runtime_scout_config(
                legacy_scout,
                flow.name,
                scout_nodes[0],
                agent_node,
                delivery_nodes,
                verifier_node,
            )
            legacy_scout.last_run = datetime.utcnow()
            manager.session.add(legacy_scout)
            manager.session.commit()

            items = _dedupe_content_items(items)

        with next(get_session()) as session:
            flow, scout_node, agent_node, channel_node = _get_flow_bundle(session, scout_id)
            scout_nodes = _get_flow_scout_nodes(session, [flow.id]).get(flow.id, [scout_node])
            channel_nodes = _get_flow_channel_nodes(session, [flow.id]).get(flow.id, [channel_node])
            flow.updated_at = legacy_scout.last_run or datetime.utcnow()
            for current_scout_node in scout_nodes:
                current_scout_node.last_run = legacy_scout.last_run
                session.add(current_scout_node)
            session.add(flow)
            session.commit()

        if not items:
            return {
                "scout": _serialize_flow(flow, scout_nodes, agent_node, channel_nodes),
                "items_found": 0,
                "created_post": None,
                "created_posts": [],
                "source_failures": flow_errors,
            }

        created_posts: list[PostModel] = []
        if legacy_scout.intent == "scouting":
            content = manager.format_scouting_output(legacy_scout, items)
            delivery_platforms = sorted(
                {
                    platform
                    for current_channel_node in delivery_nodes
                    for platform in _safe_json_loads(current_channel_node.platforms, [])
                }
            ) or ["telegram"]
            if verifier_node:
                created_posts.append(
                    PostModel(
                        content=content,
                        platform=_safe_json_loads(verifier_node.platforms, ["telegram"])[0],
                        status="pending_review",
                        created_at=datetime.utcnow(),
                        scout_id=legacy_scout.id,
                        role="verification",
                        delivery_targets_json=json.dumps(delivery_platforms),
                    )
                )
            else:
                for platform in delivery_platforms:
                    created_posts.append(
                        PostModel(
                            content=content,
                            platform=platform,
                            status="pending_review",
                            created_at=datetime.utcnow(),
                            scout_id=legacy_scout.id,
                        )
                    )
        else:
            best_item = manager.select_best_content(items, legacy_scout)
            if best_item:
                platforms = _safe_json_loads(legacy_scout.platforms, [])
                draft = manager.generate_draft(legacy_scout, best_item)
                final_platforms = platforms or ["x"]
                if verifier_node:
                    created_posts.append(
                        PostModel(
                            content=draft,
                            platform=_safe_json_loads(verifier_node.platforms, ["telegram"])[0],
                            status="pending_review",
                            created_at=datetime.utcnow(),
                            scout_id=legacy_scout.id,
                            role="verification",
                            delivery_targets_json=json.dumps(final_platforms),
                        )
                    )
                else:
                    for platform in final_platforms:
                        created_posts.append(
                            PostModel(
                                content=draft,
                                platform=platform,
                                status="pending_review",
                                created_at=datetime.utcnow(),
                                scout_id=legacy_scout.id,
                            )
                        )

        if created_posts:
            for created_post in created_posts:
                manager.session.add(created_post)
            manager.session.commit()
            for created_post in created_posts:
                manager.session.refresh(created_post)

        return {
            "scout": _serialize_flow(flow, scout_nodes, agent_node, channel_nodes),
            "items_found": len(items),
            "created_post": serialize_post(created_posts[0], flow.name) if created_posts else None,
            "created_posts": [serialize_post(created_post, flow.name) for created_post in created_posts],
            "source_failures": flow_errors,
        }
    finally:
        manager.session.close()


def approve_post(post_id: int) -> dict[str, Any]:
    with next(get_session()) as session:
        post = session.get(PostModel, post_id)
        if not post:
            raise KeyError(f"Post {post_id} not found")

        payload: dict[str, Any] = {"message": "Post approved"}

        if post.role == "verification":
            post.status = "posted"
            post.posted_at = datetime.utcnow()
            delivery_targets = _safe_json_loads(post.delivery_targets_json, [])
            delivered_posts: list[PostModel] = []
            now = datetime.utcnow()

            for platform in delivery_targets:
                if platform == "telegram":
                    delivered_post = PostModel(
                        content=post.content,
                        platform=platform,
                        status="posted",
                        created_at=now,
                        posted_at=now,
                        scout_id=post.scout_id,
                    )
                elif platform == "x":
                    provider = XProvider()
                    if not provider.authenticate():
                        raise RuntimeError("X authentication failed")
                    delivered_post = PostModel(
                        content=post.content,
                        platform=platform,
                        status="posted",
                        external_id=provider.post(post.content),
                        created_at=now,
                        posted_at=now,
                        scout_id=post.scout_id,
                    )
                elif platform == "substack":
                    provider = SubstackProvider()
                    if not provider.authenticate():
                        raise RuntimeError("Substack authentication failed")
                    external_id = provider.post(post.content)
                    delivered_post = PostModel(
                        content=post.content,
                        platform=platform,
                        status="posted",
                        external_id=external_id,
                        created_at=now,
                        posted_at=now,
                        scout_id=post.scout_id,
                    )
                    payload["edit_url"] = (
                        f"https://{os.getenv('SUBSTACK_SUBDOMAIN')}.substack.com/publish/post/{external_id}"
                        if os.getenv("SUBSTACK_SUBDOMAIN")
                        else None
                    )
                else:
                    raise RuntimeError(f"Platform '{platform}' is not supported")

                session.add(delivered_post)
                delivered_posts.append(delivered_post)

            payload["message"] = (
                f"Verified and sent to {', '.join(delivery_targets)}"
                if delivery_targets
                else "Verification approved"
            )
            payload["posts"] = [serialize_post(item) for item in delivered_posts]
        elif post.platform == "telegram":
            post.status = "posted"
            post.posted_at = datetime.utcnow()
        elif post.platform == "x":
            provider = XProvider()
            if not provider.authenticate():
                raise RuntimeError("X authentication failed")
            post.external_id = provider.post(post.content)
            post.status = "posted"
            post.posted_at = datetime.utcnow()
            payload["message"] = "Posted to X"
        elif post.platform == "substack":
            provider = SubstackProvider()
            if not provider.authenticate():
                raise RuntimeError("Substack authentication failed")
            post.external_id = provider.post(post.content)
            post.status = "posted"
            post.posted_at = datetime.utcnow()
            payload["message"] = "Substack draft created"
            payload["edit_url"] = (
                f"https://{os.getenv('SUBSTACK_SUBDOMAIN')}.substack.com/publish/post/{post.external_id}"
                if os.getenv("SUBSTACK_SUBDOMAIN")
                else None
            )
        else:
            raise RuntimeError(f"Platform '{post.platform}' is not supported")

        session.add(post)
        session.commit()
        session.refresh(post)
        payload["post"] = serialize_post(post)
        return payload


def reject_post(post_id: int) -> dict[str, Any]:
    with next(get_session()) as session:
        post = session.get(PostModel, post_id)
        if not post:
            raise KeyError(f"Post {post_id} not found")

        post.status = "rejected"
        session.add(post)
        session.commit()
        session.refresh(post)
        return {
            "message": "Post rejected",
            "post": serialize_post(post),
        }


def refresh_rss_feed(feed_id: int) -> dict[str, Any]:
    manager = RSSManager()
    return manager.update_feed(feed_id)


def create_quick_post(
    content: str,
    platforms: list[str],
    review_before_publish: bool = False,
) -> dict[str, Any]:
    created_posts: list[dict[str, Any]] = []

    with next(get_session()) as session:
        for platform in platforms:
            if review_before_publish or platform == "telegram":
                db_post = PostModel(
                    content=content,
                    platform=platform,
                    status="pending_review",
                    created_at=datetime.utcnow(),
                )
                session.add(db_post)
                session.commit()
                session.refresh(db_post)
                created_posts.append(serialize_post(db_post))
                continue

            if platform == "x":
                provider = XProvider()
                if not provider.authenticate():
                    raise RuntimeError("X authentication failed")
                external_id = provider.post(content)
            elif platform == "substack":
                provider = SubstackProvider()
                if not provider.authenticate():
                    raise RuntimeError("Substack authentication failed")
                external_id = provider.post(content)
            else:
                raise RuntimeError(f"Unsupported platform '{platform}'")

            db_post = PostModel(
                content=content,
                platform=platform,
                status="posted",
                external_id=external_id,
                created_at=datetime.utcnow(),
                posted_at=datetime.utcnow(),
            )
            session.add(db_post)
            session.commit()
            session.refresh(db_post)
            created_posts.append(serialize_post(db_post))

    return {
        "message": "Post workflow completed",
        "posts": created_posts,
    }


def get_settings_snapshot() -> dict[str, Any]:
    config_manager = ConfigManager()
    config_manager.ensure_config_exists()
    env_loaded = _safe_load_settings_env()

    return {
        "config_file": str(CONFIG_FILE),
        "env_file": str(ENV_FILE),
        "storage": {
            "env_readable": env_loaded,
            "env_writable": _is_path_effectively_writable(ENV_FILE),
            "config_writable": _is_path_effectively_writable(CONFIG_FILE),
        },
        "ai": {
            "default_provider": config_manager.get("ai.default_provider", "gemini"),
            "gemini_model": config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash"),
            "gemini_models": get_gemini_models(),
            "gemini_connection_verified": bool(config_manager.get(GEMINI_VERIFIED_KEY, False)),
            "gemini_connection_verified_at": config_manager.get(GEMINI_VERIFIED_AT_KEY),
        },
        "embeddings": {
            "enabled": config_manager.get("embeddings.enabled", True),
            "model_name": config_manager.get("embeddings.model_name"),
        },
        "credentials": {
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "telegram": bool(os.getenv("TELEGRAM_BOT_TOKEN")) and bool(os.getenv("TELEGRAM_CHAT_ID")),
            "x": all(
                bool(os.getenv(key))
                for key in ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]
            ),
            "substack": all(
                bool(os.getenv(key))
                for key in ["SUBSTACK_SUBDOMAIN", "SUBSTACK_SID", "SUBSTACK_LLI"]
            ),
            "stability": bool(os.getenv("STABILITY_API_KEY")),
            "langfuse": all(
                bool(os.getenv(key))
                for key in ["LANGFUSE_HOST", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
            ),
        },
        "values": {
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID", ""),
            "substack_subdomain": os.getenv("SUBSTACK_SUBDOMAIN", ""),
            "langfuse_host": os.getenv("LANGFUSE_HOST", ""),
        },
    }


def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    config_manager = ConfigManager()
    config_manager.ensure_config_exists()
    _ensure_settings_storage_writable()
    ai = payload.get("ai", {})
    embeddings = payload.get("embeddings", {})
    credentials = payload.get("credentials", {})
    previous_model = str(config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash") or "").strip()
    previous_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()

    if "default_provider" in ai:
        config_manager.set("ai.default_provider", ai["default_provider"])
    if "gemini_model" in ai:
        config_manager.set("ai.providers.gemini.default_model", ai["gemini_model"])
    if "enabled" in embeddings:
        config_manager.set("embeddings.enabled", embeddings["enabled"])
    if "model_name" in embeddings:
        config_manager.set("embeddings.model_name", embeddings["model_name"] or None)

    env_mapping = {
        "gemini_api_key": "GEMINI_API_KEY",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
        "x_api_key": "X_API_KEY",
        "x_api_secret": "X_API_SECRET",
        "x_access_token": "X_ACCESS_TOKEN",
        "x_access_token_secret": "X_ACCESS_TOKEN_SECRET",
        "substack_subdomain": "SUBSTACK_SUBDOMAIN",
        "substack_sid": "SUBSTACK_SID",
        "substack_lli": "SUBSTACK_LLI",
        "stability_api_key": "STABILITY_API_KEY",
        "langfuse_host": "LANGFUSE_HOST",
        "langfuse_public_key": "LANGFUSE_PUBLIC_KEY",
        "langfuse_secret_key": "LANGFUSE_SECRET_KEY",
    }

    env_updates: dict[str, str] = {}
    for payload_key, env_key in env_mapping.items():
        if payload_key in credentials:
            value = credentials[payload_key] or ""
            env_updates[env_key] = value
            os.environ[env_key] = value

    if env_updates:
        _write_env_file_atomically(env_updates)

    _safe_load_settings_env()
    next_model = str(config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash") or "").strip()
    next_key = str(os.getenv("GEMINI_API_KEY", "") or "").strip()
    if previous_model != next_model or previous_key != next_key:
        _set_gemini_verification_state(config_manager, verified=False)
    return get_settings_snapshot()


def save_and_test_gemini_settings(payload: dict[str, Any]) -> dict[str, Any]:
    config_manager = ConfigManager()
    config_manager.ensure_config_exists()
    _ensure_settings_storage_writable()
    _safe_load_settings_env()

    ai = payload.get("ai", {})
    credentials = payload.get("credentials", {})

    next_model = (ai.get("gemini_model") or config_manager.get("ai.providers.gemini.default_model", "gemini-2.5-flash") or "").strip()
    next_api_key = (credentials.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "") or "").strip()

    if not next_api_key:
        raise RuntimeError("Add a Gemini API key before testing the connection.")
    if not next_model:
        raise RuntimeError("Choose a Gemini model before testing the connection.")

    try:
        available_models = _fetch_gemini_models_for_api_key(next_api_key)
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise RuntimeError(f"Gemini connection failed: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Gemini connection failed: {exc}") from exc

    if next_model not in available_models:
        available_models = _dedupe_keep_order(available_models + [next_model])

    try:
        provider = GeminiProvider(
            model_id=next_model,
            temperature=0,
            api_key=next_api_key,
        )
        provider.generate(
            "Reply with exactly OK. No punctuation, no explanation."
        )
    except Exception as exc:
        raise RuntimeError(
            "Gemini connection failed during a generation test. "
            f"Use a valid key and model combination. Details: {_friendly_gemini_error(exc)}"
        ) from exc

    config_manager.set("ai.default_provider", "gemini")
    config_manager.set("ai.providers.gemini.default_model", next_model)
    _set_gemini_verification_state(
        config_manager,
        verified=True,
        verified_at=datetime.utcnow().isoformat(),
    )
    _write_env_file_atomically({"GEMINI_API_KEY": next_api_key})
    os.environ["GEMINI_API_KEY"] = next_api_key
    _safe_load_settings_env()

    snapshot = get_settings_snapshot()
    snapshot["ai"]["gemini_models"] = available_models
    return {
        "message": f"Gemini connected. {len(available_models)} model IDs are available.",
        "settings": snapshot,
    }


def save_and_test_telegram_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_settings_storage_writable()
    _safe_load_settings_env()

    token = _effective_credential(payload, "telegram_bot_token", "TELEGRAM_BOT_TOKEN")
    chat_id = _effective_credential(payload, "telegram_chat_id", "TELEGRAM_CHAT_ID")

    if not token:
        raise RuntimeError("Add a Telegram bot token before testing the connection.")

    try:
        me_response = requests.get(
            f"https://api.telegram.org/bot{token}/getMe",
            timeout=15,
        )
        me_response.raise_for_status()
        me_payload = me_response.json()
        if not me_payload.get("ok"):
            raise RuntimeError(me_payload.get("description") or "Telegram bot validation failed.")

        if chat_id:
            chat_response = requests.get(
                f"https://api.telegram.org/bot{token}/getChat",
                params={"chat_id": chat_id},
                timeout=15,
            )
            chat_response.raise_for_status()
            chat_payload = chat_response.json()
            if not chat_payload.get("ok"):
                raise RuntimeError(chat_payload.get("description") or "Telegram chat validation failed.")
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise RuntimeError(f"Telegram connection failed: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Telegram connection failed: {exc}") from exc

    updates = {"TELEGRAM_BOT_TOKEN": token}
    if "telegram_chat_id" in payload or chat_id:
        updates["TELEGRAM_CHAT_ID"] = chat_id
    _persist_env_credentials(updates)

    snapshot = get_settings_snapshot()
    return {
        "message": "Telegram is connected and ready." if chat_id else "Telegram bot token is valid. Add a chat ID when you are ready to route drafts there.",
        "settings": snapshot,
    }


def save_and_test_x_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_settings_storage_writable()
    _safe_load_settings_env()

    api_key = _effective_credential(payload, "x_api_key", "X_API_KEY")
    api_secret = _effective_credential(payload, "x_api_secret", "X_API_SECRET")
    access_token = _effective_credential(payload, "x_access_token", "X_ACCESS_TOKEN")
    access_token_secret = _effective_credential(payload, "x_access_token_secret", "X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        raise RuntimeError("Add the full X credential set before testing the connection.")

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        response = client.get_me(user_fields=["username"])
        if response.data is None:
            raise RuntimeError("X credentials were accepted, but the account identity could not be fetched.")
    except Exception as exc:
        raise RuntimeError(f"X connection failed: {exc}") from exc

    _persist_env_credentials(
        {
            "X_API_KEY": api_key,
            "X_API_SECRET": api_secret,
            "X_ACCESS_TOKEN": access_token,
            "X_ACCESS_TOKEN_SECRET": access_token_secret,
        }
    )

    snapshot = get_settings_snapshot()
    username = getattr(response.data, "username", None)
    suffix = f" Connected to @{username}." if username else " X publishing is ready."
    return {
        "message": f"X credentials validated.{suffix}",
        "settings": snapshot,
    }


def save_and_test_substack_settings(payload: dict[str, Any]) -> dict[str, Any]:
    _ensure_settings_storage_writable()
    _safe_load_settings_env()

    subdomain = _effective_credential(payload, "substack_subdomain", "SUBSTACK_SUBDOMAIN")
    sid = _effective_credential(payload, "substack_sid", "SUBSTACK_SID")
    lli = _effective_credential(payload, "substack_lli", "SUBSTACK_LLI")

    if not all([subdomain, sid, lli]):
        raise RuntimeError("Add the Substack subdomain, sid, and lli before testing the connection.")

    try:
        auth = SubstackAuth(cookies_dict={"sid": sid, "lli": lli})
        response = auth.get(f"https://{subdomain}.substack.com/api/v1/publication", timeout=30)
        response.raise_for_status()
        publication = response.json()
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        raise RuntimeError(f"Substack connection failed: {detail}") from exc
    except Exception as exc:
        raise RuntimeError(f"Substack connection failed: {exc}") from exc

    _persist_env_credentials(
        {
            "SUBSTACK_SUBDOMAIN": subdomain,
            "SUBSTACK_SID": sid,
            "SUBSTACK_LLI": lli,
        }
    )

    snapshot = get_settings_snapshot()
    publication_name = publication.get("name") or subdomain
    return {
        "message": f"Substack connected to {publication_name}.",
        "settings": snapshot,
    }


def get_saved_gemini_key() -> dict[str, str]:
    _safe_load_settings_env()
    return {"value": os.getenv("GEMINI_API_KEY", "")}


def get_logs(lines: int = 100) -> dict[str, Any]:
    app_log = LOGS_DIR / "app" / "app.log"
    bot_log = ENV_FILE.parent / "bot-service.log"

    def read_tail(path: str) -> list[str]:
        file_path = os.path.expanduser(path)
        target = os.path.abspath(file_path)
        if not os.path.exists(target):
            return []
        with open(target, "r", encoding="utf-8") as handle:
            return [line.rstrip("\n") for line in handle.readlines()[-lines:]]

    return {
        "app": read_tail(str(app_log)),
        "bot": read_tail(str(bot_log)),
    }


def get_gemini_models() -> list[str]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return CURATED_GEMINI_MODELS.copy()

    try:
        return _fetch_gemini_models_for_api_key(api_key)
    except Exception:
        return CURATED_GEMINI_MODELS.copy()
