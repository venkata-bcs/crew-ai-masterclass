"""
0.1 Setup & LLM Keys
Module 0 · Getting Started | Read first: md/00-getting-started/0_1_setup_and_keys.md

What you'll learn:
  - How every script in this course finds the LLM key (settings.config)
  - How to check that Python, CrewAI and the NVIDIA LLM all work

Run (from the repo root):
  .venv\\Scripts\\python code\\00-getting-started\\0_1_check_setup.py
"""

import os
import re
import sys
import time
from importlib.metadata import version
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")


def check(label: str, ok: bool, detail: str) -> bool:
    print(f"  {'✅' if ok else '❌'} {label:<22} {detail}")
    return ok


print("===== SETUP CHECK =====\n")

# 1. Python version: CrewAI supports 3.10 - 3.13
py_ok = (3, 10) <= sys.version_info[:2] <= (3, 13)
check("Python 3.10 - 3.13", py_ok, sys.version.split()[0])

# 2. CrewAI installed?
try:
    from crewai import LLM

    check("crewai installed", True, version("crewai"))
except ImportError:
    check("crewai installed", False, "run: pip install crewai")
    sys.exit(1)

# 3. settings.config exists at the repo root (two folders up from this file)
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
if not check("settings.config found", SETTINGS.exists(), str(SETTINGS)):
    sys.exit(1)

# 4. Read KEY='value' lines into a dict
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
key = cfg.get("NVIDIA_API_KEY") or cfg.get("NVDIA_API_KEY")
masked = f"{key[:6]}...{key[-4:]}" if key else "missing"  # never print a whole key
if not check("NVIDIA key present", bool(key), masked):
    sys.exit(1)

# 5. Build the LLM exactly the way every course script does
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,  # NVIDIA's API is OpenAI-compatible
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=key,
)
check("Model", True, llm.model)

# 6. One real call, timed
start = time.perf_counter()
try:
    answer = llm.call("Reply with exactly: READY")
    check("LLM responds", "READY" in answer.upper(), f"{answer.strip()!r} in {time.perf_counter() - start:.1f}s")
except Exception as e:  # noqa: BLE001 - show any connection problem plainly
    check("LLM responds", False, str(e)[:120])
    sys.exit(1)

print("\nAll good. You're ready for Module 1.")

# ---------------------------------------------------------------
# Takeaways
#   - Keys live in settings.config (git-ignored), never in code.
#   - NVIDIA speaks the OpenAI protocol, so CrewAI's OpenAI client works
#     with just a different base_url.
#   - If this script passes, every other script in the course will run.
