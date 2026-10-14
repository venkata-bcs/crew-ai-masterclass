"""
3.1 CrewAI: What Is It?
Module 3 · CrewAI Basics | Read first: md/03-crewai-basics/3_1_what_is_crewai.md

What you'll learn:
  The smallest possible CrewAI program: 1 agent, 1 task, 1 crew.
  Every line is explained. This is the "hello world" of CrewAI.

Run (from the repo root):
  .venv\\Scripts\\python code\\03-crewai-basics\\3_1_what_is_crewai.py "black holes"
"""

# --- Standard library imports ---
import os
import re
import sys
from pathlib import Path

# CrewAI sends anonymous usage data by default. Switch it off BEFORE importing crewai.
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
# CrewAI prints emoji; make the Windows console accept them.
sys.stdout.reconfigure(encoding="utf-8")

# The 4 building blocks of almost every CrewAI program.
from crewai import LLM, Agent, Crew, Task

# --- The brain: read the NVIDIA key from settings.config at the repo root ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"  # 2 folders up from this file
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),  # which model to use
    custom_openai=True,  # NVIDIA speaks the OpenAI protocol
    base_url="https://integrate.api.nvidia.com/v1",  # where to send requests
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],  # who we are
)

# --- The worker: an Agent is described in plain English ---
teacher = Agent(
    role="Friendly Teacher",  # job title
    goal="Explain {topic} so a 12-year-old understands it",  # {topic} is filled in at kickoff
    backstory="You have taught science for 20 years and love everyday examples.",  # personality
    llm=llm,  # the brain it thinks with
)

# --- The job: a Task says WHAT to do and what "done" looks like ---
explain = Task(
    description="Explain {topic} in simple words.",
    expected_output="3 short paragraphs and one everyday analogy. No jargon.",
    agent=teacher,  # who is responsible
)

# --- The team: a Crew groups agents and tasks ---
crew = Crew(agents=[teacher], tasks=[explain])

# --- Go: kickoff() runs the work and returns a result object ---
topic = sys.argv[1] if len(sys.argv) > 1 else "black holes"
result = crew.kickoff(inputs={"topic": topic})

print("\n===== RESULT =====\n")
print(result.raw)  # .raw is the final answer as plain text

# ---------------------------------------------------------------
# Takeaways
#   - CrewAI = a Python framework for teams of AI agents.
#   - You DESCRIBE agents and tasks in plain English; CrewAI runs them.
#   - Every program in this course is a variation of these ~10 lines.
