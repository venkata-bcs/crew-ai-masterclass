"""
06 - Guardrails: automatically check an answer and make the agent retry.

A guardrail is a normal Python function. It receives the task output and returns
    (True,  value)          -> accepted
    (False, "what's wrong") -> the agent tries again with that feedback
Run:  .venv\\Scripts\\python scripts\\basic-examples\\06_guardrail.py "our new coffee shop"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.tasks.task_output import TaskOutput

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

MAX_CHARS = 200


def check_post(output: TaskOutput) -> tuple[bool, str]:
    text = output.raw.strip()
    print(f"\n[guardrail] checking {len(text)} chars ...")
    if len(text) > MAX_CHARS:
        return False, f"Too long: {len(text)} characters. Rewrite it in under {MAX_CHARS}."
    if "#" not in text:
        return False, "Missing a hashtag. Add at least one #hashtag."
    print("[guardrail] passed ✅")
    return True, text


marketer = Agent(
    role="Social Media Marketer",
    goal="Write catchy, short social media posts",
    backstory="You know that short posts with a hashtag perform best.",
    llm=llm,
)

task = Task(
    description="Write one social media post announcing {product}.",
    expected_output=f"A single post under {MAX_CHARS} characters with at least one hashtag.",
    agent=marketer,
    guardrail=check_post,
    guardrail_max_retries=3,  # give up after 3 failed attempts
)

product = sys.argv[1] if len(sys.argv) > 1 else "our new coffee shop opening on Friday"
result = Crew(agents=[marketer], tasks=[task]).kickoff(inputs={"product": product})
print("\n===== FINAL POST =====\n")
print(result.raw)
