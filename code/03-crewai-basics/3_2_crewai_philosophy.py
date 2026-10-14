"""
3.2 CrewAI Philosophy
Module 3 · CrewAI Basics | Read first: md/03-crewai-basics/3_2_crewai_philosophy.md

What you'll learn:
  CrewAI's big idea: model your AI team like a real company.
  Clear roles + clear tasks + clear handoffs = better results.
  Same task, two agents:  a vague "Assistant"  vs  a sharp specialist.

Run (from the repo root):
  .venv\\Scripts\\python code\\03-crewai-basics\\3_2_crewai_philosophy.py
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

JOB = "Write the error message shown when a customer's card payment fails."

# A) Vague agent + vague task: the LLM has to guess everything.
vague_agent = Agent(role="Assistant", goal="Help", backstory="You help.", llm=llm)
vague_task = Task(description=JOB, expected_output="An error message.", agent=vague_agent)

# B) Sharp agent + sharp task: a real job title, a measurable goal,
#    a backstory that sets tone and rules, and a precise "done".
sharp_agent = Agent(
    role="Senior UX Writer for a payments app",
    goal="Write error messages that calm users and tell them exactly what to do next",
    backstory=(
        "You've written UI copy for banks for 10 years. You never blame the user, "
        "never use technical codes, and always give one clear next step."
    ),
    llm=llm,
)
sharp_task = Task(
    description=JOB,
    expected_output="A title (max 6 words) and a body (max 25 words) with one clear next step. No error codes.",
    agent=sharp_agent,
)

print("===== A) VAGUE: role='Assistant', goal='Help' =====\n")
print(Crew(agents=[vague_agent], tasks=[vague_task]).kickoff().raw.strip())

print("\n===== B) SHARP: a real role, goal, backstory and 'done' =====\n")
print(Crew(agents=[sharp_agent], tasks=[sharp_task]).kickoff().raw.strip())

# ---------------------------------------------------------------
# Takeaways
#   - Role-playing is the core of CrewAI: treat agents like hires.
#   - Specific role + goal + backstory -> consistent tone and quality.
#   - expected_output is your acceptance test: make it measurable.
