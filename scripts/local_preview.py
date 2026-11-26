"""Start/stop the prepared Windows preview. Never installs software or resets data."""

import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"
STATE = LOCAL / "preview-processes.json"
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def short_path(path):
    buffer = ctypes.create_unicode_buffer(32768)
    if not ctypes.windll.kernel32.GetShortPathNameW(str(path), buffer, len(buffer)):
        raise RuntimeError("Cannot resolve the local PostgreSQL path")
    return Path(buffer.value)


def started_at(pid):
    """Process creation time prevents stopping an unrelated process after PID reuse."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [
        ctypes.POINTER(wintypes.FILETIME)
    ] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *(ctypes.byref(v) for v in values)):
            return None
        return (values[0].dwHighDateTime << 32) | values[0].dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def port_open(port):
    with socket.socket() as connection:
        connection.settimeout(0.3)
        return connection.connect_ex(("127.0.0.1", port)) == 0


def stop():
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    for name in ("web", "api"):
        saved = state.get(name)
        if (
            saved
            and saved.get("created")
            and started_at(saved["pid"]) == saved["created"]
        ):
            subprocess.run(
                ["taskkill", "/PID", str(saved["pid"]), "/T", "/F"],
                creationflags=FLAGS,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    if state.get("database"):
        pg = short_path(LOCAL / "pgsql/bin/pg_ctl.exe")
        data = short_path(LOCAL / "pgdata")
        subprocess.run(
            [str(pg), "-D", str(data), "-m", "fast", "-w", "stop"],
            creationflags=FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    STATE.unlink(missing_ok=True)
    print("Preview stopped. Database files are preserved.")


def start():
    if STATE.exists():
        state = json.loads(STATE.read_text())
        if all(
            state.get(n)
            and state[n].get("created")
            and started_at(state[n]["pid"]) == state[n]["created"]
            for n in ("web", "api")
        ):
            print("Already running: http://127.0.0.1:3000")
            return
        stop()
    for port in (3000, 8000, 55432):
        if port_open(port):
            raise RuntimeError(
                f"Port {port} is occupied. No existing process was stopped."
            )
    config_path = LOCAL / "runtime.json"
    if not config_path.exists():
        raise RuntimeError(
            "This local preview has not been prepared. Follow FORDEV.md for normal setup."
        )
    runtime = json.loads(config_path.read_text(encoding="utf-8"))
    python = ROOT / ".venv/Scripts/python.exe"
    node = Path(runtime["node"])
    for path in (
        python,
        node,
        LOCAL / "pgsql/bin/postgres.exe",
        LOCAL / "pgdata/PG_VERSION",
        ROOT / "frontend/node_modules/vite/bin/vite.js",
        LOCAL / "pg-password",
    ):
        if not path.is_file():
            raise RuntimeError(
                f"Missing preview dependency: {path.name}. See FORDEV.md."
            )
    password = (LOCAL / "pg-password").read_text().strip()
    env = {
        **os.environ,
        "PYTHONUTF8": "1",
        "TEMP": str(LOCAL / "tmp"),
        "TMP": str(LOCAL / "tmp"),
        "DATABASE_URL": f"postgresql+psycopg://mai:{password}@127.0.0.1:55432/mai_dev",
    }
    state = {}

    def save():
        STATE.write_text(json.dumps(state), encoding="utf-8")

    def launch(name, args, cwd):
        with (LOCAL / f"{name}-stdout.log").open("w") as out, (
            LOCAL / f"{name}-stderr.log"
        ).open("w") as err:
            process = subprocess.Popen(
                args, cwd=cwd, env=env, stdout=out, stderr=err, creationflags=FLAGS
            )
        state[name] = {"pid": process.pid, "created": started_at(process.pid)}
        save()
        return process

    try:
        pg_root = short_path(LOCAL)
        pg = launch(
            "pg",
            [str(pg_root / "pgsql/bin/postgres.exe"), "-D", str(pg_root / "pgdata")],
            pg_root,
        )
        state["database"] = True
        save()
        import psycopg

        for _ in range(50):
            if pg.poll() is not None:
                raise RuntimeError("PostgreSQL did not start. See .local/pg-stderr.log")
            try:
                with psycopg.connect(
                    env["DATABASE_URL"].replace(
                        "postgresql+psycopg://", "postgresql://"
                    ),
                    connect_timeout=1,
                ):
                    break
            except psycopg.OperationalError:
                time.sleep(0.2)
        else:
            raise RuntimeError("PostgreSQL is not ready")
        subprocess.run(
            [str(python), "-m", "app.migrate"],
            cwd=ROOT / "backend",
            env=env,
            creationflags=FLAGS,
            check=True,
        )
        launch(
            "api",
            [
                str(python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ROOT / "backend",
        )
        launch(
            "web",
            [
                str(node),
                str(ROOT / "frontend/node_modules/vite/bin/vite.js"),
                "--host",
                "127.0.0.1",
                "--port",
                "3000",
            ],
            ROOT / "frontend",
        )
        for _ in range(50):
            try:
                for url in ("http://127.0.0.1:8000/health", "http://127.0.0.1:3000"):
                    with urllib.request.urlopen(url, timeout=1) as response:
                        if response.status != 200:
                            raise OSError("Not ready")
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("Preview is not ready. Inspect .local/*-stderr.log")
        print("Ready: http://127.0.0.1:3000")
        print("To stop, run STOP.cmd. No system service was installed.")
    except Exception:
        stop()
        raise


if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit(
            "Prepared preview is for Windows. See FORDEV.md for other systems."
        )
    try:
        if sys.argv[1:] == ["start"]:
            start()
        elif sys.argv[1:] == ["stop"]:
            stop()
        else:
            raise RuntimeError("Usage: local_preview.py start|stop")
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
