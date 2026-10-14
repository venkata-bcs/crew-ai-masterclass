"""
8.1 Flows in CrewAI
Module 8 · Flows | Read first: md/08-flows/8_1_flows_intro.md

What you'll learn:
  A Flow is a pipeline YOU control: plain Python steps and LLM steps,
  wired together with decorators.
      @start()             -> runs first
      @listen(step)        -> runs when `step` finishes, receives its return value
  Demo: fetch a Wikipedia summary (code) -> simplify it (LLM) -> save it (code).

Run (from the repo root):
  .venv\\Scripts\\python code\\08-flows\\8_1_flows_intro.py "Photosynthesis"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

import requests
from crewai import LLM
from crewai.flow.flow import Flow, listen, start

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

OUTPUT_DIR = Path(__file__).parent / "output"


class ExplainerFlow(Flow):
    # Step 1 (plain code): fetch the facts. No LLM needed for this.
    @start()
    def fetch_summary(self):
        topic = self.state["topic"]  # set from kickoff(inputs=...)
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{topic.replace(' ', '_')}"
        data = requests.get(url, headers={"User-Agent": "crew-ai-masterclass/1.0"}, timeout=30).json()
        print(f"[1 fetch]    {len(data.get('extract', ''))} characters from Wikipedia")
        return data.get("extract", f"No summary found for {topic}.")

    # Step 2 (LLM): receives step 1's return value as `summary`.
    @listen(fetch_summary)
    def simplify(self, summary):
        print("[2 simplify] asking the LLM to rewrite it for a 10-year-old")
        return llm.call(f"Rewrite this for a 10-year-old in 3 short sentences:\n\n{summary}")

    # Step 3 (plain code): save the result. The flow's final return value.
    @listen(simplify)
    def save(self, simple_text):
        OUTPUT_DIR.mkdir(exist_ok=True)
        path = OUTPUT_DIR / f"{self.state['topic'].lower().replace(' ', '_')}_for_kids.md"
        path.write_text(f"# {self.state['topic']} (for kids)\n\n{simple_text.strip()}\n", encoding="utf-8")
        print(f"[3 save]     wrote {path.name}")
        return simple_text


topic = sys.argv[1] if len(sys.argv) > 1 else "Photosynthesis"
flow = ExplainerFlow()
answer = flow.kickoff(inputs={"topic": topic})  # inputs go into flow.state

print("\n===== RESULT =====\n")
print(answer.strip())
print(f"\nflow.state = {dict(flow.state)}")

# ---------------------------------------------------------------
# Takeaways
#   - Crew = agents decide HOW. Flow = you decide WHAT runs, WHEN.
#   - Mix plain code and LLM steps freely; use code where code is enough.
#   - Each @listen step receives the previous step's return value.
#   - self.state is shared by every step (here: the topic).
