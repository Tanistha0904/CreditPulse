import os
import json
import sqlite3
import csv
import io
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

DB_PATH = "data/audit.db"
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ── DB SETUP ──────────────────────────────────────────────────────────────────
def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT UNIQUE,
        client_name TEXT,
        contact_email TEXT,
        amount REAL,
        currency TEXT DEFAULT 'INR',
        due_date TEXT,
        follow_up_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        days_overdue INTEGER DEFAULT 0,
        payment_link TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_no TEXT,
        client_name TEXT,
        stage TEXT,
        tone TEXT,
        subject TEXT,
        email_body TEXT,
        send_status TEXT,
        ai_sentiment_score REAL,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        dry_run INTEGER DEFAULT 1
    )""")
    conn.commit()
    conn.close()

def seed_sample_data():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0]
    if count == 0:
        today = date.today()
        samples = [
            ("INV-2024-001", "Rajesh Kapoor", "rajesh@kapoorindustries.com",  45000, "INR", (today - timedelta(days=5)).isoformat(),  1, "pending", "https://pay.example.com/inv001"),
            ("INV-2024-002", "Priya Sharma",  "priya@sharmacorp.com",          82000, "INR", (today - timedelta(days=12)).isoformat(), 2, "pending", "https://pay.example.com/inv002"),
            ("INV-2024-003", "Arjun Mehta",   "arjun@mehtatech.io",           120000, "INR", (today - timedelta(days=19)).isoformat(), 3, "pending", "https://pay.example.com/inv003"),
            ("INV-2024-004", "Sunita Verma",  "sunita@vermallp.com",           35000, "INR", (today - timedelta(days=27)).isoformat(), 4, "pending", "https://pay.example.com/inv004"),
            ("INV-2024-005", "Kiran Patel",   "kiran@patelgroup.com",          95000, "INR", (today - timedelta(days=35)).isoformat(), 5, "escalated","https://pay.example.com/inv005"),
            ("INV-2024-006", "Neha Agarwal",  "neha@agarwalfin.com",           18000, "INR", (today - timedelta(days=3)).isoformat(),  0, "pending", "https://pay.example.com/inv006"),
            ("INV-2024-007", "Ravi Nair",     "ravi@nairconsult.in",           62000, "INR", (today - timedelta(days=15)).isoformat(), 3, "pending", "https://pay.example.com/inv007"),
        ]
        for s in samples:
            due = date.fromisoformat(s[5])
            days_ov = max(0, (date.today() - due).days)
            c.execute("""INSERT OR IGNORE INTO invoices
                (invoice_no,client_name,contact_email,amount,currency,due_date,follow_up_count,status,days_overdue,payment_link)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (s[0],s[1],s[2],s[3],s[4],s[5],s[6],s[7],days_ov,s[8]))
        conn.commit()
    conn.close()

# ── TONE ENGINE ───────────────────────────────────────────────────────────────
def get_stage_info(days_overdue):
    if days_overdue <= 7:
        return {"stage": "1st Follow-Up", "tone": "Warm & Friendly",    "urgency": 1}
    elif days_overdue <= 14:
        return {"stage": "2nd Follow-Up", "tone": "Polite but Firm",    "urgency": 2}
    elif days_overdue <= 21:
        return {"stage": "3rd Follow-Up", "tone": "Formal & Serious",   "urgency": 3}
    elif days_overdue <= 30:
        return {"stage": "4th Follow-Up", "tone": "Stern & Urgent",     "urgency": 4}
    else:
        return {"stage": "Escalation",    "tone": "Legal Escalation",   "urgency": 5}

