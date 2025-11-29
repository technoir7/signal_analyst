import os, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[2]
README = ROOT/"README.md"
DEV = ROOT/"dev.sh"
TMUX = ROOT/"run_all_tmux.sh"
META = ROOT/"run_meta_checks.sh"

def test_readme_exists():
    assert README.exists()
    txt = README.read_text()
    assert "uvicorn" in txt.lower()

@pytest.mark.parametrize("s",[DEV,TMUX,META])
def test_scripts_exist(s):
    assert s.exists()

@pytest.mark.skipif(not DEV.exists(), reason="dev.sh missing")
def test_dev_sh_dry_run():
    env = os.environ.copy(); env["DEV_SH_DRY_RUN"]="1"
    p = subprocess.run(["bash", str(DEV)], env=env, cwd=str(ROOT),
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert p.returncode == 0