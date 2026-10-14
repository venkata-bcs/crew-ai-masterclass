"""
9.4 Pattern: Human in the Loop (HITL)
Module 9 · Simple Patterns | Read first: md/09-simple-patterns/9_4_human_in_the_loop.md

PROBLEM:  An AI writes an email to a customer. You don't want it sent
          until a PERSON has read it and is happy with it.
SOLUTION: human_input=True on the task. The agent writes a draft, then
          STOPS and asks you in the terminal:
            - type feedback (e.g. "shorter, mention free delivery") -> it rewrites
            - press Enter with nothing typed                        -> approved
          Only then does the script "send" it.

Run (from the repo root), then answer in the terminal:
  .venv\\Scripts\\python code\\09-simple-patterns\\9_4_human_in_the_loop.py
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

writer = Agent(
    role="Customer Email Writer",
    goal="Write friendly emails that customers enjoy reading",
    backstory="You write warm, clear emails and happily take feedback.",
    llm=llm,
    verbose=True,  # needed so you can SEE each draft before you give feedback
)

email = Task(
    description="Write an email telling customer Maria that her order #4521 has been delayed by 2 days.",
    expected_output="A short email: subject line, greeting, 2-3 sentences, sign-off from 'The Shop Team'.",
    agent=writer,
    human_input=True,  # <- the agent pauses here and asks YOU before finishing
)

print("👀 The agent will show you a draft and ask for feedback.")
print("   Type changes and press Enter to get a new draft, or just press Enter to approve.\n")

result = Crew(agents=[writer], tasks=[email]).kickoff()

print("\n✅ APPROVED BY A HUMAN. Sending...\n")
print(result.raw.strip())
print("\n📧 Sent! (in a real app, this is where you'd call your email service)")

# ---------------------------------------------------------------
# Takeaways
#   - human_input=True = "show me before you finish".
#   - Use it for anything risky: emails to customers, payments, deleting data.
#   - The agent uses your feedback to improve the draft, so be specific.
