from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from influencerpy.database import create_db_and_tables
from influencerpy.web.runtime import is_bot_running, start_bot_process, stop_bot_process
from influencerpy.web.services import (
    approve_post,
    create_quick_post,
    create_scout,
    create_scout_node,
    delete_scout_record,
    generate_flow_suggestion,
    get_dashboard_snapshot,
    get_logs,
    get_scout_builder_snapshot,
    get_settings_snapshot,
    preview_scout_node,
    list_posts,
    list_scouts,
    refresh_rss_feed,
    reject_post,
    run_scout_workflow,
    search_posts,
    update_scout_node,
    update_scout_record,
    save_and_test_gemini_settings,
    update_settings,
)

app = FastAPI(title="InfluencerPy Dashboard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict:
    return get_dashboard_snapshot()


@app.get("/api/scouts")
def scouts() -> list[dict]:
    return list_scouts()


@app.get("/api/scout-builder")
def scout_builder() -> dict:
    return get_scout_builder_snapshot()


@app.post("/api/flow-suggestions")
def flow_suggestions(payload: dict) -> dict:
    try:
        return generate_flow_suggestion(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scout-nodes")
def create_scout_node_endpoint(payload: dict) -> dict:
    try:
        return create_scout_node(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/scout-nodes/{node_id}")
def update_scout_node_endpoint(node_id: int, payload: dict) -> dict:
    try:
        return update_scout_node(node_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scout-nodes/preview")
def preview_scout_node_endpoint(payload: dict) -> dict:
    try:
        return preview_scout_node(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scouts")
def create_scout_endpoint(payload: dict) -> dict:
    try:
        return create_scout(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.put("/api/scouts/{scout_id}")
def update_scout_endpoint(scout_id: int, payload: dict) -> dict:
    try:
        return update_scout_record(scout_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.delete("/api/scouts/{scout_id}")
def delete_scout_endpoint(scout_id: int) -> dict:
    try:
        return delete_scout_record(scout_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/scouts/{scout_id}/run")
def run_scout(scout_id: int) -> dict:
    try:
        return run_scout_workflow(scout_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/posts")
def posts(status: str | None = None, limit: int = 25, q: str = "") -> list[dict]:
    if q:
        return search_posts(query=q, status=status, limit=limit)
    return list_posts(status=status, limit=limit)


@app.post("/api/posts/quick")
def quick_post(payload: dict) -> dict:
    try:
        return create_quick_post(
            content=payload.get("content", ""),
            platforms=payload.get("platforms", []),
            review_before_publish=payload.get("review_before_publish", False),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/posts/{post_id}/approve")
def approve(post_id: int) -> dict:
    try:
        return approve_post(post_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/posts/{post_id}/reject")
def reject(post_id: int) -> dict:
    try:
        return reject_post(post_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/system")
def system_status() -> dict[str, bool]:
    return {"bot_running": is_bot_running()}


@app.post("/api/system/start")
def start_system() -> dict[str, bool]:
    return {"started": start_bot_process(), "bot_running": is_bot_running()}


@app.post("/api/system/stop")
def stop_system() -> dict[str, bool]:
    return {"stopped": stop_bot_process(), "bot_running": is_bot_running()}


@app.post("/api/rss/{feed_id}/refresh")
def refresh_feed(feed_id: int) -> dict:
    return refresh_rss_feed(feed_id)


@app.get("/api/settings")
def settings() -> dict:
    return get_settings_snapshot()


@app.put("/api/settings")
def save_settings(payload: dict) -> dict:
    try:
        return update_settings(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/settings/gemini/test")
def save_and_test_gemini(payload: dict) -> dict:
    try:
        return save_and_test_gemini_settings(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/logs")
def logs(lines: int = 100) -> dict:
    return get_logs(lines=lines)
