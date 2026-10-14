"""
1.3 Characteristics of Agents
Module 1 · Agent Fundamentals | Read first: md/01-agent-fundamentals/1_3_characteristics_of_agents.md

What you'll learn:
  Agents are autonomous, goal-directed, use tools, and work in a LOOP
  (think -> act -> observe). We run the same job twice:
    A) max_iter=6  -> the agent can loop as much as it needs
    B) max_iter=2  -> the loop is cut short
  and count the LLM calls and tool calls each time.

Run (from the repo root):
  .venv\\Scripts\\python code\\01-agent-fundamentals\\1_3_characteristics_of_agents.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import LLMCallCompletedEvent, ToolUsageFinishedEvent, crewai_event_bus
from crewai.tools import tool

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# A fake "database". The agent can only see it through the tool.
POPULATION = {"tokyo": 37_400_000, "delhi": 32_900_000, "shanghai": 29_200_000}


@tool("City population")
def city_population(city: str) -> str:
    """Look up the population of ONE city."""
    value = POPULATION.get(city.lower().strip())
    return f"{city}: {value:,}" if value else f"{city}: unknown"


# Count what the agent does, using CrewAI's events.
counts = {"llm": 0, "tools": []}


@crewai_event_bus.on(LLMCallCompletedEvent)
def on_llm(source, event):
    counts["llm"] += 1


@crewai_event_bus.on(ToolUsageFinishedEvent)
def on_tool(source, event):
    counts["tools"].append(f"{event.tool_name}({event.tool_args})")


def run(max_iter: int) -> None:
    counts["llm"], counts["tools"] = 0, []
    analyst = Agent(
        role="Data Analyst",
        goal="Answer with exact figures from the tool",
        backstory="You look up every number. You never guess.",
        tools=[city_population],
        llm=llm,
        max_iter=max_iter,  # the loop limit
    )
    task = Task(
        description="Look up the populations of Tokyo, Delhi and Shanghai one by one, then give the total.",
        expected_output="Each city's population and the total.",
        agent=analyst,
    )
    try:
        answer = Crew(agents=[analyst], tasks=[task]).kickoff().raw.strip()[:300]
    except Exception as e:  # noqa: BLE001 - a cut-short agent may fail to produce any answer
        answer = f"❌ no usable answer ({type(e).__name__}): the loop limit stopped it mid-job"
    crewai_event_bus.flush()  # wait for CrewAI's events to be delivered
    print(f"\n----- max_iter={max_iter} -----")
    print(f"LLM calls : {counts['llm']}")
    print(f"Tool calls: {len(counts['tools'])} -> {counts['tools']}")
    print(f"Answer    : {answer}")


run(max_iter=6)
run(max_iter=2)
print(f"\nTrue total: {sum(POPULATION.values()):,}")

# ---------------------------------------------------------------
# Takeaways
#   - Autonomous: you never said "call the tool 3 times". It decided.
#   - Goal-directed: it keeps looping until the goal is met...
#   - ...or until a limit (max_iter, max_execution_time) stops it.
#     With max_iter=2 it must stop early: missing data, or no answer at all.
