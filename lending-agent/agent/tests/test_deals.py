"""Conversation loop and deal storage, exercised against a stand-in for the Claude API."""

import json
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from lending_agent import deals


class Block(SimpleNamespace):
    def model_dump(self, **_):
        return {k: v for k, v in vars(self).items() if v is not None}


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    @property
    def text_stream(self):
        return iter(b.text for b in self.message.content if b.type == "text")

    def get_final_message(self):
        return self.message


class FakeClient:
    """Replays scripted assistant turns and records every request."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.requests = []
        self.uploaded, self.deleted = [], []
        self.files = SimpleNamespace(upload=self._upload, delete=self.deleted.append)
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _upload(self, file):
        self.uploaded.append(file[0])
        return SimpleNamespace(id=f"file_{len(self.uploaded)}")

    def _stream(self, **kw):
        self.requests.append(json.loads(json.dumps(kw["messages"])))
        return FakeStream(self.turns.pop(0))


def turn(stop, *blocks):
    usage = SimpleNamespace(input_tokens=1000, output_tokens=200, cache_read_input_tokens=5000,
                            cache_creation_input_tokens=0)
    return SimpleNamespace(stop_reason=stop, content=list(blocks), usage=usage)


def text(t):
    return Block(type="text", text=t)


@pytest.fixture
def deal(tmp_path):
    return deals.DealStore(tmp_path).create("Oak Plaza refinance")


def test_store_create_list_and_unique_ids(tmp_path):
    store = deals.DealStore(tmp_path)
    a, b = store.create("Oak Plaza"), store.create("Oak Plaza")
    assert a.root.name == "oak-plaza" and b.root.name == "oak-plaza-2"
    assert {d.name for d in store.list()} == {"Oak Plaza"}


def test_pdf_goes_to_files_api_and_excel_becomes_text(deal):
    client = FakeClient([])
    deals.add_file(deal, "2024 tax return.pdf", b"%PDF-1.4", client)
    wb = Workbook()
    wb.active.append(["Unit", "Rent"])
    wb.active.append(["101", 1500])
    import io
    buf = io.BytesIO()
    wb.save(buf)
    deals.add_file(deal, "rent roll.xlsx", buf.getvalue(), client)
    assert client.uploaded == ["2024 tax return.pdf"]
    blocks = deals._attachment_blocks(deal)
    assert blocks[0]["source"] == {"type": "file", "file_id": "file_1"}
    assert "101,1500" in blocks[1]["source"]["data"]


def test_unsupported_and_path_tricks(deal):
    with pytest.raises(deals.UnsupportedFile):
        deals.add_file(deal, "virus.exe", b"x", FakeClient([]))
    deals.add_file(deal, "../../escape.txt", b"hello", FakeClient([]))
    assert (deal.uploads / "escape.txt").exists()


def test_tool_loop_builds_file_and_saves_history(deal):
    deals.add_file(deal, "t12.pdf", b"%PDF", FakeClient([]))
    tool_call = Block(type="tool_use", id="tu_1", name="create_loan_workbook", input={
        "filename": "Oak Plaza - sizing.xlsx", "deal_name": "Oak Plaza", "noi": 410000,
        "collateral_value": 5200000, "loan_amount": 3600000, "annual_rate": 0.071,
        "amort_years": 25, "term_years": 10})
    client = FakeClient([turn("tool_use", text("Sizing it now."), tool_call),
                         turn("end_turn", text("Done: Oak Plaza - sizing.xlsx"))])
    out = "".join(deals.respond(deal, "Size the loan", client))
    assert "Sizing it now." in out and "Done" in out
    assert [p.name for p in deal.output_files()] == ["Oak Plaza - sizing.xlsx"]
    # first request carries the PDF; second carries the tool result
    assert client.requests[0][0]["content"][0]["type"] == "document"
    assert client.requests[1][-1]["content"][0]["type"] == "tool_result"
    assert all(f["sent"] for f in deal.files)
    assert deal.cost() > 0
    assert [r for r, _ in deals.transcript(deal)] == ["user", "assistant"]


def test_tool_error_is_reported_to_claude(deal):
    bad = Block(type="tool_use", id="tu_1", name="create_chart",
                input={"filename": "../other-deal/x.png", "title": "t", "labels": ["a"],
                       "values": [1]})
    client = FakeClient([turn("tool_use", bad), turn("end_turn", text("Fixed."))])
    "".join(deals.respond(deal, "chart", client))
    result = client.requests[1][-1]["content"][0]
    assert result["is_error"] and "workspace" in result["content"]


def test_interrupted_turn_is_repaired_on_next_message(deal):
    dangling = Block(type="tool_use", id="tu_9", name="stress_test",
                     input={"noi": 1, "loan_amount": 1, "annual_rate": 0.05, "amort_years": 25})

    class Boom(FakeClient):
        def _stream(self, **kw):
            if not self.turns:
                raise ConnectionError("network down")
            return super()._stream(**kw)

    # tool_use saved, then the connection dies before the tools run
    client = Boom([turn("tool_use", dangling)])
    gen = deals.respond(deal, "stress it", client)
    with pytest.raises(ConnectionError):
        for chunk in gen:
            if "Running stress" in chunk:
                raise ConnectionError("network down")
    client = FakeClient([turn("end_turn", text("ok"))])
    "".join(deals.respond(deal, "try again", client))
    sent = client.requests[0]
    assert sent[-1]["role"] == "user"
    assert sent[-1]["content"][0] == {"type": "tool_result", "tool_use_id": "tu_9",
                                      "is_error": True,
                                      "content": "Interrupted before this tool ran."}
    roles = [m["role"] for m in sent]
    assert all(a != b for a, b in zip(roles, roles[1:]))


def test_refusal_stops_cleanly(deal):
    client = FakeClient([turn("refusal")])
    assert "declined" in "".join(deals.respond(deal, "x", client))


def test_delete_removes_local_and_uploaded_copies(tmp_path):
    store = deals.DealStore(tmp_path)
    deal = store.create("Gone")
    client = FakeClient([])
    deals.add_file(deal, "a.pdf", b"%PDF", client)
    store.delete(deal, client)
    assert client.deleted == ["file_1"] and not deal.root.exists()
