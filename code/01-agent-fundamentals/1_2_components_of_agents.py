"""
1.2 Components of Agents
Module 1 · Agent Fundamentals | Read first: md/01-agent-fundamentals/1_2_components_of_agents.md

What you'll learn:
  An agent = LLM (brain) + role/goal/backstory (identity) + tools (hands)
             + settings (limits).
  We build one agent, run it, and PEEK at the hidden prompt CrewAI builds
  from those parts, so you can see where each component ends up.

Run (from the repo root):
  .venv\\Scripts\\python code\\01-agent-fundamentals\\1_2_components_of_agents.py
"""

import os
import re
import sys
import textwrap
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import LLMCallStartedEvent, crewai_event_bus
from crewai.tools import tool

# --- Component 1: the LLM (brain) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# --- Component 2: a tool (hands) ---
@tool("Recipe finder")
def find_recipe(ingredient: str) -> str:
    """Find a simple recipe that uses the given main ingredient."""
    recipes = {"egg": "Omelette: whisk 2 eggs, cook 2 min each side.", "rice": "Fried rice: fry cold rice with veg and soy."}
    return recipes.get(ingredient.lower().strip(), "No recipe found. Suggest something simple.")


# --- Components 3-5: identity (role, goal, backstory) + 6: settings ---
chef = Agent(
    role="Home Chef",  # 3. WHO it is
    goal="Suggest a quick dinner using what the user has",  # 4. WHAT it wants
    backstory="You cook fast weeknight meals and keep instructions short.",  # 5. HOW it behaves
    tools=[find_recipe],
    llm=llm,
    max_iter=3,  # 6. settings: at most 3 think->act loops
    allow_delegation=False,  #    no teammates to ask
)

# --- Capture the prompt CrewAI actually sends to the LLM (first call only) ---
captured = []


@crewai_event_bus.on(LLMCallStartedEvent)
def capture_prompt(source, event):
    if not captured and isinstance(event.messages, list):
        captured.extend(event.messages)


task = Task(description="I have eggs. What can I cook in 10 minutes?", expected_output="One dish and 3 short steps.", agent=chef)
result = Crew(agents=[chef], tasks=[task]).kickoff()
crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== RESULT =====\n")
print(result.raw)

print("\n===== THE HIDDEN PROMPT (first LLM call) =====")
for message in captured:
    print(f"\n--- role: {message['role']} ---")
    print(textwrap.shorten(str(message["content"]), width=700, placeholder=" [...]"))

print("\n===== WHERE EACH COMPONENT WENT =====\n")
system_text = " ".join(str(m["content"]) for m in captured)
for label, value in [("role", chef.role), ("goal", chef.goal), ("backstory", chef.backstory[:30])]:
    print(f"  {label:<10} found in prompt: {'✅' if value in system_text else '❌'}  ({value!r})")
print(f"  {'tool':<10} sent as a tool definition: {find_recipe.name!r}")

# ---------------------------------------------------------------
# Takeaways
#   - role/goal/backstory are not magic: they become text in the prompt.
#   - Tools are described to the LLM so it can choose to call them.
#   - Better descriptions = better behaviour. That's "prompting" an agent.
