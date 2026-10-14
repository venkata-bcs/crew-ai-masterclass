"""
The agent's "brain": an NVIDIA-hosted LLM.

Keys live in settings.config at the repo root (git-ignored), one per line:
    NVDIA_API_KEY='nvapi-...'
    NVIDIA_MODEL='nvidia/nemotron-3-super-120b-a12b'   # optional override

NVIDIA's API speaks the OpenAI protocol, so CrewAI's built-in OpenAI provider
can call it directly - we only swap the base_url.
"""

import re
from pathlib import Path

from crewai import LLM

SETTINGS_FILE = Path(__file__).resolve().parents[2] / "settings.config"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-3-super-120b-a12b"


def load_settings(path: Path = SETTINGS_FILE) -> dict[str, str]:
    """Parse KEY='value' lines (spaces and quotes optional)."""
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Add a line like: NVDIA_API_KEY='nvapi-...'")
    settings = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"\s*([A-Za-z_]\w*)\s*=\s*['\"]?(.*?)['\"]?\s*$", line)
        if match:
            settings[match.group(1)] = match.group(2)
    return settings


def create_llm() -> LLM:
    settings = load_settings()
    # Accept both spellings; the existing settings.config uses "NVDIA".
    api_key = settings.get("NVIDIA_API_KEY") or settings.get("NVDIA_API_KEY")
    if not api_key:
        raise KeyError(f"No NVIDIA_API_KEY / NVDIA_API_KEY found in {SETTINGS_FILE}")

    return LLM(
        model=settings.get("NVIDIA_MODEL", DEFAULT_MODEL),
        custom_openai=True,  # force the OpenAI-compatible client
        base_url=NVIDIA_BASE_URL,
        api_key=api_key,
        temperature=0.2,  # low = stick to the facts
        timeout=180,
    )
