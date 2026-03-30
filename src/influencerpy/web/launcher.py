import os
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

from influencerpy.config import PROJECT_ROOT


def _resolve_project_root() -> Path:
    override = os.getenv("INFLUENCERPY_PROJECT_ROOT")
    if override:
        candidate = Path(override).expanduser().resolve()
        if (candidate / "frontend").exists():
            return candidate

    cwd = Path.cwd().resolve()
    if (cwd / "frontend").exists():
        return cwd

    if (PROJECT_ROOT / "frontend").exists():
        return PROJECT_ROOT

    for parent in Path(__file__).resolve().parents:
        if (parent / "frontend").exists():
            return parent

    return PROJECT_ROOT


def _frontend_dir() -> Path:
    return _resolve_project_root() / "frontend"


def _wait_for_frontend_dependencies() -> None:
    frontend_dir = _frontend_dir()
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        return

    subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)


def _ensure_frontend_build(env: dict[str, str]) -> None:
    frontend_dir = _frontend_dir()
    build_id = frontend_dir / ".next" / "BUILD_ID"
    standalone_output = frontend_dir / ".next" / "standalone"

    # Installed/containerized deployments often ship with a prebuilt Next app.
    # Reusing that build avoids runtime writes into mounted source directories.
    if build_id.exists() or standalone_output.exists():
        return

    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, env=env, check=True)


def _is_port_available(host: str, port: int) -> bool:
    for probe_host in {host, "127.0.0.1", "::1"}:
        family = socket.AF_INET6 if ":" in probe_host else socket.AF_INET
        with socket.socket(family, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                if sock.connect_ex((probe_host, port)) == 0:
                    return False
            except OSError:
                continue

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _find_available_port(host: str, preferred_port: int, max_attempts: int = 20) -> int:
    for offset in range(max_attempts):
        candidate = preferred_port + offset
        if _is_port_available(host, candidate):
            return candidate
    raise RuntimeError(
        f"Could not find a free port starting at {preferred_port} on {host}."
    )


def _wait_for_http_ready(url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.0) as response:
                if 200 <= response.status < 500:
                    return
        except HTTPError as exc:
            if 200 <= exc.code < 500:
                return
            time.sleep(0.2)
        except Exception:
            time.sleep(0.2)

    raise RuntimeError(f"Timed out waiting for service at {url}")


def launch_dashboard_stack(
    backend_host: str = "127.0.0.1",
    backend_port: int = 8000,
    frontend_port: int = 3000,
    open_browser: bool = True,
) -> None:
    """Launch the dashboard backend and frontend together."""
    project_root = _resolve_project_root()
    _wait_for_frontend_dependencies()

    backend_port = _find_available_port(backend_host, backend_port)
    frontend_port = _find_available_port("127.0.0.1", frontend_port)

    api_url = f"http://{backend_host}:{backend_port}"
    api_connect_host = "127.0.0.1" if backend_host == "0.0.0.0" else backend_host
    api_connect_url = f"http://{api_connect_host}:{backend_port}"
    frontend_url = f"http://127.0.0.1:{frontend_port}"

    print(f"Starting dashboard API on {api_url}")
    print(f"Starting dashboard UI on {frontend_url}")

    backend_process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "influencerpy.web.api:app",
            "--host",
            backend_host,
            "--port",
            str(backend_port),
        ],
        cwd=project_root,
        env=os.environ.copy(),
    )

    _wait_for_http_ready(f"{api_connect_url}/api/health", timeout_seconds=45.0)

    frontend_env = os.environ.copy()
    frontend_env["NEXT_PUBLIC_API_BASE_URL"] = f"{api_connect_url}/api"
    frontend_env["INFLUENCERPY_API_BASE_URL"] = f"{api_connect_url}/api"
    frontend_env["PORT"] = str(frontend_port)

    _ensure_frontend_build(frontend_env)

    frontend_process = subprocess.Popen(
        ["npm", "run", "start"],
        cwd=_frontend_dir(),
        env=frontend_env,
    )

    _wait_for_http_ready(frontend_url, timeout_seconds=60.0)

    if open_browser:
        webbrowser.open(frontend_url)

    try:
        while True:
            if backend_process.poll() is not None:
                raise RuntimeError(
                    f"Dashboard backend stopped unexpectedly. Intended URL: {api_url}"
                )
            if frontend_process.poll() is not None:
                raise RuntimeError(
                    f"Dashboard frontend stopped unexpectedly. Intended URL: {frontend_url}"
                )
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in (frontend_process, backend_process):
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in (frontend_process, backend_process):
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
