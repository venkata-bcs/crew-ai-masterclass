"""
2.1 Why Multi-Agent Systems?
Module 2 · Thinking in Multi-Agent Systems | Read first: md/02-multi-agent-thinking/2_1_why_multi_agent.md

What you'll learn:
  The same brief done two ways:
    A) ONE generalist agent does research + writing + review in one go
    B) THREE specialists, each doing one step and passing work along
  Then compare the outputs, the LLM calls, tokens and time.

Run (from the repo root):
  .venv\\Scripts\\python code\\02-multi-agent-thinking\\2_1_why_multi_agent.py "remote work"
"""

import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
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

# Count LLM calls and tokens with CrewAI's events
stats = {"calls": 0, "tokens": 0}


@crewai_event_bus.on(LLMCallCompletedEvent)
def count(source, event):
    stats["calls"] += 1
    stats["tokens"] += (event.usage or {}).get("total_tokens", 0)


def measure(crew: Crew, topic: str) -> tuple[str, dict]:
    stats.update(calls=0, tokens=0)
    start = time.perf_counter()
    text = crew.kickoff(inputs={"topic": topic}).raw
    crewai_event_bus.flush()  # wait for CrewAI's events to be delivered
    return text, {**stats, "seconds": time.perf_counter() - start}


topic = sys.argv[1] if len(sys.argv) > 1 else "remote work"

# ---------------------------------------------------------------
# A) One generalist doing everything in one task
# ---------------------------------------------------------------
generalist = Agent(role="Content Generalist", goal="Produce great content", backstory="You do everything yourself.", llm=llm)
do_everything = Task(
    description="Research {topic}, write a 120-word post for beginners about it, then review and improve it.",
    expected_output="The final 120-word post only.",
    agent=generalist,
)
text_a, stats_a = measure(Crew(agents=[generalist], tasks=[do_everything]), topic)

# ---------------------------------------------------------------
# B) Three specialists, one step each, passing work via context
# ---------------------------------------------------------------
researcher = Agent(role="Researcher", goal="List accurate key facts about {topic}", backstory="Facts only, no fluff.", llm=llm)
writer = Agent(role="Writer", goal="Turn facts into a clear post for beginners", backstory="You write simply.", llm=llm)
reviewer = Agent(role="Reviewer", goal="Fix unclear or wrong sentences", backstory="A strict, kind editor.", llm=llm)

research = Task(description="List 5 key facts about {topic}.", expected_output="5 bullet facts.", agent=researcher)
write = Task(description="Write a 120-word post about {topic} from the facts.", expected_output="A 120-word post.", agent=writer, context=[research])
review = Task(description="Review and improve the post.", expected_output="The final 120-word post only.", agent=reviewer, context=[write])
text_b, stats_b = measure(Crew(agents=[researcher, writer, reviewer], tasks=[research, write, review]), topic)

# ---------------------------------------------------------------
# Compare
# ---------------------------------------------------------------
print("\n===== A) ONE GENERALIST =====\n")
print(text_a)
print("\n===== B) THREE SPECIALISTS =====\n")
print(text_b)

print("\n===== COMPARISON =====\n")
print(f"{'':<18} {'LLM calls':>9} {'Tokens':>8} {'Seconds':>8}")
print(f"{'A) Generalist':<18} {stats_a['calls']:>9} {stats_a['tokens']:>8,} {stats_a['seconds']:>8.1f}")
print(f"{'B) Specialists':<18} {stats_b['calls']:>9} {stats_b['tokens']:>8,} {stats_b['seconds']:>8.1f}")

# ---------------------------------------------------------------
# Takeaways
#   - Specialists cost more calls and tokens...
#   - ...but each step is focused, visible and easy to fix on its own.
#   - If B isn't clearly better for your job, you may not need a crew (see 2.3).
