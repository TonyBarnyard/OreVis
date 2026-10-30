"""LendAgent - single-broker web app.

    ANTHROPIC_API_KEY=... APP_PASSWORD=... streamlit run broker_app.py

Upload a deal's documents, ask for work in plain English, download the Excel
and Word files the agent produces. See START_HERE.md.
"""

from __future__ import annotations

import hmac
import os
from pathlib import Path

import streamlit as st

from lending_agent.deals import DealStore, UnsupportedFile, add_file, respond, transcript

DATA_DIR = os.environ.get("DATA_DIR", str(Path(__file__).parent / "data"))
PASSWORD = os.environ.get("APP_PASSWORD", "")

QUICK_ASKS = {
    "Spread the financials": (
        "Spread every tax return and financial statement in this deal into an Excel workbook, "
        "one column per year, with formulas for totals, EBITDA and cash flow available for debt "
        "service. List any add-backs you made and any years or schedules that are missing."),
    "Size the loan": (
        "Using the documents, work out underwritten NOI (or cash flow) and the collateral value, "
        "then size the loan at 1.25x DSCR, 75% LTV and 9% debt yield unless I've said otherwise. "
        "Run the stress tests and build the loan sizing workbook."),
    "Lender package": (
        "Write a lender-ready loan package in Word: executive summary, request and sources and "
        "uses, borrower and guarantor profile, collateral, financial analysis with key metrics, "
        "strengths, risks and mitigants, and a document index."),
    "Missing documents": (
        "Review what's in this deal and give me a checklist of the documents a lender will still "
        "need, plus a short email I can send the borrower asking for them."),
}

MIME = {".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png"}

st.set_page_config(page_title="LendAgent", page_icon="📊", layout="wide")


def md(text: str) -> str:
    """Show dollar amounts literally; Streamlit otherwise reads $...$ as maths."""
    return text.replace("$", r"\$")


def check_password() -> bool:
    if not PASSWORD:
        st.sidebar.warning("No APP_PASSWORD set. Only run like this on your own computer.")
        return True
    if st.session_state.get("authed"):
        return True
    st.title("LendAgent")
    pw = st.text_input("Password", type="password")
    if st.button("Sign in"):
        if hmac.compare_digest(pw.encode(), PASSWORD.encode()):
            st.session_state.authed = True
            st.rerun()
        st.error("Wrong password.")
    return False


def get_client():
    if "client" not in st.session_state:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            st.error("ANTHROPIC_API_KEY is not set. See START_HERE.md, step 1.")
            st.stop()
        import anthropic
        st.session_state.client = anthropic.Anthropic()
    return st.session_state.client


if not check_password():
    st.stop()

store = DealStore(DATA_DIR)

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("Deals")
    with st.form("new_deal", clear_on_submit=True):
        name = st.text_input("New deal name", placeholder="e.g. Oak Plaza refinance")
        if st.form_submit_button("Create deal") and name.strip():
            st.session_state.deal_id = store.create(name).root.name
            st.rerun()
    deals = store.list()
    if not deals:
        st.info("Create your first deal to start.")
        st.stop()
    ids = [d.root.name for d in deals]
    current = st.session_state.get("deal_id")
    index = ids.index(current) if current in ids else 0
    choice = st.radio("Open deal", ids, index=index,
                      format_func=lambda i: next(d.name for d in deals if d.root.name == i))
    st.session_state.deal_id = choice
    deal = store.load(choice)
    st.caption(f"Claude usage on this deal: about ${deal.cost():,.2f}")
    with st.expander("Delete this deal"):
        st.write("Removes its documents, conversation and files. This can't be undone.")
        if st.button("Delete permanently", type="primary"):
            uploaded = any(f.get("file_id") for f in deal.files)
            store.delete(deal, get_client() if uploaded else None)
            st.session_state.pop("deal_id", None)
            st.rerun()

# --------------------------------------------------------------------- main
st.title(deal.name)
left, right = st.columns([3, 1])

with right:
    st.subheader("Documents")
    uploads = st.file_uploader(
        "Add documents", accept_multiple_files=True, label_visibility="collapsed",
        type=["pdf", "png", "jpg", "jpeg", "xlsx", "xlsm", "csv", "docx", "txt"],
        key=f"up-{deal.root.name}-{len(deal.files)}")
    if uploads and st.button("Add to deal"):
        with st.spinner("Uploading..."):
            for up in uploads:
                try:
                    add_file(deal, up.name, up.getvalue(), get_client())
                except UnsupportedFile as e:
                    st.error(str(e))
        st.rerun()
    for f in deal.files:
        st.write(("✅ " if f["sent"] else "🆕 ") + f["name"])
    if any(not f["sent"] for f in deal.files):
        st.caption("🆕 = goes to the agent with your next message.")

    st.subheader("Files made")
    outputs = deal.output_files()
    if not outputs:
        st.caption("Workbooks, memos and charts appear here.")
    for p in outputs:
        st.download_button(p.name, p.read_bytes(), file_name=p.name,
                           mime=MIME.get(p.suffix, "application/octet-stream"),
                           key=f"dl-{p.name}", use_container_width=True)

with left:
    for role, text in transcript(deal):
        with st.chat_message(role):
            st.markdown(md(text))

    ask = None
    cols = st.columns(len(QUICK_ASKS))
    for col, (label, prompt) in zip(cols, QUICK_ASKS.items()):
        if col.button(label, use_container_width=True):
            ask = prompt
    typed = st.chat_input("Ask about this deal...")
    ask = typed or ask

    if ask:
        with st.chat_message("user"):
            st.markdown(md(ask))
        with st.chat_message("assistant"):
            try:
                st.write_stream(md(chunk) for chunk in respond(deal, ask, get_client()))
            except Exception as e:  # network/API trouble: the conversation is saved up to here
                st.error(f"Something went wrong talking to Claude: {e}. Your deal is saved; "
                         "try again.")
            else:
                st.rerun()
