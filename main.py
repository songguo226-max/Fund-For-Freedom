from __future__ import annotations

import os
import signal
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


def _cmd_text(cmd: list[str]) -> str:
    return " ".join(cmd)


def _run_step(name: str, cmd: list[str], cwd: Path) -> None:
    print(f"[setup] {name}: {_cmd_text(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def _start(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen:
    print(f"[start] {name}: {_cmd_text(cmd)}", flush=True)
    return subprocess.Popen(cmd, cwd=cwd)


def _run_backend() -> None:
    os.chdir(BACKEND)
    sys.path.insert(0, str(BACKEND))
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=int(BACKEND_PORT))


def _start_backend() -> BaseProcess:
    print(f"[start] backend: uvicorn app.main:app --host 127.0.0.1 --port {BACKEND_PORT}", flush=True)
    proc = get_context("spawn").Process(target=_run_backend, name="fund-backend")
    proc.start()
    return proc


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

    backend = None
    frontend = None
    try:
        backend = _start_backend()
        frontend = _start(
            "frontend",
            [NPM, "run", "dev", "--", "--host", "127.0.0.1", "--port", FRONTEND_PORT],
            FRONTEND,
        )
    except Exception:
        if frontend is not None:
            _stop_process_tree(frontend, "frontend")
        if backend is not None:
            _stop_backend(backend)
        raise

    print("\n应用已启动：", flush=True)
    print(f"  前端: http://127.0.0.1:{FRONTEND_PORT}", flush=True)
    print(f"  后端: http://127.0.0.1:{BACKEND_PORT}/api/v1/health", flush=True)
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
