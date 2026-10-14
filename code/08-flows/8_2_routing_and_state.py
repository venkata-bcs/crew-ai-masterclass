"""
8.2 Routing & State
Module 8 · Flows | Read first: md/08-flows/8_2_routing_and_state.md

What you'll learn:
  - Structured state: a Pydantic model instead of a loose dict
  - @router: look at the state, return a label, only that branch runs
  - or_(...): one step that runs after ANY of several branches
  Demo: a support-ticket triage flow (billing / tech / other).

Run (from the repo root):
  .venv\\Scripts\\python code\\08-flows\\8_2_routing_and_state.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM
from crewai.flow.flow import Flow, listen, or_, router, start
from pydantic import BaseModel

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# 1) Structured state: typed fields with defaults. Typos become errors, not bugs.
class TicketState(BaseModel):
    ticket: str = ""
    category: str = ""
    reply: str = ""
    handled_by: str = ""


class TriageFlow(Flow[TicketState]):
    @start()
    def receive(self):
        print(f"\n🎫 {self.state.ticket}")

    # 2) The router returns a LABEL. Only listeners of that label run.
    @router(receive)
    def classify(self):
        label = llm.call(
            "Classify this support ticket. Reply with exactly one word: BILLING, TECH or OTHER.\n\n" + self.state.ticket
        ).strip().upper()
        self.state.category = next((c for c in ("BILLING", "TECH") if c in label), "OTHER").lower()
        return self.state.category

    @listen("billing")
    def billing_team(self):
        self.state.handled_by = "Billing team"
        self.state.reply = llm.call(f"As a polite billing agent, reply in 2 sentences to: {self.state.ticket}")

    @listen("tech")
    def tech_team(self):
        self.state.handled_by = "Tech support"
        self.state.reply = llm.call(f"As a patient tech support agent, give 2 troubleshooting steps for: {self.state.ticket}")

    @listen("other")
    def general_team(self):
        self.state.handled_by = "General inbox"
        self.state.reply = "Thanks for reaching out! A team member will reply within 24 hours."  # no LLM needed

    # 3) or_: runs after whichever branch actually ran.
    @listen(or_(billing_team, tech_team, general_team))
    def send_reply(self):
        self.state.reply = " ".join(str(self.state.reply).split())  # tidy: one line
        return self.state  # the flow's final result


TICKETS = [
    "I was charged twice for my subscription this month.",
    "The app crashes every time I upload a photo.",
    "Do you have a office in Lisbon? I'd love to visit.",
]

results = []
for ticket in TICKETS:
    state = TriageFlow().kickoff(inputs={"ticket": ticket})  # a fresh flow per ticket
    results.append(state)

# Print after the flows finish (CrewAI's live console display can hide prints made mid-flow)
print("\n===== TRIAGE =====")
for state in results:
    print(f"\n🎫 {state.ticket}")
    print(f"   router -> {state.category}")
    print(f"   {state.handled_by}: {state.reply[:160]}...")

print("\n===== SUMMARY =====\n")
for state in results:
    print(f"  {state.category:<8} -> {state.handled_by:<14} | {state.ticket[:45]}")

# ---------------------------------------------------------------
# Takeaways
#   - Flow[YourModel] gives typed, auto-completed state: self.state.ticket.
#   - @router = if/else for your pipeline. Labels are just strings.
#   - Not every branch needs an LLM ("other" is plain code).
#   - or_(a, b, c) joins branches; and_(a, b) waits for ALL of them.
