"""
6.2 Guardrails
Module 6 · Reliable Outputs | Read first: md/06-reliable-outputs/6_2_guardrails.md

What you'll learn:
  A guardrail is a Python function that checks a task's output.
      return (True,  value)        -> accepted
      return (False, "feedback")   -> the agent retries, WITH your feedback
  We set strict rules for a product tagline and log every attempt.

Run (from the repo root):
  .venv\\Scripts\\python code\\06-reliable-outputs\\6_2_guardrails.py
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

PRODUCT = "BrewBot"
attempts = []


# The guardrail: plain Python rules, checked after every attempt.
def tagline_rules(output: TaskOutput) -> tuple[bool, str]:
    text = output.raw.strip().strip('"')
    problems = []
    if len(text.split()) != 5:
        problems.append(f"must be EXACTLY 5 words (you wrote {len(text.split())})")
    if PRODUCT not in text:
        problems.append(f"must include the product name '{PRODUCT}'")
    if "!" in text:
        problems.append("must not use exclamation marks")
    if re.search(r"https?://|www\.", text):
        problems.append("must not contain links")
    # A "hidden" brand rule the copywriter was never told about. The feedback teaches it.
    if not text.endswith("."):
        problems.append("must end with a full stop (brand style guide)")

    attempts.append((text, problems))
    print(f"\n[guardrail] attempt {len(attempts)}: {text!r} -> {'✅ pass' if not problems else '❌ ' + '; '.join(problems)}")
    if problems:
        return False, "Rewrite the tagline. It " + "; it ".join(problems) + "."
    return True, text


copywriter = Agent(
    role="Copywriter",
    goal="Write punchy product taglines",
    backstory="You love bold, exciting taglines.",  # tempts it to break the rules!
    llm=llm,
)

task = Task(
    description=f"Write a tagline for {PRODUCT}, a smart coffee machine that brews when your alarm rings.",
    expected_output=f"Only the tagline: exactly 5 words, includes '{PRODUCT}', no '!' and no links.",
    agent=copywriter,
    guardrail=tagline_rules,
    guardrail_max_retries=3,  # give up after 3 retries
)

try:
    result = Crew(agents=[copywriter], tasks=[task]).kickoff()
    final = result.raw
except Exception as e:  # noqa: BLE001 - raised when every retry fails the guardrail
    final = f"(no tagline passed after {len(attempts)} attempts: {type(e).__name__})"

print("\n===== ATTEMPT LOG =====\n")
for i, (text, problems) in enumerate(attempts, 1):
    print(f"  {i}. {'✅' if not problems else '❌'} {text}")
print(f"\nFINAL: {final}")

# ---------------------------------------------------------------
# Takeaways
#   - Guardrails turn "please follow the rules" into "you MUST follow the rules".
#   - The feedback string tells the agent exactly what to fix.
#   - Use code for checkable rules (length, words, format, banned content).
#   - Combine with output_pydantic (6.1): Pydantic checks SHAPE, guardrails check CONTENT.
