"""The core agentic loop: drives Claude with the accounting/advising toolset.

Uses streaming and a manual tool-use loop so tool calls can be surfaced to the
user and executed against the shared SQLite ledger.
"""

from __future__ import annotations

import json
import os
import sys

import anthropic

from .prompts import SYSTEM_PROMPT
from .store import Store
from .tools import TOOLS, run_tool

MODEL = os.environ.get("FINANCE_MODEL", "claude-opus-4-8")
MAX_TOKENS = 16000
# Cap tool round-trips per turn so a misbehaving loop can't run unbounded.
MAX_ITERATIONS = 20


class FinanceAgent:
    def __init__(self, store: Store | None = None, *, show_tools: bool = True,
                 client: anthropic.Anthropic | None = None):
        self.store = store or Store()
        self.client = client or anthropic.Anthropic()
        self.show_tools = show_tools
        self.messages: list[dict] = []

    def reset(self) -> None:
        self.messages = []

    # ------------------------------------------------------------------ #
    def send(self, user_message: str) -> str:
        """Run one user turn to completion; returns the final assistant text.

        Streams assistant text to stdout as it arrives and prints tool activity.
        """
        self.messages.append({"role": "user", "content": user_message})
        final_text_parts: list[str] = []

        for _ in range(MAX_ITERATIONS):
            with self.client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                thinking={"type": "adaptive"},
                messages=self.messages,
            ) as stream:
                for text in stream.text_stream:
                    sys.stdout.write(text)
                    sys.stdout.flush()
                response = stream.get_final_message()

            # Record the assistant turn verbatim (preserves tool_use blocks).
            self.messages.append({"role": "assistant", "content": response.content})
            final_text_parts = [b.text for b in response.content if b.type == "text"]

            if response.stop_reason != "tool_use":
                sys.stdout.write("\n")
                break

            # Execute every requested tool and feed results back.
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                if self.show_tools:
                    sys.stdout.write(
                        f"\n  \033[2m↳ {block.name}({_fmt_args(block.input)})\033[0m\n"
                    )
                    sys.stdout.flush()
                result = run_tool(self.store, block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
            self.messages.append({"role": "user", "content": tool_results})
        else:
            sys.stdout.write("\n[Reached the tool-iteration limit for this turn.]\n")

        return "".join(final_text_parts)


def _fmt_args(d: dict) -> str:
    try:
        s = json.dumps(d, default=str)
    except Exception:
        s = str(d)
    return s if len(s) <= 120 else s[:117] + "..."
