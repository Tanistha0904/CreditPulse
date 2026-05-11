# 💳 CreditPulse — AI Finance Credit Follow-Up Agent

> An intelligent accounts receivable agent powered by ****. Automatically generates escalating follow-up emails for overdue invoices with tone-aware AI, full audit logging, and a beautiful dashboard.

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

# CreditPulse AI

AI-powered finance collections dashboard for tracking overdue invoices, payment risks, and automated follow-up email generation.

## Live Demo

https://web-production-5cae3.up.railway.app/

---

## Features

- Invoice tracking dashboard
- Payment risk analysis
- AI-generated follow-up emails
- Escalation workflow system
- Audit logs
- CSV upload support
- Real-time finance metrics

---

## Tech Stack

- Python
- Flask
- HTML/CSS
- Anthropic Claude API
- Railway
- GitHub

---

## Screenshots

(Add screenshots here later)

---

## Local Setup

### Clone Repository

```bash
git clone https://github.com/Tanistha0904/CreditPulse.git
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run Project

```bash
python app.py
```

---

## Deployment

Deployed on Railway.

---

## Author

Tanistha Keshri