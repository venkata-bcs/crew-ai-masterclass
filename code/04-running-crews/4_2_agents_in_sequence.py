"""
4.2 Agents in Sequence
Module 4 · Running Crews | Read first: md/04-running-crews/4_2_agents_in_sequence.md

What you'll learn:
  In a sequential crew each task WAITS for the one before it, and the
  earlier output is passed on through `context`. We draw a timeline
  of when each task started and finished to prove it.

Run (from the repo root):
  .venv\\Scripts\\python code\\04-running-crews\\4_2_agents_in_sequence.py
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
from crewai.events import TaskCompletedEvent, TaskStartedEvent, crewai_event_bus

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# --- Record when each task starts and ends ---
T0 = time.perf_counter()
timeline = {}


@crewai_event_bus.on(TaskStartedEvent)
def task_started(source, event):
    timeline[event.task.name] = [time.perf_counter() - T0, None]


@crewai_event_bus.on(TaskCompletedEvent)
def task_done(source, event):
    timeline[event.task.name][1] = time.perf_counter() - T0


# --- A 3-step pipeline ---
researcher = Agent(role="Researcher", goal="Collect facts", backstory="Accurate and brief.", llm=llm)
writer = Agent(role="Writer", goal="Write a short article", backstory="Clear and friendly.", llm=llm)
editor = Agent(role="Editor", goal="Polish the article", backstory="Strict but kind.", llm=llm)

research = Task(name="1 research", description="List 4 facts about {topic}.", expected_output="4 bullets.", agent=researcher)
write = Task(name="2 write", description="Write a 100-word article on {topic} from the facts.", expected_output="One paragraph.", agent=writer, context=[research])
edit = Task(name="3 edit", description="Polish the article. Keep it under 100 words.", expected_output="The final paragraph.", agent=editor, context=[write])

crew = Crew(agents=[researcher, writer, editor], tasks=[research, write, edit], process=Process.sequential)
T0 = time.perf_counter()
result = crew.kickoff(inputs={"topic": "the deep sea"})
crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== FINAL ARTICLE =====\n")
print(result.raw)

# --- Draw the timeline: each '█' is a slice of time ---
print("\n===== TIMELINE =====\n")
total = max(end for _, end in timeline.values())
for name, (start, end) in timeline.items():
    left = int(start / total * 50)
    width = max(1, int((end - start) / total * 50))
    print(f"{name:<11} |{' ' * left}{'█' * width}{' ' * (50 - left - width)}| {start:5.1f}s -> {end:5.1f}s")
print(f"\nTotal: {total:.1f}s. No bars overlap: each task waited for the previous one.")

# ---------------------------------------------------------------
# Takeaways
#   - Sequential = an assembly line. Order is the list order.
#   - context=[earlier_task] is how output is handed forward.
#   - Total time = sum of all steps. Module 4.3 shows how to overlap them.
