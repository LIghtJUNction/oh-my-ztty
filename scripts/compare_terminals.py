#!/usr/bin/env python3
"""Measure scoped idle PSS on private Xvfb; this is not a native GPU ranking."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import select
import signal
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_graphical import memory, peer_pid, process_identity, run, wait_until


def descendants(pid):
    result, pending = set(), [pid]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.add(current)
        try:
            pending.extend(map(int, Path(f"/proc/{current}/task/{current}/children").read_text().split()))
        except FileNotFoundError:
            pass
    return result


def alive(pid, identity):
    if identity is None or process_identity(pid) != identity:
        return False
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0] != "Z"
    except FileNotFoundError:
        return False


def stop(owned):
    for signum in (signal.SIGTERM, signal.SIGKILL):
        for pid, identity in owned.items():
            if alive(pid, identity):
                try:
                    os.kill(pid, signum)
                except ProcessLookupError:
                    pass
        time.sleep(0.15)
    return [pid for pid, identity in owned.items() if alive(pid, identity)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / ".cache/comparison/linux-x86_64-terminal-comparison.json")
    args = parser.parse_args()
    archive = args.archive.resolve()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    logs = ROOT / ".cache/comparison"
    logs.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "oh-my-ztty.virtual-display-comparison.v2",
        "recorded_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scope": "One window at a time on a private Xvfb display, forced software OpenGL, the same installed preset zsh with completion initialized, the same resolved font family and nominal font size, and verified 100x28 PTY; padding units differ as recorded below. Application PSS includes terminal processes, direct helpers, and shell. Newly activated session helpers are listed separately.",
        "limitations": [
            "Xvfb has no hardware GPU presentation. These software OpenGL results do not rank native GPU desktops.",
            "The display server and private D-Bus daemon are excluded. PSS does not measure GPU allocations.",
            "One launch per terminal, five seconds of settling, then ten samples at 200 ms intervals.",
            "PSS depends on library pages shared with other running processes. Font requests match; renderer implementations and actual glyph rasterization differ.",
        ],
        "archive": archive.name,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "system": {"kernel": os.uname().release, "architecture": os.uname().machine},
        "load_average_at_start": list(os.getloadavg()),
        "versions": {"kitty": subprocess.check_output(["kitty", "--version"], text=True).splitlines()[0]},
        "cases": {},
    }
    with tempfile.TemporaryDirectory(prefix="omztty-compare-") as temporary:
        temp = Path(temporary)
        home, runtime = temp / "home with spaces", temp / "runtime"
        demo = home / "demo"
        demo.mkdir(parents=True)
        runtime.mkdir(mode=0o700)
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("XDG_", "ZSHARD_", "OMZTTY_", "ZDOTDIR", "ZTTY_"))
            and key not in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY", "DBUS_SESSION_BUS_ADDRESS", "SESSION_MANAGER")
        }
        env.update(
            HOME=str(home), XDG_DATA_HOME=str(home / ".local/share"),
            XDG_CONFIG_HOME=str(home / ".config"), XDG_CACHE_HOME=str(home / ".cache"),
            XDG_STATE_HOME=str(home / ".local/state"), XDG_RUNTIME_DIR=str(runtime),
            XDG_SESSION_TYPE="x11", GDK_BACKEND="x11", LIBGL_ALWAYS_SOFTWARE="1",
        )
        with tarfile.open(archive, "r:gz") as bundle:
            installer = temp / "install.sh"
            installer.write_bytes(bundle.extractfile("oh-my-ztty/install.sh").read())
            report["build"] = json.loads(bundle.extractfile("oh-my-ztty/BUILD.json").read())
            preset_lines = bundle.extractfile("oh-my-ztty/config/ztty/config").read().decode().splitlines()
            preset = {line.split("=", 1)[0].strip(): line.split("=", 1)[1].strip() for line in preset_lines if "=" in line and not line.lstrip().startswith("#")}
        font_family = run(["fc-match", "--format", "%{family[0]}", preset["font"]], env).stdout
        font_size = preset["font"].rsplit(":size=", 1)[1].split(":", 1)[0]
        report["preset"] = {"font_pattern": preset["font"], "resolved_font_family": font_family, "font_size_pt": font_size, "ztty_padding_px": int(preset["window-padding"]), "kitty_padding_pt": float(preset["window-padding"])}
        report["limitations"].append(f"Padding is not pixel-matched: ztty requests {preset['window-padding']} px; kitty requests {preset['window-padding']} pt, the documented unit of window_padding_width.")
        report["padding_unit_source"] = "Installed kitty 0.50.0 kitty/options/definition.py, window_padding_width: window padding in pts."
        report["working_directory"] = "Temporary directory outside a Git repository."
        run(["sh", installer, "--from", archive], env)
        cli = home / ".local/bin/omztty"
        report["versions"]["ztty"] = run([cli, "ztty", "--version"], env).stdout.strip()
        report["versions"]["zsh"] = run(["zsh", "--version"], env).stdout.strip()
        (home / "memory.zsh").write_text(
            "zshard complete || return\n"
            "clear\n"
            "print -r -- 'Project Z terminal comparison'\n"
            "print -r -- 'Same preset shell. Completion initialized. No AI connection.'\n"
            'stty size > "$HOME/grid"\n'
            'print -r -- $$ > "$HOME/shell-pid"\n'
            'print -r -- ready > "$HOME/ready"\n'
        )
        xvfb = subprocess.Popen(
            ["Xvfb", "-displayfd", "1", "-screen", "0", "1440x1000x24", "-nolisten", "tcp"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env,
        )
        bus = None
        try:
            if not select.select([xvfb.stdout], [], [], 10)[0]:
                raise RuntimeError("Xvfb did not provide a display")
            env["DISPLAY"] = ":" + xvfb.stdout.readline().strip()
            bus = subprocess.Popen(
                ["dbus-daemon", "--session", "--nofork", "--print-address=1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, env=env,
            )
            if not select.select([bus.stdout], [], [], 5)[0]:
                raise RuntimeError("private D-Bus did not provide an address")
            env["DBUS_SESSION_BUS_ADDRESS"] = bus.stdout.readline().strip()
            cases = {
                "ztty": ([str(cli), "terminal", "--zsh", "--name", "ohmy-compare", "--geometry", "100x28"], "ztty"),
                "kitty": ([
                    "kitty", "--config", "NONE", "--class", "ohmy-compare-kitty", "--title", "ohmy-compare-kitty",
                    "-o", f"font_family={font_family}", "-o", f"font_size={font_size}", "-o", "initial_window_width=100c",
                    "-o", "initial_window_height=28c", "-o", "remember_window_size=no", "-o", f"window_padding_width={preset['window-padding']}",
                    "-o", f"background={preset['background']}", "-o", f"foreground={preset['foreground']}",
                    "-o", "shell_integration=disabled", "-o", "enable_audio_bell=no", "-o", "close_on_child_death=yes",
                    str(cli), "shell", "--zsh",
                ], "ohmy-compare-kitty"),
            }
            for name, (command, window_class) in cases.items():
                for filename in ("ready", "grid", "shell-pid"):
                    (home / filename).unlink(missing_ok=True)
                address = "@ohmy-compare-" + uuid.uuid4().hex
                case_env = {**env, "OMZTTY_SOCKET": address, "ZTTY_SOCKET": address}
                case = {
                    "command": [part.replace(str(cli), "{installed_omztty}") for part in command],
                    "settle_seconds": 5,
                }
                owned, app, broker, shell_pid = {}, None, None, None
                bus_before = descendants(bus.pid)
                def members():
                    application = descendants(app.pid) if app else set()
                    if broker:
                        application |= descendants(broker)
                    if shell_pid:
                        application.add(shell_pid)
                    helpers = descendants(bus.pid) - bus_before - application
                    for pid in application | helpers:
                        if pid not in owned:
                            owned[pid] = process_identity(pid)
                    return application, helpers
                with (logs / f"{name}.stderr.log").open("w") as errors:
                    try:
                        app = subprocess.Popen(
                            command, cwd=demo, env=case_env, stdout=subprocess.DEVNULL,
                            stderr=errors, start_new_session=True,
                        )
                        owned[app.pid] = process_identity(app.pid)
                        def window():
                            result = run(["xdotool", "search", "--onlyvisible", "--class", window_class], case_env, check=False)
                            return result.stdout.strip().splitlines()[0] if result.returncode == 0 and result.stdout.strip() else None
                        window_id = wait_until(window, seconds=12)
                        run(["xdotool", "windowfocus", "--sync", window_id], case_env)
                        run(["xdotool", "type", "--delay", "0", 'source "$HOME/memory.zsh"'], case_env)
                        run(["xdotool", "key", "Return"], case_env)
                        wait_until(lambda: (home / "ready").exists(), seconds=10)
                        rows, columns = map(int, (home / "grid").read_text().split())
                        if (columns, rows) != (100, 28):
                            raise RuntimeError(f"requested 100x28 but actual PTY is {columns}x{rows}")
                        case["geometry"] = {"columns": columns, "rows": rows}
                        shell_pid = int((home / "shell-pid").read_text())
                        if name == "ztty":
                            broker = peer_pid(address)
                            if not broker:
                                raise RuntimeError("owned ztty broker was not found")
                        members()
                        time.sleep(5)
                        samples, processes = [], []
                        for _ in range(10):
                            application, helpers = members()
                            processes = []
                            for pid in sorted(application | helpers):
                                if not alive(pid, owned[pid]):
                                    continue
                                try:
                                    processes.append({
                                        "program": Path(f"/proc/{pid}/comm").read_text().strip(),
                                        "executable": os.readlink(f"/proc/{pid}/exe").replace(str(home), "{temporary_home}"),
                                        "scope": "session-helper" if pid in helpers else "application",
                                        **memory(pid),
                                    })
                                except (FileNotFoundError, ProcessLookupError):
                                    pass
                            sample = {
                                "application_Pss_KiB": sum(p["Pss_KiB"] for p in processes if p["scope"] == "application"),
                                "session_helpers_Pss_KiB": sum(p["Pss_KiB"] for p in processes if p["scope"] == "session-helper"),
                                "total_Pss_KiB": sum(p["Pss_KiB"] for p in processes),
                                "total_Rss_KiB": sum(p["Rss_KiB"] for p in processes),
                            }
                            samples.append(sample)
                            time.sleep(0.2)
                        case["processes_at_last_sample"] = processes
                        case["samples"] = samples
                        case["sample_count"] = len(samples)
                        for field in samples[0]:
                            case["median_" + field] = statistics.median(sample[field] for sample in samples)
                        case["status"] = "measured"
                    except Exception as error:
                        case["status"], case["reason"] = "excluded", str(error)
                    finally:
                        broker = broker or peer_pid(address)
                        members()
                        case["cleanup_ok"] = not stop(owned)
                        if app:
                            app.wait(timeout=3)
                report["cases"][name] = case
                print(name, case["status"], case.get("median_application_Pss_KiB"), case.get("reason", ""), flush=True)
            run([cli, "uninstall"], env)
        finally:
            if bus:
                stop({pid: process_identity(pid) for pid in descendants(bus.pid)})
                bus.wait(timeout=3)
            xvfb.terminate()
            try:
                xvfb.wait(timeout=3)
            except subprocess.TimeoutExpired:
                xvfb.kill()
                xvfb.wait()
    report["cleanup"] = "Only owned application trees, the private D-Bus session and Xvfb were stopped. The temporary HOME was removed."
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(args.output)
    if any(not case.get("cleanup_ok") for case in report["cases"].values()):
        raise SystemExit("owned processes remained after cleanup")


if __name__ == "__main__":
    main()
