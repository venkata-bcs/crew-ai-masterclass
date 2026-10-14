"""
9.2 Pattern: Multi Agent (a relay)
Module 9 · Simple Patterns | Read first: md/09-simple-patterns/9_2_multi_agent.md

PROBLEM:  You have messy meeting notes. You need a clean email to the team.
          That's two different skills: understanding notes, and writing well.
SOLUTION: TWO agents in a relay. The Note Taker pulls out the facts,
          then the Email Writer turns those facts into a friendly email.

Run (from the repo root):
  .venv\\Scripts\\python code\\09-simple-patterns\\9_2_multi_agent.py
"""

import os
import re
import sys
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

NOTES = """
mtg tues - sam, priya, li. website launch moved to 15 nov (design not ready).
priya to finish homepage by fri. li needs logo files from sam asap. budget ok.
next mtg thurs 10am
"""

# Agent 1: understands messy notes
note_taker = Agent(
    role="Note Taker",
    goal="Pull clear facts out of messy notes",
    backstory="You never miss a decision, a deadline or an owner.",
    llm=llm,
)
# Agent 2: writes nicely
email_writer = Agent(
    role="Email Writer",
    goal="Write short, friendly team emails",
    backstory="Your emails are clear, warm and easy to scan.",
    llm=llm,
)

# Task 1 -> Task 2: the output of the first is handed to the second
extract = Task(
    description="Extract the decisions, action items (with owners) and next meeting from these notes:\n{notes}",
    expected_output="Three short lists: Decisions, Action items (who + what + when), Next meeting.",
    agent=note_taker,
)
write = Task(
    description="Write an email to the team based on the extracted facts.",
    expected_output="An email with a subject line, a 1-line intro, and bullet points.",
    agent=email_writer,
    context=[extract],  # <- the relay: Email Writer receives Note Taker's facts
)

result = Crew(agents=[note_taker, email_writer], tasks=[extract, write]).kickoff(inputs={"notes": NOTES})

print("\n📝 STEP 1 - Note Taker's facts:\n")
print(result.tasks_output[0].raw.strip())
print("\n📧 STEP 2 - Email Writer's email:\n")
print(result.raw.strip())

# ---------------------------------------------------------------
# Takeaways
#   - Two different skills -> two agents, each good at one thing.
#   - context=[earlier_task] passes the work along, like a relay baton.
