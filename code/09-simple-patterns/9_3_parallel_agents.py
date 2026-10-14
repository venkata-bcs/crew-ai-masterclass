"""
9.3 Pattern: Parallel Agents
Module 9 · Simple Patterns | Read first: md/09-simple-patterns/9_3_parallel_agents.md

PROBLEM:  You have a new product idea and want feedback from 3 experts:
          a customer, an engineer and an accountant. Asking them one by one is slow.
SOLUTION: Ask all 3 AT THE SAME TIME (async_execution=True),
          then a 4th agent combines their opinions into one verdict.

Run (from the repo root):
  .venv\\Scripts\\python code\\09-simple-patterns\\9_3_parallel_agents.py
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

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

IDEA = "A smart water bottle that glows when you forget to drink, priced at $49."


def expert(role: str) -> Agent:
    return Agent(role=role, goal="Give honest, short feedback", backstory=f"You think like a typical {role.lower()}.", llm=llm)


customer, engineer, accountant = expert("Customer"), expert("Engineer"), expert("Accountant")
boss = Agent(role="Product Manager", goal="Make a clear go / no-go decision", backstory="Decisive and fair.", llm=llm)

# The 3 opinions: independent of each other -> run them in parallel
opinions = [
    Task(description="Would you buy this? Why or why not? Idea: {idea}", expected_output="2 sentences.", agent=customer, async_execution=True),
    Task(description="Is this easy or hard to build? Idea: {idea}", expected_output="2 sentences.", agent=engineer, async_execution=True),
    Task(description="Can this make money at that price? Idea: {idea}", expected_output="2 sentences.", agent=accountant, async_execution=True),
]
# The verdict: needs ALL 3 opinions -> waits for them via context
verdict = Task(
    description="Read the 3 expert opinions and decide: GO or NO-GO for this idea: {idea}",
    expected_output="'GO' or 'NO-GO' on the first line, then one sentence why.",
    agent=boss,
    context=opinions,
)

start = time.perf_counter()
result = Crew(agents=[customer, engineer, accountant, boss], tasks=[*opinions, verdict]).kickoff(inputs={"idea": IDEA})
seconds = time.perf_counter() - start

print(f"\n💡 IDEA: {IDEA}\n")
for icon, name, output in zip(["🛒", "🔧", "💰"], ["Customer", "Engineer", "Accountant"], result.tasks_output):
    print(f"{icon} {name:<10}: {output.raw.strip()}\n")
print(f"🧑‍💼 VERDICT   : {result.raw.strip()}")
print(f"\n⏱️ Done in {seconds:.1f}s (the 3 experts answered at the same time)")

# ---------------------------------------------------------------
# Takeaways
#   - Independent questions -> ask them in parallel with async_execution=True.
#   - The task that needs all answers lists them in context=[...] and waits.
#   - A crew must END with a normal (non-async) task, here: the verdict.
