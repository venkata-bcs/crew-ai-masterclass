"""
2.4 CrewAI vs Chatbots
Module 2 · Thinking in Multi-Agent Systems | Read first: md/02-multi-agent-thinking/2_4_crewai_vs_chatbots.md

What you'll learn:
  A CHATBOT keeps a conversation going: you lead, it replies, turn by turn.
  A CREW takes a job, works on it, and hands back a finished result.
  Same goal (plan a weekend trip), both ways.

Run (from the repo root):
  .venv\\Scripts\\python code\\02-multi-agent-thinking\\2_4_crewai_vs_chatbots.py
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

# ---------------------------------------------------------------
# A) Chatbot: a list of messages that grows every turn.
#    YOU drive. Each reply is one LLM call. Nothing is "finished".
#    (User turns are scripted here so the demo runs on its own.)
# ---------------------------------------------------------------
print("===== A) CHATBOT: you lead, turn by turn =====")
history = [{"role": "system", "content": "You are a friendly travel chatbot. Reply in at most 2 sentences."}]
user_turns = [
    "I want a weekend trip from London.",
    "Somewhere by the sea, please.",
    "OK, what should I pack?",
]
for turn in user_turns:
    history.append({"role": "user", "content": turn})
    reply = llm.call(history)  # the WHOLE history goes in every time
    history.append({"role": "assistant", "content": reply})
    print(f"\n👤 {turn}\n🤖 {reply.strip()}")

# ---------------------------------------------------------------
# B) Crew: one request in, a complete deliverable out.
#    The AGENTS drive: plan the trip, then build the packing list.
# ---------------------------------------------------------------
print("\n\n===== B) CREW: one request in, a finished plan out =====")
planner = Agent(role="Trip Planner", goal="Plan a realistic seaside weekend from {city}", backstory="You plan simple, affordable trips.", llm=llm)
packer = Agent(role="Packing Expert", goal="Write a packing checklist for the planned trip", backstory="You never forget the essentials.", llm=llm)

plan = Task(description="Plan a 2-day seaside weekend trip from {city}.", expected_output="Destination, how to get there, Day 1 and Day 2 in 2-3 bullets each.", agent=planner)
pack = Task(description="Write a packing checklist for this exact trip.", expected_output="A checklist of 8-10 items with [ ] boxes.", agent=packer, context=[plan])

result = Crew(agents=[planner, packer], tasks=[plan, pack]).kickoff(inputs={"city": "London"})
print("\n" + result.tasks_output[0].raw.strip())
print("\n" + result.raw.strip())

print("\n===== THE DIFFERENCE =====\n")
rows = [
    ("Who leads?", "You, every turn", "The agents"),
    ("Output", "Replies in a chat", "A finished deliverable"),
    ("Memory", f"Message history ({len(history)} messages)", "Task context between agents"),
    ("Best for", "Open-ended conversation", "A job with a clear result"),
]
print(f"{'':<12} {'Chatbot':<32} Crew")
for label, chatbot, crew in rows:
    print(f"{label:<12} {chatbot:<32} {crew}")

# ---------------------------------------------------------------
# Takeaways
#   - Chatbots are conversations; crews are jobs.
#   - A crew can sit BEHIND a chatbot: the chat collects the request,
#     the crew does the work.
