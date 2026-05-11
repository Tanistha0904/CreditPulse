# 💳 CreditPulse — AI Finance Credit Follow-Up Agent

> An intelligent accounts receivable agent powered by **Claude AI (Anthropic)**. Automatically generates escalating follow-up emails for overdue invoices with tone-aware AI, full audit logging, and a beautiful dashboard.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![Claude](https://img.shields.io/badge/AI-Claude%20Sonnet-purple) ![License](https://img.shields.io/badge/license-MIT-orange)

---

## 🎯 What It Does

CreditPulse solves the manual pain of chasing overdue payments by:

1. **Ingesting** invoice data from CSV/manual entry or the built-in sample dataset
2. **Analyzing** each invoice's days-overdue to determine escalation stage
3. **Generating** tone-calibrated emails using Claude AI (Stage 1: Warm → Stage 4: Stern → Stage 5: Legal Escalation)
4. **Logging** every email to a SQLite audit trail with timestamp, tone, sentiment score
5. **Analyzing** your entire portfolio with AI-powered risk assessment

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│                    Flask Web App                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Dashboard  │  │Invoice Queue │  │  Audit Log  │ │
│  └─────────────┘  └──────────────┘  └─────────────┘ │
│         │                │                 │         │
│  ┌──────▼────────────────▼─────────────────▼──────┐  │
│  │              Flask REST API                     │  │
│  │  /api/invoices  /api/generate-email  /api/stats │  │
│  └───────────────────────┬─────────────────────────┘  │
│                          │                            │
│  ┌───────────────────────▼────────────────────────┐   │
│  │             Agent Logic Layer                  │   │
│  │  ┌──────────────┐    ┌───────────────────────┐ │   │
│  │  │ Tone Engine  │    │  Claude AI Client     │ │   │
│  │  │ (days→stage) │    │  (email generation +  │ │   │
│  │  └──────────────┘    │   portfolio analysis) │ │   │
│  │                      └───────────────────────┘ │   │
│  └──────────────────────────────────────────────── │   │
│                          │                            │
│  ┌───────────────────────▼────────────────────────┐   │
│  │             SQLite Database                    │   │
│  │   invoices table  +  audit_log table           │   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/creditpulse-agent.git
cd creditpulse-agent

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY

# 5. Run the app
python app.py
```

Open http://localhost:5000 in your browser. Sample data loads automatically!

---

## 🌐 Free Deployment Options

### Option 1: Render (Recommended — Easiest)

1. Push your code to GitHub (make sure `.env` is in `.gitignore`)
2. Go to [render.com](https://render.com) → Sign up free
3. Click **New → Web Service**
4. Connect your GitHub repo
5. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python app.py`
6. Under **Environment Variables**, add:
   - `ANTHROPIC_API_KEY` = your key
7. Click **Deploy** — you get a free URL like `https://creditpulse.onrender.com`

> ⚠️ Free Render tier spins down after 15 min of inactivity. First load may take 30s.

### Option 2: Railway

1. Go to [railway.app](https://railway.app) → New Project
2. Deploy from GitHub repo
3. Add `ANTHROPIC_API_KEY` in Variables tab
4. Railway auto-detects Python + Flask

### Option 3: Hugging Face Spaces (Gradio/Flask)

1. Create a Space at [huggingface.co/spaces](https://huggingface.co/spaces)
2. Choose **Docker** or **Gradio** SDK
3. Upload files, add secret `ANTHROPIC_API_KEY`

### Option 4: Vercel (Serverless)

Requires slight refactoring to use serverless functions. Not recommended for SQLite.

---

## 🔒 Technical Stack & Decision Log

| Layer | Choice | Reason |
|-------|--------|--------|
| **LLM** | Claude Sonnet 4 (`claude-sonnet-4-20250514`) | Best cost/quality balance; excellent structured JSON output; strong instruction following for tone calibration |
| **Framework** | Flask 3.0 | Lightweight, easy to deploy, perfect for REST API + template serving |
| **Agent Pattern** | Single-agent ReAct-style | Each API call is stateless; agent receives full invoice context and outputs structured JSON |
| **Database** | SQLite | Zero-config, file-based, perfect for demo/single-server deployment |
| **Prompt Design** | System + User roles with JSON-only instruction | Prevents hallucination, ensures parseable output |
| **UI** | Vanilla JS + Flask templates | No build step, easy to deploy anywhere |

---

## 🛡️ Security Mitigations

| Risk | Mitigation |
|------|-----------|
| **Prompt Injection** | All invoice fields are passed as structured data, not interpolated into system prompts; LLM responses validated as JSON before use |
| **API Key Exposure** | Keys loaded via `python-dotenv` from `.env`; `.env` in `.gitignore`; `.env.example` provided with no real values |
| **PII in Logs** | Email bodies stored in local SQLite only; no PII sent to external analytics; audit log exportable by authorized users only |
| **Hallucination Risk** | LLM instructed to return strict JSON; `json.loads()` with try/catch fallback; all dynamic fields pre-populated from DB (not LLM-generated) |
| **Unauthorized Access** | For production: add API key auth middleware or OAuth; rate limiting via Flask-Limiter |
| **Email Spoofing** | Dry-run mode by default; real SMTP only when explicitly enabled; SPF/DKIM/DMARC to be configured on sender domain |
| **Escalation Safety** | Stage 5 (30+ days) triggers human review flag — NO automated email generated |

---

## 📊 Tone Escalation Matrix

| Stage | Trigger | Tone | Action |
|-------|---------|------|--------|
| 1st Follow-Up | 1–7 days overdue | Warm & Friendly | AI-generated polite reminder |
| 2nd Follow-Up | 8–14 days overdue | Polite but Firm | Request payment confirmation |
| 3rd Follow-Up | 15–21 days overdue | Formal & Serious | Mention credit term impact |
| 4th Follow-Up | 22–30 days overdue | Stern & Urgent | Final automated notice |
| Escalation | 30+ days overdue | 🔴 Legal Flag | Human review — no auto-email |

---

## 📁 Project Structure

```
creditpulse-agent/
├── app.py              # Main Flask app + agent logic
├── templates/
│   └── index.html      # Full dashboard UI
├── data/               # SQLite DB (auto-created, gitignored)
├── requirements.txt
├── Procfile            # For Render/Heroku deployment
├── .env.example        # Template for secrets
├── .gitignore
└── README.md
```

---

## 🧪 Testing with Sample Data

The app seeds 7 sample invoices on first run, covering all escalation stages:
- Stages 1–4 (various overdue periods)
- One pre-escalated invoice (30+ days)
- Mix of payment amounts (₹18K–₹1.2L)

Use **Bulk Process** to generate all emails at once, or click **✉ Generate** per invoice.

---

## 📄 Deliverables Checklist (Internship)

- [x] Data Ingestion (CSV upload + seeded SQLite)
- [x] Tone Escalation Engine (5-stage matrix)
- [x] AI Email Generation (Claude Sonnet)
- [x] Trigger Logic (auto-detect overdue stage)
- [x] Dry-run mode (default ON)
- [x] Audit Trail (SQLite + CSV export)
- [x] Escalation Cap (30+ days → human flag)
- [x] Personalised emails (all fields from DB)
- [x] Dashboard UI with stats
- [x] AI Portfolio Analysis (bonus)
- [x] Security documentation
- [x] Deployment ready (Render/Railway)

---

## 🙏 Built With

- [Anthropic Claude](https://anthropic.com) — AI email generation
- [Flask](https://flask.palletsprojects.com/) — Web framework
- [SQLite](https://sqlite.org/) — Audit storage

*Internship Project — AI Enablement Track*
