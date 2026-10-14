"""
02 - The smallest real crew: 1 agent + 1 task.

Shows: Agent (role / goal / backstory), Task (description / expected_output),
Crew + kickoff(inputs=...) filling in {topic}.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\02_one_agent_one_task.py "black holes"
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

teacher = Agent(
    role="Friendly Teacher",
    goal="Explain {topic} so that a 12-year-old understands it",
    backstory="You have taught science for 20 years and love simple everyday examples.",
    llm=llm,
    verbose=True,  # watch the agent work
)

explain = Task(
    description="Explain {topic} in simple words.",
    expected_output="3 short paragraphs and one everyday analogy. No jargon.",
    agent=teacher,
)

crew = Crew(agents=[teacher], tasks=[explain])

topic = sys.argv[1] if len(sys.argv) > 1 else "the internet"
result = crew.kickoff(inputs={"topic": topic})  # {topic} is filled in everywhere

print("\n===== RESULT =====\n")
print(result.raw)
