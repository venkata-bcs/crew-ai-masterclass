"""
4.4 Async Crews
Module 4 · Running Crews | Read first: md/04-running-crews/4_4_async_crews.md

What you'll learn:
  4.3 ran TASKS in parallel inside one crew.
  Here we run whole, separate CREWS at the same time with
  kickoff_async() + asyncio.gather(), and measure the speed-up.

Run (from the repo root):
  .venv\\Scripts\\python code\\04-running-crews\\4_4_async_crews.py
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

COUNTRIES = ["Japan", "Peru", "Kenya"]


def make_crew() -> Crew:
    """Each country gets its own, independent crew."""
    guide = Agent(role="Travel Guide", goal="Give quick travel tips", backstory="You've been everywhere.", llm=llm)
    tip = Task(description="Give the single best travel tip for {country}.", expected_output="One sentence.", agent=guide)
    return Crew(agents=[guide], tasks=[tip])


# 1) One after another: total = sum of all three
start = time.perf_counter()
one_by_one = [make_crew().kickoff(inputs={"country": c}) for c in COUNTRIES]
sequential_time = time.perf_counter() - start


# 2) All at once: total ≈ the slowest one
async def run_all_at_once():
    jobs = [make_crew().kickoff_async(inputs={"country": c}) for c in COUNTRIES]  # nothing runs yet
    return await asyncio.gather(*jobs)  # start them all and wait for every one


start = time.perf_counter()
together = asyncio.run(run_all_at_once())
async_time = time.perf_counter() - start

print("\n===== RESULTS (async run) =====\n")
for country, result in zip(COUNTRIES, together):
    print(f"{country:<6} {result.raw.strip()}")

print("\n===== SPEED =====\n")
print(f"One by one     : {sequential_time:5.1f}s")
print(f"All at once    : {async_time:5.1f}s")
print(f"Speed-up       : {sequential_time / async_time:.1f}x")

# ---------------------------------------------------------------
# Takeaways
#   - kickoff_async returns an awaitable; asyncio.gather runs many together.
#   - Great for independent jobs: one crew per customer, per file, per country.
#   - LLM calls spend most time WAITING on the network, so overlap is cheap.
#   - Watch your provider's rate limits when you run many at once.