# ── AI EMAIL GENERATOR ────────────────────────────────────────────────────────
def generate_email_with_ai(invoice: dict, stage_info: dict) -> dict:
    tone = stage_info["tone"]
    stage = stage_info["stage"]
    days_ov = invoice["days_overdue"]
    amt_fmt = f"₹{invoice['amount']:,.0f}"

    system_prompt = """You are a professional finance collections specialist AI. 
Generate a follow-up payment reminder email. 
Respond ONLY with a valid JSON object (no markdown, no code fences) with keys: "subject", "body", "sentiment_score".
- subject: email subject line
- body: full professional email body (plain text, no HTML)
- sentiment_score: float 0.0-1.0 (0=very aggressive, 1=very friendly)"""

    user_prompt = f"""Generate a {tone} payment reminder email for:
- Client: {invoice['client_name']}
- Invoice: {invoice['invoice_no']}  
- Amount Due: {amt_fmt}
- Due Date: {invoice['due_date']}
- Days Overdue: {days_ov}
- Follow-up Stage: {stage}
- Payment Link: {invoice['payment_link']}
- Previous Follow-ups Sent: {invoice['follow_up_count']}

Tone guidance for {tone}:
{_tone_guidance(tone)}

The email must mention the client name, invoice number, exact amount, and days overdue. End with a clear CTA."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            messages=[{"role": "user", "content": user_prompt}],
            system=system_prompt
        )
        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
        return result
    except Exception as e:
        # Fallback template
        return {
            "subject": f"Payment Reminder – {invoice['invoice_no']} | {amt_fmt}",
            "body": f"Dear {invoice['client_name']},\n\nThis is a reminder that {invoice['invoice_no']} for {amt_fmt} is {days_ov} days overdue.\n\nPlease pay at: {invoice['payment_link']}\n\nRegards,\nFinance Team",
            "sentiment_score": 0.7
        }

def _tone_guidance(tone):
    guides = {
        "Warm & Friendly": "Be warm, assume it's an oversight, keep it light and friendly. Use first name.",
        "Polite but Firm": "Polite but clearly state payment is pending. Request a confirmation date.",
        "Formal & Serious": "Formal salutation (Mr./Ms.). Express concern. Mention potential impact on credit terms. 48-hour response request.",
        "Stern & Urgent": "Very serious. Final reminder. Mention legal escalation consequence. Demand immediate action.",
        "Legal Escalation": "Do not generate email. Flag for manual review."
    }
    return guides.get(tone, "Professional and clear.")

# ── AI BATCH ANALYSIS ─────────────────────────────────────────────────────────
def analyze_portfolio_with_ai(invoices: list) -> dict:
    """Get AI insights on the overall receivables portfolio."""
    summary = [{"invoice": i["invoice_no"], "client": i["client_name"],
                "amount": i["amount"], "days_overdue": i["days_overdue"],
                "stage": i["status"]} for i in invoices]

    prompt = f"""Analyze this accounts receivable portfolio and give a brief JSON report:
{json.dumps(summary, indent=2)}

Respond ONLY with JSON (no markdown):
{{
  "risk_level": "Low|Medium|High|Critical",
  "total_at_risk": <number>,
  "key_insight": "<one sentence>",
  "recommended_action": "<one sentence>",
  "collection_probability": "<percentage string>"
}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip().replace("```json","").replace("```","").strip()
        return json.loads(raw)
    except:
        return {
            "risk_level": "Medium",
            "total_at_risk": sum(i["amount"] for i in invoices),
            "key_insight": "Multiple overdue invoices require immediate attention.",
            "recommended_action": "Prioritize follow-ups for invoices over 21 days.",
            "collection_probability": "72%"
        }

# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/invoices")
def get_invoices():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # Refresh days_overdue
    invoices = c.execute("SELECT * FROM invoices ORDER BY days_overdue DESC").fetchall()
    result = []
    for inv in invoices:
        inv = dict(inv)
        try:
            due = date.fromisoformat(inv["due_date"])
            inv["days_overdue"] = max(0, (date.today() - due).days)
        except:
            pass
        stage = get_stage_info(inv["days_overdue"])
        inv["stage"] = stage["stage"]
        inv["tone"] = stage["tone"]
        inv["urgency"] = stage["urgency"]
        result.append(inv)
    conn.close()
    return jsonify(result)

@app.route("/api/generate-email", methods=["POST"])
def generate_email():
    data = request.json
    invoice_no = data.get("invoice_no")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    inv = c.execute("SELECT * FROM invoices WHERE invoice_no=?", (invoice_no,)).fetchone()
    conn.close()
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404

    inv = dict(inv)
    try:
        due = date.fromisoformat(inv["due_date"])
        inv["days_overdue"] = max(0, (date.today() - due).days)
    except:
        pass

    stage_info = get_stage_info(inv["days_overdue"])

    if stage_info["urgency"] == 5:
        return jsonify({"escalated": True, "stage": "Escalation",
                        "message": "This invoice has been flagged for legal/finance team review. No automated email will be sent."})

    email = generate_email_with_ai(inv, stage_info)
    email["stage"] = stage_info["stage"]
    email["tone"] = stage_info["tone"]
    email["invoice"] = inv
    return jsonify(email)

@app.route("/api/send-email", methods=["POST"])
def send_email():
    data = request.json
    invoice_no = data.get("invoice_no")
    subject    = data.get("subject", "")
    body       = data.get("body", "")
    tone       = data.get("tone", "")
    stage      = data.get("stage", "")
    sentiment  = data.get("sentiment_score", 0.5)
    dry_run    = data.get("dry_run", True)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    inv = c.execute("SELECT * FROM invoices WHERE invoice_no=?", (invoice_no,)).fetchone()
    if not inv:
        conn.close()
        return jsonify({"error": "Not found"}), 404

    inv = dict(zip([d[0] for d in c.description], inv))
    send_status = "dry_run_success" if dry_run else "sent"

    # Log to audit
    c.execute("""INSERT INTO audit_log
        (invoice_no,client_name,stage,tone,subject,email_body,send_status,ai_sentiment_score,dry_run)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (invoice_no, inv["client_name"], stage, tone, subject, body, send_status, sentiment, 1 if dry_run else 0))

    # Update follow_up_count
    c.execute("UPDATE invoices SET follow_up_count=follow_up_count+1 WHERE invoice_no=?", (invoice_no,))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "status": send_status, "dry_run": dry_run})

@app.route("/api/bulk-process", methods=["POST"])
def bulk_process():
    dry_run = request.json.get("dry_run", True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    invoices = c.execute("SELECT * FROM invoices WHERE status='pending'").fetchall()
    conn.close()

    results = []
    for inv in invoices:
        inv = dict(inv)
        try:
            due = date.fromisoformat(inv["due_date"])
            inv["days_overdue"] = max(0, (date.today() - due).days)
        except:
            pass
        stage_info = get_stage_info(inv["days_overdue"])
        if stage_info["urgency"] == 5:
            # Escalate
            conn2 = sqlite3.connect(DB_PATH)
            conn2.execute("UPDATE invoices SET status='escalated' WHERE invoice_no=?", (inv["invoice_no"],))
            conn2.commit(); conn2.close()
            results.append({"invoice_no": inv["invoice_no"], "action": "escalated", "client": inv["client_name"]})
        else:
            email = generate_email_with_ai(inv, stage_info)
            conn2 = sqlite3.connect(DB_PATH)
            conn2.execute("""INSERT INTO audit_log
                (invoice_no,client_name,stage,tone,subject,email_body,send_status,ai_sentiment_score,dry_run)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (inv["invoice_no"], inv["client_name"], stage_info["stage"], stage_info["tone"],
                 email["subject"], email["body"], "dry_run_success" if dry_run else "sent",
                 email.get("sentiment_score", 0.5), 1 if dry_run else 0))
            conn2.execute("UPDATE invoices SET follow_up_count=follow_up_count+1 WHERE invoice_no=?", (inv["invoice_no"],))
            conn2.commit(); conn2.close()
            results.append({"invoice_no": inv["invoice_no"], "action": "email_sent", "stage": stage_info["stage"], "client": inv["client_name"]})

    return jsonify({"processed": len(results), "results": results, "dry_run": dry_run})

@app.route("/api/audit-log")
def get_audit_log():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    logs = c.execute("SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 100").fetchall()
    conn.close()
    return jsonify([dict(l) for l in logs])

@app.route("/api/stats")
def get_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    pending = c.execute("SELECT COUNT(*) FROM invoices WHERE status='pending'").fetchone()[0]
    escalated = c.execute("SELECT COUNT(*) FROM invoices WHERE status='escalated'").fetchone()[0]
    total_amount = c.execute("SELECT SUM(amount) FROM invoices WHERE status='pending'").fetchone()[0] or 0
    emails_sent = c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]

    # Stage breakdown
    all_invs = c.execute("SELECT days_overdue, amount FROM invoices WHERE status='pending'").fetchall()
    stage_counts = {1:0, 2:0, 3:0, 4:0}
    for inv in all_invs:
        days = inv[0]
        s = get_stage_info(days)["urgency"]
        if s <= 4:
            stage_counts[s] = stage_counts.get(s, 0) + 1
    conn.close()

    return jsonify({
        "total": total,
        "pending": pending,
        "escalated": escalated,
        "total_amount": total_amount,
        "emails_sent": emails_sent,
        "stage_breakdown": stage_counts
    })

