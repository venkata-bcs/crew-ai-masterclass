"""
9.1 Pattern: Single Agent
Module 9 · Simple Patterns | Read first: md/09-simple-patterns/9_1_single_agent.md

PROBLEM:  A customer left an angry review. You need a calm, polite reply.
SOLUTION: ONE agent with a clear role does ONE task. That's all.

Run (from the repo root):
  .venv\\Scripts\\python code\\09-simple-patterns\\9_1_single_agent.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

REVIEW = "Terrible! My pizza arrived 45 minutes late and cold. Never ordering again."

# 1) The agent: who it is
support = Agent(
    role="Customer Support Agent",
    goal="Calm unhappy customers and fix their problem",
    backstory="You are kind, you apologise sincerely, and you always offer a fix.",
    llm=llm,
)

# 2) The task: what to do, and what "done" looks like
reply = Task(
    description="Write a reply to this customer review: {review}",
    expected_output="A short, polite reply (max 3 sentences) with an apology and a concrete offer.",
    agent=support,
)

# 3) Run it
result = Crew(agents=[support], tasks=[reply]).kickoff(inputs={"review": REVIEW})

print("\n😠 REVIEW :", REVIEW)
print("\n🤖 REPLY  :", result.raw.strip())

# ---------------------------------------------------------------
# Takeaways
#   - One clear job -> one agent. Start here before adding more agents.
#   - role + goal + backstory set the tone; expected_output sets the format.
