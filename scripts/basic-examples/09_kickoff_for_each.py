"""
09 - Reuse one crew for many inputs with kickoff_for_each().

Build the crew once, then run it for a list of inputs. One result per input.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\09_kickoff_for_each.py
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

translator = Agent(
    role="Translator",
    goal="Translate text accurately into {language}",
    backstory="A professional translator who keeps the original tone.",
    llm=llm,
)

task = Task(
    description="Translate this sentence into {language}: 'Teamwork makes the dream work.'",
    expected_output="Only the translated sentence, nothing else.",
    agent=translator,
)

crew = Crew(agents=[translator], tasks=[task])

inputs = [{"language": "French"}, {"language": "Spanish"}, {"language": "Hindi"}, {"language": "Japanese"}]
results = crew.kickoff_for_each(inputs=inputs)  # runs the crew 4 times
for inp, res in zip(inputs, results):
    print(f"{inp['language']:>10}: {res.raw.strip()}")
