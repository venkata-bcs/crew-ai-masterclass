"""
7.1 Hierarchical Process
Module 7 · Advanced Crews | Read first: md/07-advanced-crews/7_1_hierarchical_process.md

What you'll learn:
  A small "agency": a manager plus 3 specialists. The manager reads the brief,
  delegates pieces to the right specialist, checks the answers and combines them.
  We use a CUSTOM manager_agent (instead of manager_llm), and log every
  delegation plus the LLM calls per agent.

Run (from the repo root):
  .venv\\Scripts\\python code\\07-advanced-crews\\7_1_hierarchical_process.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task
from crewai.events import LLMCallCompletedEvent, ToolUsageFinishedEvent, crewai_event_bus

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# --- Watch the manager work ---
delegations, llm_calls = [], []


@crewai_event_bus.on(ToolUsageFinishedEvent)
def on_delegate(source, event):
    # The manager delegates through built-in tools named like "Delegate work to coworker"
    if "coworker" in event.tool_name.lower():
        args = event.tool_args if isinstance(event.tool_args, dict) else {}
        delegations.append((event.tool_name, args.get("coworker", "?"), str(args.get("task", ""))[:70]))


@crewai_event_bus.on(LLMCallCompletedEvent)
def on_llm(source, event):
    llm_calls.append(event.agent_role or "-")


# --- The custom manager: you control its personality and standards ---
director = Agent(
    role="Agency Director",
    goal="Deliver a complete, consistent launch kit by delegating to the right specialist",
    backstory="You never do specialist work yourself. You brief clearly and check every answer.",
    llm=llm,
    allow_delegation=True,  # a manager MUST be allowed to delegate
)

# --- The specialists (no delegation: they just do their job) ---
copywriter = Agent(role="Copywriter", goal="Write short, catchy marketing copy", backstory="Punchy and clear.", llm=llm, allow_delegation=False)
designer = Agent(role="Visual Designer", goal="Describe simple, striking visuals", backstory="Minimalist style.", llm=llm, allow_delegation=False)
seo = Agent(role="SEO Specialist", goal="Pick search keywords people really use", backstory="Data-driven.", llm=llm, allow_delegation=False)

# --- One brief, NO agent assigned: the director decides who does what ---
brief = Task(
    description=(
        "Create a launch kit for 'PawPal', a GPS collar for dogs: "
        "1) a headline and a 2-sentence description, "
        "2) a description of the hero image, "
        "3) 5 SEO keywords."
    ),
    expected_output="A launch kit with 3 labelled sections: Copy, Visual, Keywords.",
)

crew = Crew(
    agents=[copywriter, designer, seo],  # the manager is NOT in this list
    tasks=[brief],
    process=Process.hierarchical,
    manager_agent=director,  # custom manager (alternative: manager_llm=llm)
)
result = crew.kickoff()
crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== LAUNCH KIT =====\n")
print(result.raw)

print("\n===== DELEGATION LOG =====\n")
for tool_name, coworker, what in delegations:
    print(f"  Director -> {coworker:<16} [{tool_name}] {what}...")

print("\n===== LLM CALLS PER AGENT =====\n")
for role in dict.fromkeys(llm_calls):
    print(f"  {role:<16} {llm_calls.count(role)}")
print(f"  {'TOTAL':<16} {len(llm_calls)}")

# ---------------------------------------------------------------
# Takeaways
#   - Hierarchical = tasks without a fixed agent + a manager who delegates.
#   - manager_llm: CrewAI creates a default manager. manager_agent: you define it.
#   - The manager's thinking costs extra LLM calls (see the count). Use it when
#     the work really needs planning; otherwise sequential is cheaper.
