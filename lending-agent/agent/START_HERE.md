# LendAgent: start-up version (one broker)

A private web page where you upload a deal's documents, ask for work in plain English, and
download the Excel and Word files the agent produces.

## 1. Get a Claude API key (10 minutes)

1. Sign up at **console.anthropic.com** and add a payment card under **Billing**.
2. Set a **monthly spend limit** (for example $100) so costs can't run away.
3. Under **API keys**, create a key and copy it somewhere safe. It starts with `sk-ant-`.

## 2. Start it on your own computer

1. Install **Python 3.12** from python.org. On Windows, tick **"Add python.exe to PATH"**.
2. Download this project (GitHub → **Code** → **Download ZIP**) and unzip it.
3. Open the `lending-agent/agent` folder and double-click:
   - **Mac:** `start.command`. If the Mac blocks it the first time, right-click it, choose
     **Open**, then **Open** again.
   - **Windows:** `start.bat`.
4. The first time, it installs what it needs (a minute or two) and asks for your Claude API
   key. The key is saved privately in a `.env` file in that folder, so you're only asked once.
5. Your browser opens at http://localhost:8501. Close the black window to stop the app.

## 3. Use it

1. **Create a deal** in the left-hand panel, for example "Oak Plaza refinance".
2. **Upload documents**: tax returns, financial statements, T-12s, rent rolls, appraisals and
   term sheets. PDFs and scans are read directly. Excel, CSV and Word files work too.
3. Click a quick button (**Spread the financials**, **Size the loan**, **Lender package**,
   **Missing documents**) or type a request, such as:
   - "Compare these two term sheets side by side in Excel and tell me which is cheaper over 5
     years."
   - "What's the global DSCR including the guarantor's personal cash flow?"
   - "Draft an email to the borrower asking for the 2023 K-1s."
4. Download the files from **Files made**. Check every figure against the source documents
   before anything goes to a lender. The agent cites where its numbers come from.

Claude usage typically costs **$1–6 per deal**. The running total for each deal is shown in the
left-hand panel.

## 4. Put it online so you can both use it (when ready)

Any small server that runs Docker works, for example DigitalOcean, AWS Lightsail or Render, at
about $12–25 a month. A developer can set this up in about an hour.

```bash
docker build -t lendagent .
docker run -d -p 8501:8501 -v lendagent-data:/data \
  -e ANTHROPIC_API_KEY=sk-ant-... -e APP_PASSWORD=choose-a-long-password lendagent
```

**Always set `APP_PASSWORD` online**, and put the site behind HTTPS. Most hosts do this for you.
Caddy is a simple option on a plain server.

## Keeping client data safe in this version

- Each deal's documents, conversation and files are stored in the `data/` folder (or the
  `/data` volume on a server). Keep that computer's disk encrypted (FileVault on Mac,
  BitLocker on Windows) and back the folder up.
- Documents are sent to Anthropic's API so Claude can read them. Anthropic doesn't train
  models on API data by default. PDFs and images are kept in Anthropic's file storage until
  you delete the deal. **Delete deal** removes them there and on your computer.
- The agent can only write files inside the open deal's folder.

## What this version doesn't do yet

- **One shared password,** with no separate logins. That's fine for the two of you, but not for
  customers.
- **No billing or separate customer accounts.**
- Before selling access to other brokers you need separate logins, each broker's data walled
  off, and billing. `PLAN.md` and `SECURITY.md` describe that next step.
