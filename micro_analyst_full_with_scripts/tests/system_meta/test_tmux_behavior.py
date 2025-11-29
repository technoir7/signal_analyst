import json
import os
import subprocess
from pathlib import Path


def _print_check_line(check_id: str, status: str, message: dict) -> None:
    print(f"CHECK {check_id} {status} {json.dumps(message, separators=(',', ':'))}")


def check_run_all_tmux_guard():
    """
    LM_03_RUN_ALL_TMUX_GUARD

    Ensure run_all_tmux.sh checks for tmux presence explicitly.
    """
    check_id = "LM_03_RUN_ALL_TMUX_GUARD"
    script_path = Path("run_all_tmux.sh")

    if not script_path.exists():
        status = "SKIP"
        msg = {
            "detail": "run_all_tmux.sh not found; skipping tmux guard check.",
            "hint": "If you rely on a tmux cluster, include run_all_tmux.sh.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    content = script_path.read_text(encoding="utf-8")
    has_guard = "command -v tmux" in content or "which tmux" in content
    status = "PASS" if has_guard else "FAIL"
    msg = {
        "detail": (
            "tmux guard "
            + ("found in run_all_tmux.sh" if has_guard else "not found in run_all_tmux.sh")
        )
    }
    if status == "FAIL":
        msg["hint"] = (
            "Add a guard at the top of run_all_tmux.sh, e.g.: "
            "'if ! command -v tmux >/dev/null 2>&1; then echo \"tmux is not installed\"; exit 1; fi'"
        )

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


def check_run_all_tmux_behavior_no_tmux():
    """
    LM_03_RUN_ALL_TMUX_BEHAVIOR_NO_TMUX

    Simulate an environment where tmux is not on PATH and ensure run_all_tmux.sh
    exits non-zero and prints a clear message, rather than exploding.
    """
    check_id = "LM_03_RUN_ALL_TMUX_BEHAVIOR_NO_TMUX"
    script_path = Path("run_all_tmux.sh")

    if not script_path.exists():
        status = "SKIP"
        msg = {
            "detail": "run_all_tmux.sh not found; skipping behavior-no-tmux check.",
            "hint": "Include run_all_tmux.sh if you advertise tmux-based orchestration.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    env = dict(os.environ)
    # Intentionally wipe PATH so 'tmux' cannot be found; call /bin/bash explicitly.
    env["PATH"] = "/nonexistent"

    proc = subprocess.run(
        ["/bin/bash", str(script_path)],
        env=env,
        capture_output=True,
        text=True,
    )
    combined_output = ((proc.stdout or "") + (proc.stderr or ""))[:200]
    # We expect a non-zero exit in no-tmux scenario.
    status = "PASS" if proc.returncode != 0 else "FAIL"
    msg = {
        "detail": f"run_all_tmux.sh exited {proc.returncode} with PATH=/nonexistent",
        "output_sample": combined_output,
    }
    if status == "FAIL":
        msg["hint"] = (
            "Ensure run_all_tmux.sh detects missing tmux and exits non-zero "
            "with a clear message instead of silently succeeding."
        )

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


# pytest integration ---------------------------------------------------------


def test_run_all_tmux_guard():
    result = check_run_all_tmux_guard()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])


def test_run_all_tmux_behavior_no_tmux():
    result = check_run_all_tmux_behavior_no_tmux()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])
