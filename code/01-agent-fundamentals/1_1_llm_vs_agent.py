"""
1.1 LLM vs Agent
Module 1 · Agent Fundamentals | Read first: md/01-agent-fundamentals/1_1_llm_vs_agent.md

What you'll learn:
  An LLM can only ANSWER from what it already knows.
  An agent can DECIDE to use tools, look at the results, and then answer.
  We ask both the same question, which needs today's date and exact maths.

Run (from the repo root):
  .venv\\Scripts\\python code\\01-agent-fundamentals\\1_1_llm_vs_agent.py
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
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

QUESTION = "What is 17.5% of 2,348.60, and how many days are left from today until 2027-03-15?"

# ---------------------------------------------------------------
# Part 1: the plain LLM. One call, no tools, no loop.
# It doesn't know today's date and does maths "in its head".
# ---------------------------------------------------------------
print("===== 1. PLAIN LLM (just answers) =====\n")
print(llm.call(QUESTION + " Answer in two short sentences."))


# ---------------------------------------------------------------
# Part 2: an agent. Same brain, plus tools and a reasoning loop.
# ---------------------------------------------------------------
@tool("Calculator")
def calculator(expression: str) -> str:
    """Evaluate a simple arithmetic expression exactly, e.g. '2348.60 * 17.5 / 100'."""
    if not re.fullmatch(r"[\d\s.+\-*/()]+", expression):  # only allow plain maths
        return "Only numbers and + - * / ( ) are allowed."
    return str(round(eval(expression), 4))  # noqa: S307 - input is restricted above


@tool("Today's date")
def todays_date() -> str:
    """Return today's date as YYYY-MM-DD."""
    return date.today().isoformat()


@tool("Days between dates")
def days_between(start: str, end: str) -> str:
    """Number of days from start to end. Dates as YYYY-MM-DD."""
    return str((date.fromisoformat(end) - date.fromisoformat(start)).days)


assistant = Agent(
    role="Careful Assistant",
    goal="Answer questions exactly, using tools for dates and maths",
    backstory="You never guess numbers. You always check with a tool.",
    tools=[calculator, todays_date, days_between],
    llm=llm,
    verbose=True,  # watch it decide which tool to use
)
task = Task(description=QUESTION, expected_output="Two short sentences with the exact numbers.", agent=assistant)

print("\n===== 2. AGENT (decides, uses tools, then answers) =====\n")
result = Crew(agents=[assistant], tasks=[task]).kickoff()
print(result.raw)

# ---------------------------------------------------------------
# Part 3: the real answer, computed in plain Python, to compare.
# ---------------------------------------------------------------
print("\n===== 3. TRUTH (plain Python) =====\n")
print(f"17.5% of 2,348.60 = {2348.60 * 17.5 / 100:.2f}")
print(f"Days from {date.today()} to 2027-03-15 = {(date(2027, 3, 15) - date.today()).days}")

# ---------------------------------------------------------------
# Takeaways
#   - LLM: text in -> text out. It can't check anything.
#   - Agent: LLM + tools + a loop (think -> act -> observe -> answer).
#   - Compare section 1 with section 3: the plain LLM may guess the date.
