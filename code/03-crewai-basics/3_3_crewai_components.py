"""
3.3 CrewAI Components
Module 3 · CrewAI Basics | Read first: md/03-crewai-basics/3_3_crewai_components.md

What you'll learn:
  The core components in one program: LLM, Agent, Tool, Task, Crew, Process,
  and the CrewOutput result object you get back.
  At the end we print a "component map" of everything that ran.

Run (from the repo root):
  .venv\\Scripts\\python code\\03-crewai-basics\\3_3_crewai_components.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool

# COMPONENT: LLM ------------------------------------------------
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# COMPONENT: Tool -----------------------------------------------
@tool("Reading time")
def reading_time(text: str) -> str:
    """Estimate how long a text takes to read (200 words per minute)."""
    words = len(text.split())
    return f"{words} words, about {max(1, round(words / 200))} min"


# COMPONENT: Agents ---------------------------------------------
writer = Agent(role="Blog Writer", goal="Write short, clear blog intros", backstory="Plain words, short sentences.", llm=llm)
editor = Agent(
    role="Editor",
    goal="Polish text and report its reading time",
    backstory="You always measure reading time with your tool.",
    tools=[reading_time],
    llm=llm,
)

# COMPONENT: Tasks ----------------------------------------------
draft = Task(description="Write a 80-word blog intro about {topic}.", expected_output="One paragraph, about 80 words.", agent=writer)
polish = Task(
    description="Polish the intro, then use the reading time tool on it.",
    expected_output="The polished paragraph, then a line 'Reading time: ...'.",
    agent=editor,
    context=[draft],
)

# COMPONENT: Crew + Process -------------------------------------
crew = Crew(agents=[writer, editor], tasks=[draft, polish], process=Process.sequential)

# COMPONENT: Kickoff -> CrewOutput ------------------------------
result = crew.kickoff(inputs={"topic": "learning to code at 40"})

print("\n===== FINAL RESULT (result.raw) =====\n")
print(result.raw)

print("\n===== COMPONENT MAP =====\n")
print(f"LLM       {llm.model}")
print(f"Process   {crew.process.value}")
for agent in crew.agents:
    tools = ", ".join(t.name for t in agent.tools) or "none"
    print(f"Agent     {agent.role:<12} tools: {tools}")
for i, task_output in enumerate(result.tasks_output, 1):
    print(f"Task {i}    by {task_output.agent:<12} -> {len(task_output.raw.split())} words")

print("\n===== THE RESULT OBJECT (CrewOutput) =====\n")
print(f"result.raw           -> final text ({len(result.raw)} chars)")
print(f"result.tasks_output  -> {len(result.tasks_output)} TaskOutput objects, one per task")
print(f"result.pydantic      -> {result.pydantic}  (filled when a task uses output_pydantic, see 6.1)")
print(f"result.json_dict     -> {result.json_dict}  (filled when a task uses output_json)")

# ---------------------------------------------------------------
# Takeaways
#   - LLM thinks, Tool acts, Agent = both + identity, Task = the job,
#     Crew + Process = the team and its way of working.
#   - kickoff() returns a CrewOutput: the final answer AND every step.
#   - Memory (7.2) and Flows (Module 8) build on these same pieces.
