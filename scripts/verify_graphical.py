#!/usr/bin/env python3
"""Validate the real graphical suite on isolated Xvfb and record scoped memory."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import select
import shutil
import signal
import socket
import statistics
import struct
import subprocess
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]

def run(argv, env, cwd=None, check=True, timeout=20):
    return subprocess.run([str(value) for value in argv], env=env, cwd=cwd,
                          capture_output=True, text=True, check=check, timeout=timeout)

def wait_until(probe, seconds=10):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        result = probe()
        if result:
            return result
        time.sleep(0.02)
    raise RuntimeError("readiness deadline expired")

def process_identity(pid):
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return fields[19]
    except FileNotFoundError:
        return None

def memory(pid):
    values = {}
    for line in Path(f"/proc/{pid}/smaps_rollup").read_text().splitlines():
        fields = line.split()
        if fields and fields[0].rstrip(":") in ["Rss", "Pss", "Private_Clean", "Private_Dirty", "Shared_Clean", "Shared_Dirty"]:
            values[fields[0].rstrip(":") + "_KiB"] = int(fields[1])
    return values

def cache_snapshot(directory):
    return {path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "mtime_ns": path.stat().st_mtime_ns}
            for path in sorted(directory.glob("zcompdump-*")) if path.is_file()}

def find_session(value):
    if isinstance(value, dict):
        if "broker_pid" in value and "pid" in value and value.get("name") == "oh-my-ztty-verify":
            return value
        for item in value.values():
            result = find_session(item)
            if result:
                return result
    if isinstance(value, list):
        for item in value:
            result = find_session(item)
            if result:
                return result
    return None

def peer_pid(address):
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as stream:
            stream.settimeout(0.5)
            stream.connect("\0" + address[1:])
            pid, uid, _ = struct.unpack("3i", stream.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid == os.getuid():
                return pid
    except OSError:
        return None

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/reports")
    parser.add_argument("--samples", type=int, default=40)
    args = parser.parse_args()
    for tool in ["Xvfb", "xdotool", "import", "zsh"]:
        if not shutil.which(tool):
            raise SystemExit(f"required graphical-test tool missing: {tool}")
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.archive.resolve()
    with tarfile.open(archive) as tar:
        build = json.load(tar.extractfile("oh-my-ztty/BUILD.json"))
        preset_lines = tar.extractfile("oh-my-ztty/config/ztty/config").read().decode().splitlines()
        preset = {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip() for line in preset_lines if "=" in line and not line.lstrip().startswith("#")}
    report = {
        "schema": "oh-my-ztty.graphical.v1",
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "build": build,
        "scope": "One actual suite window on an isolated Xvfb display, 100x28 cells, preset font and padding, temporary Git checkout. X server excluded from application memory. No AI connection.",
        "preset": {"font_pattern": preset["font"], "padding_px": int(preset["window-padding"])},
        "kernel": os.uname().release,
        "architecture": os.uname().machine,
    }
    with tempfile.TemporaryDirectory(prefix="oh-my-ztty-gui-") as temporary:
        temp = Path(temporary)
        home = temp / "home"
        demo = home / "work/oh-my-ztty"
        demo.mkdir(parents=True)
        runtime = temp / "runtime"
        runtime.mkdir(mode=0o700)
        env = {key: value for key, value in os.environ.items() if not key.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR", "ZTTY_")) and key not in ["DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY"]}
        address = "@oh-my-ztty-test-" + uuid.uuid4().hex
        env.update(HOME=str(home), XDG_DATA_HOME=str(home / ".local/share"),
                   XDG_CONFIG_HOME=str(home / ".config"), XDG_CACHE_HOME=str(home / ".cache"),
                   XDG_STATE_HOME=str(home / ".local/state"), XDG_RUNTIME_DIR=str(runtime),
                   OMZTTY_SOCKET=address, ZTTY_SOCKET=address, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
        run(["git", "-c", "init.defaultBranch=main", "init", "--quiet", demo], env)
        run(["git", "-C", demo, "-c", "user.name=oh-my-ztty", "-c", "user.email=preview@example.invalid", "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "Preview workspace"], env)
        if shutil.which("fc-match"):
            report["preset"]["resolved_font_family"] = run(["fc-match", "--format", "%{family}", preset["font"]], env).stdout
        run(["sh", ROOT / "install.sh", "--from", archive, "--no-memory-manager"], env)
        cli = home / ".local/bin/omztty"
        release_id = cli.resolve().parents[1].name
        cache_dir = home / ".cache/oh-my-ztty/zshard" / release_id
        prepared_cache = cache_snapshot(cache_dir)
        if not prepared_cache:
            raise RuntimeError("installer did not prepare its completion dump")
        source = home / "verify.zsh"
        source.write_text(
            'ztty --version > "$HOME/component-versions"\n'
            'zdot --version >> "$HOME/component-versions"\n'
            'ssmcp --version >> "$HOME/component-versions"\n'
            'zfetch --version >> "$HOME/component-versions"\n'
            'print -r -- ready > "$HOME/gui-ready"\n'
        )
        xvfb = subprocess.Popen(["Xvfb", "-displayfd", "1", "-screen", "0", "1600x1000x24", "-nolisten", "tcp"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        launcher = None
        broker_pid = None
        owned = {}
        try:
            if not select.select([xvfb.stdout], [], [], 10)[0]:
                raise RuntimeError("Xvfb did not provide a display")
            number = xvfb.stdout.readline().strip()
            if not number.isdigit():
                raise RuntimeError("Xvfb returned an invalid display")
            env["DISPLAY"] = ":" + number
            start = time.perf_counter_ns()
            launcher = subprocess.Popen([str(cli), "terminal", "--name", "oh-my-ztty-verify", "--geometry", "100x28"],
                                        env=env, cwd=demo, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            owned[launcher.pid] = process_identity(launcher.pid)
            def window():
                result = run(["xdotool", "search", "--onlyvisible", "--class", "ztty"], env, check=False)
                return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None
            window_id = wait_until(window)
            report["window_visible_ms"] = (time.perf_counter_ns() - start) / 1_000_000
            status = json.loads(run([cli, "ztty", "info", "oh-my-ztty-verify"], env).stdout)
            session = find_session(status)
            if session is None:
                raise RuntimeError("ztty did not return the owned session metadata")
            broker_pid = int(session["broker_pid"])
            shell_pid = int(session["pid"])
            if broker_pid != peer_pid(address):
                raise RuntimeError("broker identity does not match the isolated socket")
            for pid in [broker_pid, shell_pid]:
                owned[pid] = process_identity(pid)
            run(["xdotool", "windowfocus", "--sync", window_id], env)
            run(["xdotool", "type", "--clearmodifiers", "--window", window_id, "--delay", "0", 'source "$HOME/verify.zsh"'], env)
            run(["xdotool", "key", "--window", window_id, "Return"], env)
            wait_until(lambda: (home / "gui-ready").exists())
            time.sleep(0.2)
            report["geometry"] = {"cols": session["cols"], "rows": session["rows"]}
            if report["geometry"] != {"cols": 100, "rows": 28}:
                raise RuntimeError("terminal PTY does not match the requested 100x28 grid")
            report["before_completion"] = {"ztty_broker": memory(broker_pid), "zsh": memory(shell_pid), "waiting_launcher": memory(launcher.pid)}
            run(["xdotool", "type", "--window", window_id, "--delay", "0", "omztty "], env)
            run(["xdotool", "key", "--window", window_id, "Tab"], env)
            time.sleep(0.6)
            run(["xdotool", "key", "--window", window_id, "ctrl+c"], env)
            run(["xdotool", "type", "--window", window_id, "--delay", "0", 'print -r -- ready > "$HOME/tab-ready"'], env)
            run(["xdotool", "key", "--window", window_id, "Return"], env)
            wait_until(lambda: (home / "tab-ready").exists())
            time.sleep(0.2)
            report["after_completion"] = {"ztty_broker": memory(broker_pid), "zsh": memory(shell_pid), "waiting_launcher": memory(launcher.pid)}
            used_cache = cache_snapshot(cache_dir)
            report["completion_cache"] = {"prepared": prepared_cache, "after_first_tab": used_cache, "reused": prepared_cache == used_cache}
            if prepared_cache != used_cache:
                raise RuntimeError("first Tab rebuilt the prepared completion dump: " + json.dumps(report["completion_cache"]))
            (home / "gui-ready").unlink()
            run(["xdotool", "type", "--window", window_id, "--delay", "0", 'source "$HOME/verify.zsh"'], env)
            run(["xdotool", "key", "--window", window_id, "Return"], env)
            wait_until(lambda: (home / "gui-ready").exists())
            report["component_versions"] = (home / "component-versions").read_text().splitlines()
            run(["xdotool", "key", "--window", window_id, "ctrl+l"], env)
            for command in ["omztty version", "git status --short --branch"]:
                run(["xdotool", "type", "--window", window_id, "--delay", "0", command], env)
                run(["xdotool", "key", "--window", window_id, "Return"], env)
                time.sleep(0.2)
            screenshot = args.output / f"linux-{os.uname().machine}-terminal.png"
            run(["import", "-window", window_id, screenshot], env)
            report["screenshot"] = screenshot.name
            report["graphical_checks"] = ["visible window", "keyboard command executed in preset zsh", "first completion returned to a usable shell", "actual component versions verified"]
            run(["xdotool", "key", "--window", window_id, "ctrl+l"], env)
            run(["xdotool", "type", "--window", window_id, "--delay", "0",
                 'omztty info --boot && print -r -- ready > "$HOME/boot-ready"'], env)
            run(["xdotool", "key", "--window", window_id, "Return"], env)
            wait_until(lambda: (home / "boot-ready").exists())
            boot = json.loads(run([cli, "info", "--boot", "--json"], env).stdout)
            if boot.get("schema") != "zfetch.boot.v1" or len(boot.get("stages", [])) != 9:
                raise RuntimeError("installed zfetch did not return the complete boot structure")
            boot_screenshot = args.output / f"linux-{os.uname().machine}-boot.png"
            run(["import", "-window", window_id, boot_screenshot], env)
            report["boot"] = {"schema": boot["schema"], "stages": len(boot["stages"]),
                              "screenshot": boot_screenshot.name}
            report["graphical_checks"].append("boot-chain command executed in the preset zsh")
            run([cli, "ztty", "close", "oh-my-ztty-verify"], env)
            launcher.wait(timeout=5)
        finally:
            if broker_pid is None:
                broker_pid = peer_pid(address)
                if broker_pid:
                    owned[broker_pid] = process_identity(broker_pid)
            for pid, identity in owned.items():
                if identity is not None and process_identity(pid) == identity:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
            if launcher is not None:
                try:
                    launcher.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    launcher.kill()
                    launcher.wait()
            xvfb.terminate()
            try:
                xvfb.wait(timeout=5)
            except subprocess.TimeoutExpired:
                xvfb.kill()
                xvfb.wait()
        live = []
        for pid, identity in owned.items():
            if identity is not None and process_identity(pid) == identity:
                fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
                if fields[0] != "Z":
                    live.append(pid)
        if live:
            raise RuntimeError("owned application process remained after cleanup")
        report["cleanup"] = "All owned application processes and Xvfb stopped; temporary HOME removed."
        cases = {"vanilla_zsh": ["zsh", "-df", "-ic", "exit"], "suite_shell": [str(cli), "shell", "-ic", "exit"]}
        for command in cases.values():
            for _ in range(5):
                run(command, env, cwd=demo)
        samples = {name: [] for name in cases}
        order = list(cases) * args.samples
        random.Random(0).shuffle(order)
        for name in order:
            start = time.perf_counter_ns()
            run(cases[name], env, cwd=demo)
            samples[name].append((time.perf_counter_ns() - start) / 1_000_000)
        report["startup"] = {
            "definition": "Warm process wall time for an interactive zsh -c exit. Suite includes launcher and preset initialization; no prompt, Tab, model or network call. Vanilla disables user/global rc and is a minimum-feature baseline.",
            "samples_per_case": args.samples,
            "results": {name: {"median_ms": statistics.median(values), "p95_ms": sorted(values)[int(0.95 * (len(values) - 1))], "min_ms": min(values), "raw_ms": values} for name, values in samples.items()},
        }
        run([cli, "uninstall"], env)
    output = args.output / f"linux-{os.uname().machine}-suite.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "startup"}, indent=2))
    print(json.dumps({name: {key: value for key, value in data.items() if key != "raw_ms"} for name, data in report["startup"]["results"].items()}, indent=2))
    print("report:", output)

if __name__ == "__main__":
    main()
