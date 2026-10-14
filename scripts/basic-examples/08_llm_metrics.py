"""
08 - LLM metrics: know your LLM, and measure every call your crew makes.

Prints three things:
  1. LLM details  - model, provider, endpoint, temperature, (masked) key
  2. Per-call metrics, from CrewAI's events:
       Read time     = seconds until the first VISIBLE token. Includes reading the prompt
                       AND any hidden reasoning, which NVIDIA does not stream.
       Gen time      = seconds spent streaming the visible answer (response - read time)
       Response time = seconds from request to last token
       Speed         = output tokens (incl. reasoning) per second of total response time
       Read tokens   = input tokens served from the provider's prompt cache
       Input / Output / Reasoning tokens (reasoning = hidden "thinking")
  3. A summary - totals, averages, slowest call, where the time went

Run:  .venv\\Scripts\\python scripts\\basic-examples\\08_llm_metrics.py "the moon"
"""

import os
import re
import sys
import time
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import LLMCallCompletedEvent, LLMCallStartedEvent, LLMStreamChunkEvent, crewai_event_bus

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
key_name = "NVIDIA_API_KEY" if "NVIDIA_API_KEY" in cfg else "NVDIA_API_KEY"
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg[key_name],
    temperature=0.7,  # 0 = predictable, 1+ = creative
    stream=True,  # needed to time the first token ("read time")
)


# --- 1. LLM details ---
def mask(secret: str) -> str:
    """Show just enough of a key to recognise it, never the whole thing."""
    return f"{secret[:6]}...{secret[-4:]}" if len(secret) > 12 else "****"


def show(value) -> str:
    return "provider default" if value is None else str(value)


print("===== LLM DETAILS =====\n")
details = {
    "Model": llm.model,
    "Provider": "NVIDIA (OpenAI-compatible API)",
    "Client": f"CrewAI {type(llm).__name__} (provider='{llm.provider}')",
    "Endpoint": llm.base_url,
    "Temperature": show(llm.temperature),
    "Max tokens": show(llm.max_tokens),
    "Top-p": show(llm.top_p),
    "Streaming": llm.stream,
    "API key": f"{mask(cfg[key_name])}  ({len(cfg[key_name])} chars, '{key_name}' in {SETTINGS.name})",
}
for label, value in details.items():
    print(f"  {label:<12} {value}")

# --- 2. Record each LLM call, keyed by its call_id ---
calls = {}


@crewai_event_bus.on(LLMCallStartedEvent)
def call_started(source, event):
    calls[event.call_id] = {
        "agent": event.agent_role or "-",
        "messages": len(event.messages) if isinstance(event.messages, list) else 1,
        "start": time.perf_counter(),
        "chunks": 0,
    }


@crewai_event_bus.on(LLMStreamChunkEvent)
def chunk_arrived(source, event):
    call = calls.get(event.call_id)
    if call:
        call["chunks"] += 1
        call.setdefault("first_token", time.perf_counter())


@crewai_event_bus.on(LLMCallCompletedEvent)
def call_finished(source, event):
    call = calls.get(event.call_id)
    if call:
        call["end"] = time.perf_counter()
        call["usage"] = event.usage or {}
        call["finish"] = event.finish_reason or "-"
        call["answer_chars"] = len(str(event.response or ""))


# --- 3. A simple two-agent crew to measure ---
writer = Agent(
    role="Writer",
    goal="Write short, fun facts",
    backstory="You write for a kids' science magazine.",
    llm=llm,
)
editor = Agent(
    role="Editor",
    goal="Make text shorter and clearer",
    backstory="You cut every unnecessary word.",
    llm=llm,
)
write = Task(
    description="Write 3 fun facts about {topic}.",
    expected_output="3 numbered facts, one sentence each.",
    agent=writer,
)
edit = Task(
    description="Shorten each fact to at most 12 words.",
    expected_output="The same 3 numbered facts, shorter.",
    agent=editor,
    context=[write],
)

