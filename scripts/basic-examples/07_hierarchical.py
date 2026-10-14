"""
07 - Hierarchical process: a manager decides who does what.

The task has NO agent assigned. CrewAI creates a manager (using manager_llm)
that delegates work to the specialists and checks their answers.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\07_hierarchical.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

chef = Agent(
    role="Chef",
    goal="Design simple, tasty recipes",
    backstory="A home-cooking expert who keeps ingredient lists short.",
    llm=llm,
)
nutritionist = Agent(
    role="Nutritionist",
    goal="Estimate calories and suggest healthier swaps",
    backstory="A dietitian who gives practical, non-preachy advice.",
    llm=llm,
)

task = Task(
    description=(
        "Plan a vegetarian dinner for two: give a recipe, "
        "then estimate calories per serving and suggest one healthier swap."
    ),
    expected_output="Recipe (ingredients + steps), calories per serving, and one healthier swap.",
    # no agent= here: the manager chooses
)

crew = Crew(
    agents=[chef, nutritionist],
    tasks=[task],
    process=Process.hierarchical,
    manager_llm=llm,  # the manager's brain
    verbose=True,  # watch the manager delegate ("Delegate work to coworker")
)

result = crew.kickoff()
print("\n===== RESULT =====\n")
print(result.raw)
