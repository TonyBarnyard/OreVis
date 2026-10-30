"""Smoke-test the Streamlit screen: sign-in, creating a deal, and the deal layout."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "broker_app.py")


def start(monkeypatch, tmp_path, password="s3cret"):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_PASSWORD", password)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return AppTest.from_file(APP, default_timeout=30).run()


def test_password_required(monkeypatch, tmp_path):
    at = start(monkeypatch, tmp_path)
    at.text_input[0].input("wrong").run()
    at.button[0].click().run()
    assert at.error and "Wrong password" in at.error[0].value
    assert not at.sidebar.text_input  # deals hidden


def test_sign_in_and_create_deal(monkeypatch, tmp_path):
    at = start(monkeypatch, tmp_path)
    at.text_input[0].input("s3cret").run()
    at.button[0].click().run()
    at.sidebar.text_input[0].input("Oak Plaza refinance")  # form: submitted with the button
    at.sidebar.button[0].click().run()
    assert at.title[0].value == "Oak Plaza refinance"
    labels = [b.label for b in at.button]
    assert {"Spread the financials", "Size the loan", "Lender package",
            "Missing documents"} <= set(labels)
    assert (tmp_path / "deals" / "oak-plaza-refinance" / "deal.json").exists()
