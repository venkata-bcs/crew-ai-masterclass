"""
5.4 Building Custom Tools
Module 5 · Tools | Read first: md/05-tools/5_4_custom_tools.md

What you'll learn:
  Two ways to build your own tools, plus the things that make them robust:
    1) @tool decorator       quick: a function + a docstring
    2) BaseTool subclass     full control: a Pydantic args_schema validates inputs
    3) Errors                raise an exception -> the agent is told and can react
    4) Caching               same tool + same input = cached result, no re-run

Run (from the repo root):
  .venv\\Scripts\\python code\\05-tools\\5_4_custom_tools.py
"""

import os
import re
import sys
from pathlib import Path
from typing import Literal

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import ToolUsageErrorEvent, ToolUsageFinishedEvent, crewai_event_bus
from crewai.tools import BaseTool, tool
from pydantic import BaseModel, Field

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# ---------------------------------------------------------------
# 1) The quick way: @tool. Name in quotes, docstring = description,
#    type hints = the inputs the LLM must provide.
# ---------------------------------------------------------------
@tool("Km to miles")
def km_to_miles(km: float) -> str:
    """Convert kilometres to miles."""
    return f"{km} km = {km * 0.621371:.2f} miles"


# ---------------------------------------------------------------
# 2) The full way: BaseTool + a Pydantic schema for the inputs.
#    The schema documents AND validates every argument.
# ---------------------------------------------------------------
RATES_TO_USD = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27, "INR": 0.012}
real_runs = []  # proves caching: only real executions are added here


class CurrencyInput(BaseModel):
    amount: float = Field(description="The amount of money to convert")
    from_currency: Literal["USD", "EUR", "GBP", "INR"] = Field(description="Currency code to convert from")
    to_currency: Literal["USD", "EUR", "GBP", "INR"] = Field(description="Currency code to convert to")


class CurrencyConverter(BaseTool):
    name: str = "Currency converter"
    description: str = "Convert an amount between USD, EUR, GBP and INR using today's fixed demo rates."
    args_schema: type[BaseModel] = CurrencyInput

    def _run(self, amount: float, from_currency: str, to_currency: str) -> str:
        real_runs.append((amount, from_currency, to_currency))
        # 3) Errors: raise with a helpful message. CrewAI hands it to the agent.
        if amount <= 0:
            raise ValueError("Amount must be greater than zero. Ask the user for a positive amount.")
        converted = amount * RATES_TO_USD[from_currency] / RATES_TO_USD[to_currency]
        return f"{amount:.2f} {from_currency} = {converted:.2f} {to_currency}"


# Log every tool call: finished ones and failed ones
log = []


@crewai_event_bus.on(ToolUsageFinishedEvent)
def log_tool(source, event):
    log.append((event.tool_name, event.tool_args, "ok"))


@crewai_event_bus.on(ToolUsageErrorEvent)
def log_error(source, event):
    log.append((event.tool_name, event.tool_args, f"ERROR: {str(event.error)[:45]}"))


assistant = Agent(
    role="Travel Money Assistant",
    goal="Answer distance and money questions exactly, always with tools",
    backstory="You never convert anything in your head.",
    tools=[km_to_miles, CurrencyConverter()],
    llm=llm,
    cache=True,  # 4) Caching: identical tool calls reuse the first result (on by default)
)

task = Task(
    description=(
        "Do these in order, one tool call each: "
        "a) convert 42 km to miles; "
        "b) convert 250 USD to EUR; "
        "c) convert 250 USD to EUR again to double-check; "
        "d) convert -20 GBP to INR."
    ),
    expected_output="One line per item a-d with the result, or why it couldn't be done.",
    agent=assistant,
)

result = Crew(agents=[assistant], tasks=[task]).kickoff()

crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== RESULT =====\n")
print(result.raw)

print("\n===== TOOL LOG =====\n")
for name, args, status in log:
    print(f"  {name:<20} {str(args):<62} {status}")
asked = sum(1 for name, _, _ in log if "currency" in name)
print(f"\nCurrency converter: asked {asked}x, really executed {len(real_runs)}x -> {asked - len(real_runs)} answered from cache")
print(f"Real executions: {real_runs}")

# ---------------------------------------------------------------
# Takeaways
#   - @tool for quick tools; BaseTool + args_schema when inputs need rules.
#   - Literal[...] in the schema limits the LLM to valid choices.
#   - Raise clear errors: the agent reads them and adapts.
#   - Caching saves time and money on repeated identical calls.
