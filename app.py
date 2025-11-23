# app.py
import os
import json
from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from dotenv import load_dotenv
from models import db, User, Template
from ai_utils import (
    encrypt_key,
    decrypt_key,
    get_openai_client,
    ai_autocomplete,
    ai_autoreply,
    ai_rewrite,
    ai_fix_grammar,
)
from email_utils import send_email_smtp
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
# DB path relative to app location: instance/app.db
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///instance/app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ensure instance folder exists
os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# NOTE: your User.id is a string (UUID). DO NOT cast to int.
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


# Templates file path (relative to this file)
TEMPLATES_PATH = os.path.join(os.path.dirname(__file__), "templates.json")


def load_templates_file():
    try:
        with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# -------------------------
# Templates API
# -------------------------
@app.route("/api/templates")
@login_required
def api_templates():
    db_count = Template.query.count()
    if db_count:
        templates = [
            {"id": str(t.id), "title": t.title, "subject": t.subject, "body": t.body}
            for t in Template.query.order_by(Template.created_at.desc()).all()
        ]
        return jsonify(templates)
    else:
        return jsonify(load_templates_file())


@app.route("/api/templates/<template_id>")
@login_required
def api_template_get(template_id):
    db_row = Template.query.filter_by(id=str(template_id)).first()
    if db_row:
        return jsonify({"id": str(db_row.id), "title": db_row.title, "subject": db_row.subject, "body": db_row.body})
    data = load_templates_file()
    for t in data:
        if str(t.get("id")) == str(template_id):
            return jsonify(t)
    return jsonify({"error": "not found"}), 404


# -------------------------
# Save user-provided OpenAI key (encrypted)
# -------------------------
@app.route("/save_key", methods=["POST"])
@login_required
def save_key():
    key = None
    if request.is_json:
        key = request.json.get("openai_key")
    else:
        key = request.form.get("openai_key") or request.form.get("openaiKey")
    if not key:
        return jsonify({"ok": False, "msg": "Missing key"}), 400
    try:
        enc = encrypt_key(key)
        current_user.openai_enc_key = enc
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "msg": str(e)}), 500


# -------------------------
# Helper to obtain client for current_user
# -------------------------
def _client_for_current_user():
    if current_user.is_authenticated and getattr(current_user, "openai_enc_key", None):
        return get_openai_client(current_user.openai_enc_key)
    return get_openai_client()


# -------------------------
# AI Endpoints
# -------------------------
@app.route("/ai/autocomplete", methods=["POST"])
@login_required
def route_autocomplete():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty text"}), 400
    try:
        client = _client_for_current_user()
        out = ai_autocomplete(client, text)
        return jsonify({"ok": True, "text": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/ai/autoreply", methods=["POST"])
@login_required
def route_autoreply():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty text"}), 400
    try:
        client = _client_for_current_user()
        out = ai_autoreply(client, text)
        return jsonify({"ok": True, "text": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/ai/rewrite", methods=["POST"])
@login_required
def route_rewrite():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    style = data.get("style", "professional")
    if not text:
        return jsonify({"ok": False, "error": "Empty text"}), 400
    try:
        client = _client_for_current_user()
        out = ai_rewrite(client, text, style=style)
        return jsonify({"ok": True, "text": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/ai/grammar", methods=["POST"])
@login_required
def route_grammar():
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"ok": False, "error": "Empty text"}), 400
    try:
        client = _client_for_current_user()
        out = ai_fix_grammar(client, text)
        return jsonify({"ok": True, "text": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# -------------------------
# Send email route
# -------------------------
@app.route("/send", methods=["POST"])
@login_required
def route_send():
    to = request.form.get("to") or request.json.get("to")
    subject = request.form.get("subject") or request.json.get("subject")
    body = request.form.get("body") or request.json.get("body")

    if not to:
        return jsonify({"ok": False, "error": "Missing recipient"}), 400

    try:
        send_email_smtp(
            to_address=to,
            subject=subject,
            body_text=body,
            sender=current_user.email,
            enc_password=current_user.email_enc_password
        )
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------------
# Email Password (Keychain) UI
# -------------------------

@app.route("/email_password", methods=["GET", "POST"])
@login_required
def email_password():
    message = None

    if request.method == "POST":
        sender_email = request.form.get("sender_email")
    sender_password = request.form.get("sender_password")

    if not sender_email or not sender_password:
        message = "Missing email or password"
    else:
        # Encrypt password and store it in a file
        encrypted = encrypt_key(sender_password)

        with open("email_password.txt", "w") as f:
            f.write(json.dumps({
                "sender_email": sender_email,
                "encrypted_password": encrypted
            }))

        message = "Password saved successfully!"


    default_sender = os.getenv("DEFAULT_SENDER_EMAIL", "")
    return render_template(
        "email_password.html",
        default_sender=default_sender,
        message=message
)
# -------------------------
# Auth routes + pages
# -------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user = User.query.filter_by(email=email).first()
        if user and user.password_hash and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        if not email or not password:
            return render_template("register.html", error="Missing fields")
        existing = User.query.filter_by(email=email).first()
        if existing:
            return render_template("register.html", error="User exists")
        user = User(email=email, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for("index"))
    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    templates = []
    db_count = Template.query.count()
    if db_count:
        templates = [{"id": str(t.id), "name": t.title} for t in Template.query.order_by(Template.created_at.desc()).all()]
    else:
        js = load_templates_file()
        templates = [{"id": t.get("id"), "name": t.get("title")} for t in js]
    return render_template("index.html", templates=templates)


@app.route("/history")
@login_required
def history():
    return render_template("history.html")


# -------------------------
# CLI helper to seed templates
# -------------------------
@app.cli.command("seed-templates")
def seed_templates():
    count = Template.query.count()
    if count:
        print("Templates already present.")
        return
    data = load_templates_file()
    for t in data:
        tpl = Template(title=t.get("title") or t.get("id"), subject=t.get("subject"), body=t.get("body"))
        db.session.add(tpl)
    db.session.commit()
    print("Seeded templates:", len(data))


if __name__ == "__main__":
    app.run(debug=True)