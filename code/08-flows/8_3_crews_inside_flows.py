"""
8.3 Crews inside Flows
Module 8 · Flows | Read first: md/08-flows/8_3_crews_inside_flows.md

What you'll learn:
  The newsletter from 2.2, rebuilt as a Flow with a QUALITY GATE:
      research (crew) -> write (crew) -> quality gate (code)
                            ^                 |
                            └─── "revise" ────┘   (with feedback, max 3 tries)
                                              |
                                          "publish" -> save file
  Crews do the creative work; plain code enforces the rules and the loop.

Run (from the repo root):
  .venv\\Scripts\\python code\\08-flows\\8_3_crews_inside_flows.py "Python tips"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
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

MAX_WORDS = 90  # the editor's limit. The writer's brief doesn't mention it, like real life
MAX_ATTEMPTS = 3


# --- Two small crews, each built by a function ---
def research_crew() -> Crew:
    researcher = Agent(role="Researcher", goal="Find 3 useful ideas about {topic}", backstory="Practical and accurate.", llm=llm)
    task = Task(description="Find 3 ideas about {topic} a beginner can use this week.", expected_output="3 bullets with one example each.", agent=researcher)
    return Crew(agents=[researcher], tasks=[task])


def writing_crew() -> Crew:
    writer = Agent(role="Newsletter Writer", goal="Write tight, friendly newsletters", backstory="Every word earns its place.", llm=llm)
    task = Task(
        description=(
            "Write a newsletter about {topic} from these notes:\n{notes}\n\n"
            "Editor feedback from last attempt (may be empty): {feedback}"
        ),
        expected_output="Raw Markdown: a '# ' title, one short section per idea, and a final line starting 'Try this week:'.",
        agent=writer,
    )
    return Crew(agents=[writer], tasks=[task])


# --- Shared state for the whole flow ---
class NewsletterState(BaseModel):
    topic: str = ""
    notes: str = ""
    draft: str = ""
    feedback: str = ""
    attempts: int = 0


class NewsletterFlow(Flow[NewsletterState]):
    @start()
    def research(self):
        self.state.notes = research_crew().kickoff(inputs={"topic": self.state.topic}).raw
        print(f"[research] {len(self.state.notes.split())} words of notes")

    # Runs after research, AND again every time the gate says "revise"
    @listen(or_(research, "revise"))
    def write(self):
        self.state.attempts += 1
        inputs = {"topic": self.state.topic, "notes": self.state.notes, "feedback": self.state.feedback}
        self.state.draft = writing_crew().kickoff(inputs=inputs).raw.strip()
        print(f"[write]    attempt {self.state.attempts}: {len(self.state.draft.split())} words")

    # The quality gate: plain code, no LLM. Returns the next label.
    @router(write)
    def quality_gate(self):
        draft = self.state.draft
        problems = []
        if len(draft.split()) > MAX_WORDS:
            problems.append(f"cut it to under {MAX_WORDS} words (now {len(draft.split())})")
        if not draft.startswith("# "):
            problems.append("start with a '# ' title")
        if "Try this week:" not in draft:
            problems.append("end with a line starting 'Try this week:'")

        if problems and self.state.attempts < MAX_ATTEMPTS:
            self.state.feedback = "; ".join(problems)
            print(f"[gate]     ❌ revise: {self.state.feedback}")
            return "revise"
        print(f"[gate]     {'✅ passed' if not problems else '⚠️ publishing anyway (max attempts)'}")
        return "publish"

    @listen("publish")
    def save_newsletter(self):  # a step can't have the same name as the label it listens to
        slug = re.sub(r"[^a-z0-9]+", "_", self.state.topic.lower()).strip("_")
        path = Path(__file__).parent / "output" / f"newsletter_{slug}.md"
        path.parent.mkdir(exist_ok=True)
        path.write_text(self.state.draft + "\n", encoding="utf-8")
        print(f"[publish]  saved {path.name}")
        return self.state.draft


topic = sys.argv[1] if len(sys.argv) > 1 else "Python tips"
flow = NewsletterFlow()
newsletter = flow.kickoff(inputs={"topic": topic})

print("\n===== NEWSLETTER =====\n")
print(newsletter)
print(f"\nAttempts: {flow.state.attempts}")

# ---------------------------------------------------------------
# Takeaways
#   - A crew is just a step: crew.kickoff() inside a flow method.
#   - State carries data between crews (notes -> writer, feedback -> rewrite).
#   - A router that points back to an earlier label creates a loop. ALWAYS cap it.
#   - Code checks rules reliably; LLMs do the creative part.
