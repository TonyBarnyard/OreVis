"""Deal workspaces and the conversation loop for the single-broker app.

Each deal is a folder on disk: the files the broker uploaded, the conversation
with Claude, and the Excel/Word/chart files the agent produced. PDFs and images
are sent to Claude through the Files API once, then referenced by id on later
turns; spreadsheets and Word files are converted to text.
"""

from __future__ import annotations

import csv
import io
import json
import mimetypes
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from openpyxl import load_workbook
from docx import Document

from .agent import MODEL, SYSTEM_PROMPT, build_tools

APP_PROMPT = SYSTEM_PROMPT + """

In this app the broker uploads a deal's documents and asks you for work in plain English. \
When you create a file with a tool, tell the broker its name; it appears in the app for \
download. Give file names that describe the deal, e.g. "Oak Plaza - loan sizing.xlsx". If a \
document is unreadable or missing a page you need, say which one."""

# Opus 5.5 list prices, $ per million tokens (cache write = 1.25x input).
PRICES = {"input": 4.00, "output": 20.00, "cache_read": 0.20, "cache_write": 5.00}

FILE_API_TYPES = {".pdf": "document", ".png": "image", ".jpg": "image", ".jpeg": "image",
                  ".gif": "image", ".webp": "image"}
TEXT_TYPES = {".xlsx", ".xlsm", ".csv", ".txt", ".docx", ".md"}
MAX_TEXT_CHARS = 400_000  # ~100k tokens; larger files should be split or sent as PDF
MAX_TURN_STEPS = 25


class UnsupportedFile(ValueError):
    pass


def to_text(name: str, data: bytes) -> str:
    """Convert a spreadsheet, CSV, Word or text file to plain text for Claude."""
    ext = Path(name).suffix.lower()
    if ext in (".xlsx", ".xlsm"):
        wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        parts = []
        for ws in wb.worksheets:
            buf = io.StringIO()
            writer = csv.writer(buf)
            for row in ws.iter_rows(values_only=True):
                if any(v is not None for v in row):
                    writer.writerow(["" if v is None else v for v in row])
            parts.append(f"## Sheet: {ws.title}\n{buf.getvalue()}")
        return "\n".join(parts)
    if ext == ".docx":
        doc = Document(io.BytesIO(data))
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                lines.append(" | ".join(c.text.strip() for c in row.cells))
        return "\n".join(lines)
    return data.decode("utf-8", errors="replace")


def slugify(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "-", name).strip("-").lower()
    return s[:60] or "deal"


@dataclass
class Deal:
    root: Path
    name: str
    created: float
    files: list[dict] = field(default_factory=list)  # {name, kind, file_id?, sent}
    usage: dict = field(default_factory=lambda: {k: 0 for k in PRICES})

    @property
    def uploads(self) -> Path:
        return self.root / "uploads"

    @property
    def outputs(self) -> Path:
        return self.root / "outputs"

    @property
    def messages_path(self) -> Path:
        return self.root / "messages.json"

    def save(self) -> None:
        meta = {"name": self.name, "created": self.created, "files": self.files,
                "usage": self.usage}
        (self.root / "deal.json").write_text(json.dumps(meta, indent=2))

    def messages(self) -> list[dict]:
        if self.messages_path.exists():
            return json.loads(self.messages_path.read_text())
        return []

    def save_messages(self, messages: list[dict]) -> None:
        tmp = self.messages_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(messages))
        tmp.replace(self.messages_path)

    def cost(self) -> float:
        return sum(self.usage.get(k, 0) * p for k, p in PRICES.items()) / 1e6

    def output_files(self) -> list[Path]:
        if not self.outputs.exists():
            return []
        return sorted((p for p in self.outputs.iterdir() if p.is_file()),
                      key=lambda p: p.stat().st_mtime, reverse=True)


class DealStore:
    def __init__(self, data_dir: str | Path):
        self.root = Path(data_dir).resolve() / "deals"
        self.root.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[Deal]:
        deals = [self.load(p.name) for p in self.root.iterdir() if (p / "deal.json").exists()]
        return sorted(deals, key=lambda d: d.created, reverse=True)

    def load(self, deal_id: str) -> Deal:
        root = self.root / deal_id
        meta = json.loads((root / "deal.json").read_text())
        return Deal(root, meta["name"], meta["created"], meta.get("files", []),
                    meta.get("usage", {k: 0 for k in PRICES}))

    def create(self, name: str) -> Deal:
        base = slugify(name)
        deal_id, n = base, 2
        while (self.root / deal_id).exists():
            deal_id, n = f"{base}-{n}", n + 1
        deal = Deal(self.root / deal_id, name.strip() or "Untitled deal", time.time())
        deal.uploads.mkdir(parents=True)
        deal.outputs.mkdir()
        deal.save()
        return deal

    def delete(self, deal: Deal, client=None) -> None:
        """Remove the deal locally and its uploaded copies held by the Files API."""
        if client is not None:
            for f in deal.files:
                if f.get("file_id"):
                    try:
                        client.files.delete(f["file_id"])
                    except Exception:
                        pass  # already gone; local delete still proceeds
        shutil.rmtree(deal.root)


