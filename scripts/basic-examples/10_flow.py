"""
10 - Flows: you control the steps, with state and if/else routing.

@start   -> runs first
@router  -> looks at the state and returns a route name
@listen  -> runs when a step (or route name) finishes
self.state -> a shared dict that every step can read and write
Run:  .venv\\Scripts\\python scripts\\basic-examples\\10_flow.py "How do I reverse a list in Python?"
      .venv\\Scripts\\python scripts\\basic-examples\\10_flow.py "Why is the sky blue?"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.flow.flow import Flow, listen, router, start

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


def ask_expert(role: str, backstory: str, question: str) -> str:
    """A tiny one-agent crew, used inside the flow."""
    expert = Agent(role=role, goal="Answer questions clearly and briefly", backstory=backstory, llm=llm)
    task = Task(description=question, expected_output="A clear answer in under 120 words.", agent=expert)
    return Crew(agents=[expert], tasks=[task]).kickoff().raw


class HelpDeskFlow(Flow):
    @start()
    def receive_question(self):
        print(f"[start]  question: {self.state['question']}")

    @router(receive_question)
    def classify(self):
        label = llm.call(
            "Reply with exactly one word, CODING or GENERAL. "
            f"Is this question about programming?\n\n{self.state['question']}"
        )
        route = "coding" if "CODING" in label.upper() else "general"
        print(f"[router] -> {route}")
        return route

    @listen("coding")
    def coding_expert(self):
        return ask_expert("Senior Python Developer", "You explain code with tiny examples.", self.state["question"])

    @listen("general")
    def general_expert(self):
        return ask_expert("Science Teacher", "You explain things with everyday analogies.", self.state["question"])


question = sys.argv[1] if len(sys.argv) > 1 else "How do I reverse a list in Python?"
# inputs go into self.state; kickoff() returns the last step's return value
answer = HelpDeskFlow().kickoff(inputs={"question": question})
print("\n===== ANSWER =====\n")
print(answer)
