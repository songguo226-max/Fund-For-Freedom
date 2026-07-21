from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from multiprocessing import get_context
from multiprocessing.process import BaseProcess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
NPM = "npm.cmd" if os.name == "nt" else "npm"
BACKEND_PORT = "8010"
FRONTEND_PORT = "5173"
HOST = "127.0.0.1"


def _cmd_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def _run_step(name: str, cmd: list[str], cwd: Path) -> None:
    print(f"[setup] {name}: {_cmd_text(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def _port_is_open(port: str) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((HOST, int(port))) == 0


def _assert_port_available(port: str, label: str) -> None:
    if _port_is_open(port):
        raise RuntimeError(
            f"{label} port {port} is already in use. "
            f"Stop the existing service on http://{HOST}:{port} and run this command again."
        )


def _start(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen:
    print(f"[start] {name}: {_cmd_text(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=cwd)


def _run_backend() -> None:
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    import uvicorn

    uvicorn.run("app.main:app", host=HOST, port=int(BACKEND_PORT))


def _start_backend() -> BaseProcess:
    print(f"[start] backend: uvicorn app.main:app --host {HOST} --port {BACKEND_PORT}", flush=True)
    proc = get_context("spawn").Process(target=_run_backend, name="fund-backend")
    proc.start()
    return proc


def _wait_for_backend(proc: BaseProcess, timeout_seconds: float = 12.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if not proc.is_alive():
            raise RuntimeError(f"Backend failed to start; process exited with code {proc.exitcode}.")
        if _port_is_open(BACKEND_PORT):
            return
        time.sleep(0.2)
    raise RuntimeError(f"Backend did not become ready on http://{HOST}:{BACKEND_PORT}.")


def _stop_backend(proc: BaseProcess) -> None:
    if not proc.is_alive():
        return
    print("[stop] backend", flush=True)
    proc.terminate()
    proc.join(timeout=8)
    if proc.is_alive():
        proc.kill()
        proc.join(timeout=2)


def _stop_process_tree(proc: subprocess.Popen, name: str) -> None:
    if proc.poll() is not None:
        return
    print(f"[stop] {name}", flush=True)
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def _ensure_frontend_deps() -> None:
    if not (FRONTEND / "node_modules").exists():
        _run_step("install frontend dependencies", [NPM, "install"], FRONTEND)


def main() -> int:
    if not FRONTEND.exists():
        print("[error] frontend/ 不存在，请先完成前端初始化。", file=sys.stderr)
        return 1

    _ensure_frontend_deps()
    try:
        _assert_port_available(BACKEND_PORT, "Backend")
        _assert_port_available(FRONTEND_PORT, "Frontend")
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr, flush=True)
        return 1

    backend = None
    frontend = None
    try:
        backend = _start_backend()
        _wait_for_backend(backend)
        frontend = _start(
            "frontend",
            [NPM, "run", "dev", "--", "--host", HOST, "--port", FRONTEND_PORT, "--strictPort"],
            FRONTEND,
        )
    except Exception:
        if frontend is not None:
            _stop_process_tree(frontend, "frontend")
        if backend is not None:
            _stop_backend(backend)
        raise

    print("\n应用已启动：", flush=True)
    print(f"  前端: http://{HOST}:{FRONTEND_PORT}", flush=True)
    print(f"  后端: http://{HOST}:{BACKEND_PORT}/api/v1/health", flush=True)
    print("\n按 Ctrl+C 停止前后端。\n", flush=True)

    try:
        while True:
            frontend_code = frontend.poll()
            if frontend_code is not None:
                print(f"[exit] frontend exited with code {frontend_code}", flush=True)
                return frontend_code or 0
            if not backend.is_alive():
                print(f"[exit] backend exited with code {backend.exitcode}", flush=True)
                return backend.exitcode or 0
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n收到 Ctrl+C，正在停止服务...", flush=True)
        return 0
    finally:
        _stop_process_tree(frontend, "frontend")
        _stop_backend(backend)


if __name__ == "__main__":
    raise SystemExit(main())
