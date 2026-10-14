"""
2.3 Design Question: Agent Overkill
Module 2 · Thinking in Multi-Agent Systems | Read first: md/02-multi-agent-thinking/2_3_agent_overkill.md

What you'll learn:
  Not every problem needs agents. One simple job, solved three ways:
    1) plain Python        2) one LLM call        3) a CrewAI agent
  and compare time, tokens and correctness.

Run (from the repo root):
  .venv\\Scripts\\python code\\02-multi-agent-thinking\\2_3_agent_overkill.py
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

tokens = {"total": 0}


@crewai_event_bus.on(LLMCallCompletedEvent)
def count(source, event):
    tokens["total"] += (event.usage or {}).get("total_tokens", 0)


# The job: convert Celsius to Fahrenheit and label each reading.
READINGS_C = [12, 25, 31, 8, 19]
JOB = f"Convert these Celsius readings to Fahrenheit (1 decimal) and label each: below 15C = cold, 15-25C = mild, above 25C = hot. Readings: {READINGS_C}. Answer as lines like '12C = 53.6F cold'."
results = []


def timed(name: str, fn) -> None:
    tokens["total"] = 0
    start = time.perf_counter()
    answer = fn()
    crewai_event_bus.flush()  # wait for CrewAI's events to be delivered
    results.append((name, time.perf_counter() - start, tokens["total"], answer))


# 1) Plain Python: fixed rules, so code is perfect for this.
def plain_python() -> str:
    def label(c):
        return "cold" if c < 15 else "mild" if c <= 25 else "hot"

    return "\n".join(f"{c}C = {c * 9 / 5 + 32:.1f}F {label(c)}" for c in READINGS_C)


# 2) One LLM call: fine for fuzzy text jobs, unnecessary here.
def one_llm_call() -> str:
    return llm.call(JOB)


# 3) A full agent + crew: maximum machinery for a tiny fixed job.
def crew_agent() -> str:
    agent = Agent(role="Weather Assistant", goal="Convert and label temperatures", backstory="Precise.", llm=llm)
    task = Task(description=JOB, expected_output="One line per reading.", agent=agent)
    return Crew(agents=[agent], tasks=[task]).kickoff().raw


timed("1) Plain Python", plain_python)
timed("2) One LLM call", one_llm_call)
timed("3) CrewAI agent", crew_agent)

truth = plain_python()
print("\n===== RESULTS =====")
for name, seconds, used, answer in results:
    correct = all(line.split(" = ")[1].split()[0] in answer for line in truth.splitlines())
    print(f"\n--- {name} ---\n{answer.strip()}")
    print(f"[time {seconds:.3f}s | tokens {used:,} | numbers correct: {'✅' if correct else '❌'}]")

print("\n===== VERDICT =====\n")
print(f"{'Approach':<18} {'Seconds':>8} {'Tokens':>7}")
for name, seconds, used, _ in results:
    print(f"{name:<18} {seconds:>8.3f} {used:>7,}")

# ---------------------------------------------------------------
# Takeaways
#   - Fixed rules + exact answers -> plain code wins (free, instant, always right).
#   - Fuzzy language job, one step -> a single LLM call.
#   - Decisions, tools, several steps -> that's when an agent or crew earns its cost.
