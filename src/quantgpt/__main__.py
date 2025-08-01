# src/quantgpt/__main__.py
from __future__ import annotations

import argparse
from quantgpt.utils.env import load_env
from quantgpt.config import load_config
from quantgpt.llm.client import LLMClient

def main() -> None:
    print("[DEBUG] Starting QuantGPT main()")
    parser = argparse.ArgumentParser(description="QuantGPT launcher")
    parser.add_argument("--profile", default=None, help="Config profile to load (e.g., fast-local)")
    parser.add_argument("--prompt", default="Say hello from QuantGPT.", help="Quick test prompt")
    args = parser.parse_args()

    load_env()  # loads .env if present
    cfg = load_config(profile=args.profile)
    llm = LLMClient(cfg)

    print(f"[QuantGPT] Using model: {llm.model}")
    out = llm.chat(
        args.prompt,
        system="You are QuantGPT, an agent for cryptographic and quantum risk research.",
    )
    print("\n--- Assistant ---\n")
    print(out)

if __name__ == "__main__":
    main()