def add_file(deal: Deal, name: str, data: bytes, client) -> dict:
    """Store an uploaded file in the deal and prepare it for Claude."""
    safe = Path(name).name
    ext = Path(safe).suffix.lower()
    if ext not in FILE_API_TYPES and ext not in TEXT_TYPES:
        raise UnsupportedFile(f"{safe}: unsupported type. Use PDF, image, Excel, CSV, Word or text.")
    (deal.uploads / safe).write_bytes(data)
    entry = {"name": safe, "kind": FILE_API_TYPES.get(ext, "text"), "sent": False}
    if ext in FILE_API_TYPES:
        mime = mimetypes.guess_type(safe)[0] or "application/octet-stream"
        entry["file_id"] = client.files.upload(file=(safe, data, mime)).id
    else:
        text = to_text(safe, data)
        if len(text) > MAX_TEXT_CHARS:
            raise UnsupportedFile(f"{safe} is too large as text ({len(text):,} characters). "
                                  "Save the relevant sheets or pages as a PDF and upload that.")
    deal.files = [f for f in deal.files if f["name"] != safe] + [entry]
    deal.save()
    return entry


def _attachment_blocks(deal: Deal) -> list[dict]:
    blocks = []
    for f in deal.files:
        if f["sent"]:
            continue
        if f["kind"] == "document":
            blocks.append({"type": "document", "title": f["name"],
                           "source": {"type": "file", "file_id": f["file_id"]}})
        elif f["kind"] == "image":
            blocks.append({"type": "image", "source": {"type": "file", "file_id": f["file_id"]}})
        else:
            text = to_text(f["name"], (deal.uploads / f["name"]).read_bytes())
            blocks.append({"type": "document", "title": f["name"],
                           "source": {"type": "text", "media_type": "text/plain", "data": text}})
    return blocks


def _append_user(messages: list[dict], content: list[dict]) -> None:
    """Append a user turn, repairing history left by an interrupted earlier turn."""
    last = messages[-1] if messages else None
    if last and last["role"] == "assistant":
        pending = [b["id"] for b in last["content"] if b.get("type") == "tool_use"]
        if pending:  # tools never ran: close them out so the history stays valid
            content = [{"type": "tool_result", "tool_use_id": i, "is_error": True,
                        "content": "Interrupted before this tool ran."} for i in pending] + content
    if last and last["role"] == "user":
        last["content"] = list(last["content"]) + content
    else:
        messages.append({"role": "user", "content": content})


def _dump(block) -> dict:
    return block.model_dump(mode="json", exclude_none=True)


TOOL_LABELS = {
    "size_loan": "Sizing the loan", "credit_metrics": "Calculating credit metrics",
    "stress_test": "Running stress tests", "global_cash_flow": "Calculating global cash flow",
    "create_loan_workbook": "Building the loan sizing workbook",
    "create_spreadsheet": "Building the spreadsheet", "create_chart": "Drawing a chart",
    "create_credit_memo": "Writing the Word document",
}


def respond(deal: Deal, user_text: str, client, model: str = MODEL) -> Iterator[str]:
    """Run one broker request to completion, yielding text as it streams.

    The conversation is append-only and saved after every step, so a dropped
    connection never loses work and thinking blocks stay valid on the next turn.
    """
    tools = {t.name: t for t in build_tools(deal.outputs)}
    messages = deal.messages()
    content = _attachment_blocks(deal) + [{"type": "text", "text": user_text}]
    _append_user(messages, content)
    for f in deal.files:
        f["sent"] = True
    deal.save()
    deal.save_messages(messages)

    for _ in range(MAX_TURN_STEPS):
        with client.beta.messages.stream(
            model=model,
            max_tokens=64000,
            system=APP_PROMPT,
            thinking={"type": "adaptive"},
            output_config={"effort": "high"},
            cache_control={"type": "ephemeral"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            tools=[t.to_dict() for t in tools.values()],
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text
            final = stream.get_final_message()

        u = final.usage
        deal.usage["input"] += u.input_tokens or 0
        deal.usage["output"] += u.output_tokens or 0
        deal.usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        deal.usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0
        deal.save()

        messages.append({"role": "assistant", "content": [_dump(b) for b in final.content]})
        deal.save_messages(messages)

        if final.stop_reason == "refusal":
            yield "\n\n_The request was declined by Claude's safety checks. Try rephrasing it._"
            return
        if final.stop_reason == "pause_turn":
            continue
        if final.stop_reason != "tool_use":
            if final.stop_reason == "max_tokens":
                yield "\n\n_The answer hit the length limit. Ask me to continue._"
            return

        results = []
        for block in final.content:
            if block.type != "tool_use":
                continue
            yield f"\n\n*{TOOL_LABELS.get(block.name, block.name)}...*\n\n"
            try:
                out = tools[block.name].call(block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
            except Exception as e:  # report the failure to Claude so it can correct itself
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"Error: {e}", "is_error": True})
        messages.append({"role": "user", "content": results})
        deal.save_messages(messages)

    yield "\n\n_Stopped after too many steps. Ask me to continue._"


def transcript(deal: Deal) -> list[tuple[str, str]]:
    """Broker-visible history: (role, markdown) pairs, skipping tool plumbing."""
    out = []
    for m in deal.messages():
        content = m["content"]
        if isinstance(content, str):
            out.append((m["role"], content))
            continue
        texts, notes = [], []
        for b in content:
            if b.get("type") == "text":
                texts.append(b["text"])
            elif b.get("type") == "document":
                notes.append(f"📎 {b.get('title', 'document')}")
            elif b.get("type") == "image":
                notes.append("📎 image")
            elif b.get("type") == "tool_use":
                texts.append(f"*{TOOL_LABELS.get(b['name'], b['name'])}...*")
        if m["role"] == "user" and not texts:
            continue  # tool results
        body = "\n\n".join(texts)
        if notes:
            body = "  ".join(notes) + "\n\n" + body
        if m["role"] == "assistant" and out and out[-1][0] == "assistant":
            out[-1] = ("assistant", out[-1][1] + "\n\n" + body)
        else:
            out.append((m["role"], body))
    return out