topic = sys.argv[1] if len(sys.argv) > 1 else "the moon"
wall_start = time.perf_counter()
result = Crew(agents=[writer, editor], tasks=[write, edit]).kickoff(inputs={"topic": topic})
wall_time = time.perf_counter() - wall_start
crewai_event_bus.flush()  # let CrewAI finish its own printing first

print("\n===== RESULT =====\n")
print(result.raw)

# --- 4. Work out the numbers for each finished call ---
rows = []
for c in calls.values():
    if "end" not in c:
        continue
    u = c["usage"]
    read_time = c.get("first_token", c["end"]) - c["start"]
    response_time = c["end"] - c["start"]
    gen_time = max(response_time - read_time, 1e-6)
    out_tok = u.get("completion_tokens", 0)
    rows.append(
        {
            **c,
            "read_time": read_time,
            "gen_time": gen_time,
            "response_time": response_time,
            "speed": out_tok / max(response_time, 1e-6),
            "read_tok": u.get("cached_prompt_tokens", 0),
            "in_tok": u.get("prompt_tokens", 0),
            "out_tok": out_tok,
            "reason_tok": u.get("reasoning_tokens", 0),
        }
    )

# Table A: where the time went
print("\n===== LLM METRICS: TIMING =====\n")
print(f"{'#':>2}  {'Agent':<8} {'Msgs':>4} {'Read time':>9} {'Gen time':>8} {'Response':>8} {'Speed':>9} {'Chunks':>6}  Finish")
print("-" * 78)
for i, r in enumerate(rows, 1):
    print(
        f"{i:>2}  {r['agent']:<8} {r['messages']:>4} {r['read_time']:>8.2f}s {r['gen_time']:>7.2f}s "
        f"{r['response_time']:>7.2f}s {r['speed']:>5.0f} t/s {r['chunks']:>6}  {r['finish']}"
    )

# Table B: where the tokens went
print("\n===== LLM METRICS: TOKENS =====\n")
print(f"{'#':>2}  {'Agent':<8} {'Read tok':>8} {'Input':>7} {'Output':>7} {'Reasoning':>9} {'Visible':>7} {'Total':>7} {'Answer chars':>12}")
print("-" * 78)
for i, r in enumerate(rows, 1):
    visible = r["out_tok"] - r["reason_tok"]
    print(
        f"{i:>2}  {r['agent']:<8} {r['read_tok']:>8,} {r['in_tok']:>7,} {r['out_tok']:>7,} {r['reason_tok']:>9,} "
        f"{visible:>7,} {r['in_tok'] + r['out_tok']:>7,} {r['answer_chars']:>12,}"
    )

# Summary
if rows:
    total = lambda key: sum(r[key] for r in rows)  # noqa: E731
    llm_time = total("response_time")
    slowest = max(rows, key=lambda r: r["response_time"])
    print("\n===== SUMMARY =====\n")
    summary = {
        "LLM calls": len(rows),
        "Wall-clock time": f"{wall_time:.2f}s  ({llm_time / wall_time:.0%} of it waiting on the LLM)",
        "Avg read time": f"{total('read_time') / len(rows):.2f}s per call",
        "Avg speed": f"{total('out_tok') / llm_time:.0f} output tokens/s (incl. reasoning)",
        "Tokens in / out": f"{total('in_tok'):,} / {total('out_tok'):,}  (ratio 1 : {total('out_tok') / max(total('in_tok'), 1):.1f})",
        "Hidden reasoning": f"{total('reason_tok'):,} tokens = {total('reason_tok') / max(total('out_tok'), 1):.0%} of output you never see",
        "Cache hits": f"{total('read_tok'):,} of {total('in_tok'):,} input tokens",
        "Slowest call": f"#{rows.index(slowest) + 1} {slowest['agent']} ({slowest['response_time']:.2f}s)",
    }
    for label, value in summary.items():
        print(f"  {label:<17} {value}")