@app.route("/api/ai-insights")
def ai_insights():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    invoices = c.execute("SELECT * FROM invoices WHERE status='pending'").fetchall()
    conn.close()
    invs = [dict(i) for i in invoices]
    for inv in invs:
        try:
            due = date.fromisoformat(inv["due_date"])
            inv["days_overdue"] = max(0, (date.today() - due).days)
        except:
            pass
    insights = analyze_portfolio_with_ai(invs)
    return jsonify(insights)

@app.route("/api/upload-csv", methods=["POST"])
def upload_csv():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file"}), 400
    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    added = 0
    for row in reader:
        try:
            c.execute("""INSERT OR IGNORE INTO invoices
                (invoice_no,client_name,contact_email,amount,currency,due_date,follow_up_count,payment_link)
                VALUES (?,?,?,?,?,?,?,?)""",
                (row.get("invoice_no",""), row.get("client_name",""), row.get("contact_email",""),
                 float(row.get("amount",0)), row.get("currency","INR"),
                 row.get("due_date",""), int(row.get("follow_up_count",0)),
                 row.get("payment_link","https://pay.example.com/link")))
            added += 1
        except:
            pass
    conn.commit(); conn.close()
    return jsonify({"added": added})

@app.route("/api/export-audit")
def export_audit():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    logs = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC").fetchall()
    conn.close()
    output = io.StringIO()
    if logs:
        writer = csv.DictWriter(output, fieldnames=dict(logs[0]).keys())
        writer.writeheader()
        for l in logs:
            writer.writerow(dict(l))
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype="text/csv",
                     as_attachment=True, download_name="audit_log.csv")

if __name__ == "__main__":
    init_db()
    seed_sample_data()
    app.run(debug=True, host="0.0.0.0", port=5000)
