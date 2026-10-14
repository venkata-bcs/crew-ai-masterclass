"""
01 - Hello LLM: talk to the "brain" directly. No agent, no task, no crew.

This is level 2 on the autonomy ladder (a single LLM call).
Run:  .venv\\Scripts\\python scripts\\basic-examples\\01_hello_llm.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,  # NVIDIA's API is OpenAI-compatible
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# 1. A plain string prompt
print(llm.call("Explain what an AI agent is in 2 short sentences."))

# 2. Chat-style messages: a system message sets the personality
print(
    llm.call(
        [
            {"role": "system", "content": "You are a pirate. Answer in one sentence."},
            {"role": "user", "content": "What is Python?"},
        ]
    )
)
