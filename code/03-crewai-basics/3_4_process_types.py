"""
3.4 CrewAI Process Types
Module 3 · CrewAI Basics | Read first: md/03-crewai-basics/3_4_process_types.md

What you'll learn:
  The same team and the same tasks, run with both process types:
    Process.sequential   -> tasks run in the order you list them
    Process.hierarchical -> a manager agent decides who does what
  We compare who did the work, LLM calls and time.

Run (from the repo root):
  .venv\\Scripts\\python code\\03-crewai-basics\\3_4_process_types.py
"""

import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task
from crewai.events import LLMCallCompletedEvent, crewai_event_bus

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# Track which agent made each LLM call
calls = []


@crewai_event_bus.on(LLMCallCompletedEvent)
def on_llm(source, event):
    calls.append(event.agent_role or "-")


def build_team():
    """Fresh agents each run, so the two runs don't share state."""
    researcher = Agent(role="Researcher", goal="Find key facts", backstory="Facts only.", llm=llm, allow_delegation=False)
    writer = Agent(role="Writer", goal="Write clear summaries", backstory="Short and simple.", llm=llm, allow_delegation=False)
    return researcher, writer


def run(process: Process) -> None:
    calls.clear()
    researcher, writer = build_team()
    if process == Process.sequential:
        # Sequential: YOU assign each task to an agent and set the order.
        tasks = [
            Task(description="List 3 facts about honeybees.", expected_output="3 bullets.", agent=researcher),
            Task(description="Write a 50-word summary from the facts.", expected_output="One paragraph.", agent=writer),
        ]
        crew = Crew(agents=[researcher, writer], tasks=tasks, process=process)
    else:
        # Hierarchical: NO agent on the task. A manager (manager_llm) delegates.
        tasks = [Task(description="Find 3 facts about honeybees, then write a 50-word summary from them.", expected_output="One paragraph.")]
        crew = Crew(agents=[researcher, writer], tasks=tasks, process=process, manager_llm=llm)

    start = time.perf_counter()
    result = crew.kickoff()
    crewai_event_bus.flush()  # wait for CrewAI's events to be delivered
    seconds = time.perf_counter() - start

    print(f"\n===== {process.value.upper()} =====\n")
    print(result.raw.strip())
    who = {role: calls.count(role) for role in dict.fromkeys(calls)}
    print(f"\nLLM calls: {len(calls)}  {who}")
    print(f"Time     : {seconds:.1f}s")


run(Process.sequential)
run(Process.hierarchical)

# ---------------------------------------------------------------
# Takeaways
#   - Sequential: predictable, cheap, you control the order. Start here.
#   - Hierarchical: flexible, a "Crew Manager" plans and delegates,
#     but it costs extra LLM calls (look at the call counts).
