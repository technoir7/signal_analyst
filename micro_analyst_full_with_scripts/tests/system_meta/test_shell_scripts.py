import json
import os
import subprocess
from pathlib import Path


def _print_check_line(check_id: str, status: str, message: dict) -> None:
    """
    Emit a single-line, ChatGPT-friendly CHECK summary.

    Format:
        CHECK <ID> <STATUS> <MESSAGE_JSON>
    """
    print(f"CHECK {check_id} {status} {json.dumps(message, separators=(',', ':'))}")


def check_dev_sh_syntax():
    """
    BUG_01_DEV_SH_SYNTAX

    Ensure dev.sh has valid shell syntax via `bash -n dev.sh`.
    """
    check_id = "BUG_01_DEV_SH_SYNTAX"
    dev_sh = Path("dev.sh")

    if not dev_sh.exists():
        status = "SKIP"
        msg = {
            "detail": "dev.sh not found at project root; skipping syntax check.",
            "hint": "If dev.sh is intended as a dev entrypoint, ensure it is committed.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    proc = subprocess.run(
        ["bash", "-n", str(dev_sh)],
        capture_output=True,
        text=True,
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    msg = {
        "detail": f"bash -n dev.sh exited {proc.returncode}",
        "stderr": (proc.stderr or "")[:200],
    }
    if status == "FAIL":
        msg["hint"] = "Fix shell syntax in dev.sh; ensure all 'if' blocks end in 'fi'."

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


def check_dev_sh_smoke_dry_run():
    """
    BUG_01_DEV_SH_SMOKE

    Run dev.sh with DEV_SH_DRY_RUN=1 and require a clean exit.
    This assumes dev.sh respects DEV_SH_DRY_RUN by skipping heavy operations.
    """
    check_id = "BUG_01_DEV_SH_SMOKE"
    dev_sh = Path("dev.sh")

    if not dev_sh.exists():
        status = "SKIP"
        msg = {
            "detail": "dev.sh not found at project root; skipping dry-run smoke test.",
            "hint": "Add dev.sh if you reference it in README as a main entrypoint.",
        }
        _print_check_line(check_id, status, msg)
        return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}

    env = dict(os.environ)
    env["DEV_SH_DRY_RUN"] = "1"

    proc = subprocess.run(
        ["bash", str(dev_sh)],
        env=env,
        capture_output=True,
        text=True,
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    msg = {
        "detail": f"DEV_SH_DRY_RUN=1 dev.sh exited {proc.returncode}",
        "stdout_sample": (proc.stdout or "")[:200],
        "stderr_sample": (proc.stderr or "")[:200],
    }
    if status == "FAIL":
        msg["hint"] = "Ensure dev.sh handles DEV_SH_DRY_RUN=1 and exits 0 in dry mode."

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


# pytest integration ---------------------------------------------------------


def test_dev_sh_syntax():
    """
    Pytest wrapper: fail the test if the meta-check fails,
    but allow SKIP without failing the suite.
    """
    result = check_dev_sh_syntax()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])


def test_dev_sh_smoke_dry_run():
    result = check_dev_sh_smoke_dry_run()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])
