import json
import re
from pathlib import Path
from subprocess import CalledProcessError, run


def _print_check_line(check_id: str, status: str, message: dict) -> None:
    print(f"CHECK {check_id} {status} {json.dumps(message, separators=(',', ':'))}")


def check_venv_not_committed():
    """
    LM_01_VENV_PRESENT

    Fail only if .venv is *tracked by git*.
    Having a local .venv directory for development is fine.
    """
    check_id = "LM_01_VENV_PRESENT"
    venv_path = Path(".venv")

    # If there's no git repo here, don't enforce anything.
    try:
        run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
    except CalledProcessError:
        status = "SKIP"
        msg = {
            "detail": "Not inside a git repository; skipping .venv commit check.",
            "hint": "This check only applies to git-tracked submissions.",
        }
        _print_check_line(check_id, status, msg)
        return {
            "id": check_id,
            "status": status,
            "detail": msg["detail"],
            "data": msg,
        }

    # If .venv doesn't exist at all, we're fine.
    if not venv_path.exists():
        status = "PASS"
        msg = {"detail": ".venv directory not found at project root"}
        _print_check_line(check_id, status, msg)
        return {
            "id": check_id,
            "status": status,
            "detail": msg["detail"],
            "data": msg,
        }

    # Check whether .venv is tracked by git.
    proc = run(
        ["git", "ls-files", "--error-unmatch", ".venv"],
        capture_output=True,
        text=True,
    )
    tracked = proc.returncode == 0

    if tracked:
        status = "FAIL"
        msg = {
            "detail": ".venv directory is tracked by git.",
            "hint": "Remove .venv from version control and add it to .gitignore.",
        }
    else:
        status = "PASS"
        msg = {
            "detail": ".venv directory exists but is not tracked by git.",
        }

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


def _extract_commands_from_readme(readme_text: str):
    """
    Return a list of candidate shell commands from fenced bash/sh code blocks.
    """
    code_blocks = re.findall(
        r"```(?:bash|sh)?(.*?)```", readme_text, flags=re.DOTALL | re.IGNORECASE
    )
    commands = []
    for block in code_blocks:
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            commands.append(line)
    return commands


def check_readme_commands_exist():
    """
    LM_02_README_COMMANDS_EXIST

    For commands in README code blocks:
      - If they start with './', ensure the file exists.
      - If 'make <target>', ensure that target string appears in Makefile.
    """
    check_id = "LM_02_README_COMMANDS_EXIST"
    readme = Path("README.md")
    if not readme.exists():
        status = "SKIP"
        msg = {
            "detail": "README.md not found; skipping command contract check.",
            "hint": "Include a README.md for judges and developers.",
        }
        _print_check_line(check_id, status, msg)
        return {
            "id": check_id,
            "status": status,
            "detail": msg["detail"],
            "data": msg,
        }

    text = readme.read_text(encoding="utf-8")
    commands = _extract_commands_from_readme(text)
    missing = []

    makefile_text = (
        Path("Makefile").read_text(encoding="utf-8")
        if Path("Makefile").exists()
        else ""
    )

    for cmd in commands:
        if cmd.startswith("./"):
            # Example: ./dev.sh or ./run_all_tmux.sh
            rel = cmd.split()[0][2:]
            if not Path(rel).exists():
                missing.append(cmd)
        elif cmd.startswith("make "):
            target = cmd.split()[1]
            if target not in makefile_text:
                missing.append(cmd)

    status = "FAIL" if missing else "PASS"
    msg = {
        "detail": "README command references checked",
        "missing_commands": missing[:10],
    }
    if status == "FAIL":
        msg["hint"] = (
            "Update README or add the referenced scripts/Make targets so judges "
            "can follow the documented quickstart path."
        )

    _print_check_line(check_id, status, msg)
    return {"id": check_id, "status": status, "detail": msg["detail"], "data": msg}


# pytest integration ---------------------------------------------------------


def test_venv_not_committed():
    result = check_venv_not_committed()
    if result["status"] == "FAIL":
        raise AssertionError(result["detail"])


def test_readme_commands_exist():
    result = check_readme_commands_exist()
    if result["status"] == "FAIL":
        raise AssertionError(
            f"Some README commands reference missing resources: {result['data'].get('missing_commands')}"
        )
