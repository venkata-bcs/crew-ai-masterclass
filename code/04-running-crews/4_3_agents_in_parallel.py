"""
4.3 Agents in Parallel
Module 4 · Running Crews | Read first: md/04-running-crews/4_3_agents_in_parallel.md

What you'll learn:
  Tasks that don't depend on each other can run AT THE SAME TIME with
  async_execution=True. A later task then joins their results via context.
    Pros researcher ─┐
                     ├─> Judge
    Cons researcher ─┘
  The timeline shows the first two bars overlapping.

Run (from the repo root):
  .venv\\Scripts\\python code\\04-running-crews\\4_3_agents_in_parallel.py "electric cars"
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


optimist = Agent(role="Optimist Researcher", goal="Find the strongest advantages", backstory="You see the upside.", llm=llm)
skeptic = Agent(role="Skeptic Researcher", goal="Find the strongest disadvantages", backstory="You see the risks.", llm=llm)
judge = Agent(role="Fair Judge", goal="Weigh both sides and give a verdict", backstory="Balanced and decisive.", llm=llm)

pros = Task(
    name="pros",
    description="List the 3 biggest advantages of {topic}.",
    expected_output="3 bullets.",
    agent=optimist,
    async_execution=True,  # <- don't wait: start the next task right away
)
cons = Task(
    name="cons",
    description="List the 3 biggest disadvantages of {topic}.",
    expected_output="3 bullets.",
    agent=skeptic,
    async_execution=True,  # <- runs alongside 'pros'
)
verdict = Task(
    name="verdict",
    description="Weigh the pros and cons of {topic} and give a verdict.",
    expected_output="A 60-word verdict that mentions at least one pro and one con.",
    agent=judge,
    context=[pros, cons],  # <- waits for BOTH, then uses both outputs
)

topic = sys.argv[1] if len(sys.argv) > 1 else "electric cars"
crew = Crew(agents=[optimist, skeptic, judge], tasks=[pros, cons, verdict], process=Process.sequential)
T0 = time.perf_counter()
result = crew.kickoff(inputs={"topic": topic})
crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== PROS =====\n" + result.tasks_output[0].raw.strip())
print("\n===== CONS =====\n" + result.tasks_output[1].raw.strip())
print("\n===== VERDICT =====\n" + result.raw.strip())

print("\n===== TIMELINE =====\n")
total = max(end for _, end in timeline.values())
for name, (start, end) in timeline.items():
    left = int(start / total * 50)
    width = max(1, int((end - start) / total * 50))
    print(f"{name:<8} |{' ' * left}{'█' * width}{' ' * (50 - left - width)}| {start:5.1f}s -> {end:5.1f}s")

work = sum(end - start for start, end in timeline.values())
print(f"\nSum of task times: {work:.1f}s   Actual total: {total:.1f}s   Saved: {work - total:.1f}s")

# ---------------------------------------------------------------
# Takeaways
#   - async_execution=True = "start me and move on".
#   - A following task with context=[...] waits for those async tasks.
#   - Only parallelise tasks that DON'T need each other's output.
#   - A crew can't END on an async task: always finish with a normal one.
