#!/usr/bin/env python3
"""
Run all system meta checks and emit a JSON summary.

This is meant to be:
  - Easy for humans/judges to run.
  - Easy for ChatGPT to parse programmatically.

It prints one CHECK line per check and writes meta_test_results.json.
"""

import json
from pathlib import Path
import sys

# Ensure project root is on sys.path so 'tests' can be imported
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.system_meta.test_shell_scripts import (
    check_dev_sh_syntax,
    check_dev_sh_smoke_dry_run,
)
from tests.system_meta.test_readme_contract import (
    check_venv_not_committed,
    check_readme_commands_exist,
)
from tests.system_meta.test_tmux_behavior import (
    check_run_all_tmux_guard,
    check_run_all_tmux_behavior_no_tmux,
)
from tests.system_meta.test_cors_and_frontend import (
    check_cors_middleware_present,
)
from tests.system_meta.test_scraper_failure_modes import (
    check_web_scrape_failure_graceful,
)


def main() -> None:
    checks = []
    for fn in [
        check_dev_sh_syntax,
        check_dev_sh_smoke_dry_run,
        check_venv_not_committed,
        check_readme_commands_exist,
        check_run_all_tmux_guard,
        check_run_all_tmux_behavior_no_tmux,
        check_cors_middleware_present,
        check_web_scrape_failure_graceful,
    ]:
        result = fn()
        checks.append(
            {
                "id": result.get("id"),
                "status": result.get("status"),
                "detail": result.get("detail"),
                "data": result.get("data", {}),
            }
        )

    summary = {"checks": checks}
    out_path = Path("meta_test_results.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
