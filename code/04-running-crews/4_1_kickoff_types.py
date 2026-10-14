"""
4.1 Types of Kickoff
Module 4 · Running Crews | Read first: md/04-running-crews/4_1_kickoff_types.md

What you'll learn:
  The 4 ways to start a crew, and when to use each:
    crew.kickoff(inputs)                       one job, wait for it
    crew.kickoff_for_each(list)                many jobs, one after another
    await crew.kickoff_async(inputs)           one job, without blocking
    await crew.kickoff_for_each_async(list)    many jobs, all at the same time

Run (from the repo root):
  .venv\\Scripts\\python code\\04-running-crews\\4_1_kickoff_types.py
"""

import asyncio
import os
import re
import sys
import time
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


def make_crew() -> Crew:
    """A FRESH crew for each demo. Gotcha: after kickoff(), a crew's tasks keep the
    filled-in {animal}, so reusing that same crew object would repeat 'octopus'."""
    zoologist = Agent(role="Zoologist", goal="Share surprising animal facts", backstory="You love weird animal trivia.", llm=llm)
    fact = Task(description="Give one surprising fact about the {animal}.", expected_output="One sentence.", agent=zoologist)
    return Crew(agents=[zoologist], tasks=[fact])


ANIMALS = [{"animal": "octopus"}, {"animal": "owl"}, {"animal": "axolotl"}]
timings = []


def report(method: str, results, seconds: float) -> None:
    timings.append((method, len(results), seconds))
    print(f"\n----- {method}  ({seconds:.1f}s) -----")
    for r in results:
        print(f"  • {r.raw.strip()}")


# 1) kickoff: the normal case. Blocks until done.
start = time.perf_counter()
one = make_crew().kickoff(inputs={"animal": "octopus"})
report("kickoff", [one], time.perf_counter() - start)

# 2) kickoff_for_each: a batch, run one after another. Blocks.
start = time.perf_counter()
many = make_crew().kickoff_for_each(inputs=ANIMALS)
report("kickoff_for_each", many, time.perf_counter() - start)


# 3 & 4 are "async": they must be awaited inside an async function.
async def async_demos() -> None:
    # 3) kickoff_async: one job, but your program can do other things meanwhile.
    start = time.perf_counter()
    job = asyncio.create_task(make_crew().kickoff_async(inputs={"animal": "octopus"}))
    print("\n(kickoff_async started... the program is free to do other work here)")
    result = await job
    report("kickoff_async", [result], time.perf_counter() - start)

    # 4) kickoff_for_each_async: the whole batch at the same time.
    start = time.perf_counter()
    results = await make_crew().kickoff_for_each_async(inputs=ANIMALS)
    report("kickoff_for_each_async", results, time.perf_counter() - start)


asyncio.run(async_demos())

print("\n===== SUMMARY =====\n")
print(f"{'Method':<24} {'Jobs':>4} {'Seconds':>8}")
for method, jobs, seconds in timings:
    print(f"{method:<24} {jobs:>4} {seconds:>8.1f}")

# ---------------------------------------------------------------
# Takeaways
#   - kickoff: default. kickoff_for_each: simple batches.
#   - The async versions don't make ONE job faster; they let jobs overlap.
#   - Compare kickoff_for_each vs kickoff_for_each_async: same 3 jobs,
#     the async batch should finish in roughly the time of the slowest one.
