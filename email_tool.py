#!/usr/bin/env python3
"""
Email Automation Tool with:
- templates
- scheduler (apscheduler)
- keyring password storage
- Gmail/Outlook SMTP sending (configure via .env)
- AI Auto-Complete and AI Auto-Reply via Google Gemini (Generative API)
"""

import os
import json
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from datetime import datetime
from email.message import EmailMessage
import smtplib
import keyring
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import requests

# -------------------------
# Load environment / config
# -------------------------
load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "").strip()
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SERVICE_NAME = "Email_Automation_Tool"

# Google Generative API config (Gemini)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "models/gemini-1.5")  # default; can be e.g. "models/gemini-1.5" or similar
# Note: endpoint used below expects the model in the path (v1beta2 example). If Google changes API, you may need to update.

# -------------------------
# Templates: load / save
# -------------------------
TEMPLATES_FILE = "templates.json"
def load_templates():
    try:
        with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def save_templates(templates):
    with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=4, ensure_ascii=False)

TEMPLATES = load_templates()

# -------------------------
# Scheduler
# -------------------------
sched = BackgroundScheduler()
sched.start()

# -------------------------
# Keyring helpers
# -------------------------
def get_stored_password(sender):
    return keyring.get_password(SERVICE_NAME, sender)

def store_password(sender, password):
    keyring.set_password(SERVICE_NAME, sender, password)

# -------------------------
# Email sending (sync)
# -------------------------
def send_email_now(to_address, subject, body_text):
    sender = SENDER_EMAIL
    if not sender:
        raise ValueError("SENDER_EMAIL not set in .env")
    pw = get_stored_password(sender)
    if not pw:
        raise ValueError("No password stored. Use 'Set Password' first.")

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body_text)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
        smtp.ehlo()
        if SMTP_PORT == 587:
            smtp.starttls()
            smtp.ehlo()
        smtp.login(sender, pw)
        smtp.send_message(msg)

def send_email_threadsafe(to_address, subject, body_text):
    def _send():
        try:
            send_email_now(to_address, subject, body_text)
            messagebox.showinfo("Success", f"Email sent to {to_address}")
        except Exception as e:
            messagebox.showerror("Error sending", f"{e}")
    threading.Thread(target=_send, daemon=True).start()

def schedule_email(run_at_dt, to_address, subject, body_text):
    job = sched.add_job(send_email_now, 'date', run_date=run_at_dt, args=[to_address, subject, body_text])
    return job

# -------------------------
# Google Gemini helper
# -------------------------
def call_gemini_text(prompt, max_output_tokens=400, temperature=0.2):
    """
    Call Google Generative Text API (Gemini) using API key.
    Returns string (text) or raises Exception on failure.
    Note: API surface can change; adapt if Google updates endpoint.
    """
    if not GOOGLE_API_KEY:
        raise RuntimeError("GOOGLE_API_KEY not set in .env")

    # NOTE: This endpoint and request body follow the v1beta2/text generation pattern
    # If Google changes the API, you may need to adjust.
    url = f"https://generativeai.googleapis.com/v1beta2/{GEMINI_MODEL}:generateText?key={GOOGLE_API_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "prompt": {"text": prompt},
        "temperature": temperature,
        "maxOutputTokens": max_output_tokens,
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini API error {r.status_code}: {r.text}")
    data = r.json()
    # Response shape may vary. Many responses put content in data["candidates"][0]["content"] or similar
    # Try common patterns:
    candidate = None
    if "candidates" in data and isinstance(data["candidates"], list) and len(data["candidates"])>0:
        cand = data["candidates"][0]
        # candidate might contain 'output' or 'content' or 'text'
        for key in ("output", "content", "text"):
            if key in cand:
                return cand[key]
        # some variants: 'content' is a list of dicts with 'text'
        if "content" in cand and isinstance(cand["content"], list):
            pieces = []
            for piece in cand["content"]:
                if isinstance(piece, dict) and "text" in piece:
                    pieces.append(piece["text"])
            if pieces:
                return "".join(pieces)
    # fallback: try top-level fields
    if "output" in data:
        return data["output"]
    if "text" in data:
        return data["text"]
    # last resort: pretty-print JSON
    return json.dumps(data)

def ai_autocomplete_action(current_body):
    prompt = (
        "You are an assistant that continues and improves the following email message.\n"
        "Keep the same tone and complete naturally. Provide only the completed message body.\n\n"
        "Message to complete:\n"
        f"{current_body}\n\nComplete:"
    )
    return call_gemini_text(prompt)

def ai_autoreply_action(subject, original_body):
    prompt = (
        "You are an assistant that writes a polite, professional reply email based on the subject and the original message.\n"
        "Use clear short paragraphs. Keep it under 300 words. Start with a quick acknowledgement.\n\n"
        f"Subject: {subject}\n\nOriginal message:\n{original_body}\n\nWrite a reply:"
    )
    return call_gemini_text(prompt)

# -------------------------
# GUI
# -------------------------
root = tk.Tk()
root.title("Email Automation Tool")

# Frames
frm_top = tk.Frame(root)
frm_top.pack(padx=8, pady=6, fill="x")
frm_entries = tk.Frame(root)
frm_entries.pack(padx=8, pady=6, fill="x")
frm_body = tk.Frame(root)
frm_body.pack(padx=8, pady=6, fill="both", expand=True)
frm_templates = tk.Frame(root)
frm_templates.pack(padx=8, pady=4, fill="x")
frm_actions = tk.Frame(root)
frm_actions.pack(padx=8, pady=6, fill="x")

lbl_sender = tk.Label(frm_top, text=f"Sender: {SENDER_EMAIL or '(not set in .env)'}")
lbl_sender.pack(anchor="w")

tk.Label(frm_entries, text="To:").grid(row=0, column=0, sticky="e")
entry_to = tk.Entry(frm_entries, width=60)
entry_to.grid(row=0, column=1, padx=4, pady=2)

tk.Label(frm_entries, text="Subject:").grid(row=1, column=0, sticky="e")
entry_subject = tk.Entry(frm_entries, width=60)
entry_subject.grid(row=1, column=1, padx=4, pady=2)

tk.Label(frm_body, text="Body:").pack(anchor="w")
txt_body = scrolledtext.ScrolledText(frm_body, wrap=tk.WORD, height=14)
txt_body.pack(fill="both", expand=True, padx=4, pady=4)

# Templates UI
tk.Label(frm_templates, text="Templates:").grid(row=0, column=0, sticky="w")
template_var = tk.StringVar()
template_dropdown = ttk.Combobox(frm_templates, textvariable=template_var, width=40)
template_dropdown['values'] = ["Select a template"] + list(TEMPLATES.keys())
template_dropdown.current(0)
template_dropdown.grid(row=0, column=1, padx=4)

def apply_template():
    sel = template_var.get()
    if sel in TEMPLATES:
        txt_body.delete("1.0", tk.END)
        txt_body.insert("1.0", TEMPLATES[sel])

apply_btn = tk.Button(frm_templates, text="Apply Template", command=apply_template)
apply_btn.grid(row=0, column=2, padx=4)

# Save template sub-frame
tk.Label(frm_templates, text="New template name:").grid(row=1, column=0, sticky="e")
entry_tpl_name = tk.Entry(frm_templates, width=30)
entry_tpl_name.grid(row=1, column=1, sticky="w", padx=4)
def save_current_template():
    name = entry_tpl_name.get().strip()
    if not name:
        messagebox.showerror("Name needed", "Enter a template name.")
        return
    content = txt_body.get("1.0", tk.END).strip()
    if not content:
        messagebox.showerror("Empty", "Message body is empty - can't save.")
        return
    TEMPLATES[name] = content
    save_templates(TEMPLATES)
    template_dropdown['values'] = ["Select a template"] + list(TEMPLATES.keys())
    messagebox.showinfo("Saved", f"Template '{name}' saved.")
save_tpl_btn = tk.Button(frm_templates, text="Save New Template", command=save_current_template)
save_tpl_btn.grid(row=1, column=2, padx=4)

# AI Buttons
def on_ai_autocomplete():
    body = txt_body.get("1.0", tk.END).strip()
    if not body:
        messagebox.showerror("Empty", "Message body empty. Start typing to auto-complete.")
        return
    # run in thread
    def work():
        try:
            txt = ai_autocomplete_action(body)
            # insert as replacement or append
            root.after(0, lambda: (txt_body.delete("1.0", tk.END), txt_body.insert("1.0", txt)))
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("AI error", str(e)))
    threading.Thread(target=work, daemon=True).start()

def on_ai_autoreply():
    subj = entry_subject.get().strip()
    orig = txt_body.get("1.0", tk.END).strip()
    if not orig:
        messagebox.showerror("Missing", "No message body to reply to.")
        return
    def work():
        try:
            reply_text = ai_autoreply_action(subj, orig)
            root.after(0, lambda: (txt_body.delete("1.0", tk.END), txt_body.insert("1.0", reply_text)))
        except Exception as e:
            root.after(0, lambda: messagebox.showerror("AI error", str(e)))
    threading.Thread(target=work, daemon=True).start()

ai_auto_complete_btn = tk.Button(frm_actions, text="AI Auto-Complete", command=on_ai_autocomplete)
ai_auto_complete_btn.grid(row=0, column=0, padx=6)
ai_auto_reply_btn = tk.Button(frm_actions, text="AI Auto-Reply", command=on_ai_autoreply)
ai_auto_reply_btn.grid(row=0, column=1, padx=6)

# Schedule
tk.Label(frm_actions, text="Schedule (YYYY-MM-DD HH:MM)").grid(row=1, column=0, sticky="w")
entry_schedule = tk.Entry(frm_actions, width=20)
entry_schedule.grid(row=1, column=1, padx=4)

# Buttons: Set PW / Send / Schedule
def on_set_password():
    sender = SENDER_EMAIL
    if not sender:
        messagebox.showerror("Missing sender", "Set SENDER_EMAIL in .env first.")
        return
    def save_pw():
        pw = pw_entry.get()
        if not pw:
            messagebox.showerror("Empty", "Password can't be empty.")
            return
        store_password(sender, pw)
        pw_win.destroy()
        messagebox.showinfo("Saved", "Password stored securely in keyring.")
    pw_win = tk.Toplevel(root)
    pw_win.title("Set Password")
    tk.Label(pw_win, text=f"Set password for {sender}").pack(padx=8, pady=6)
    pw_entry = tk.Entry(pw_win, show="*", width=40)
    pw_entry.pack(padx=8, pady=6)
    tk.Button(pw_win, text="Save", command=save_pw).pack(pady=6)

def on_send_now():
    to = entry_to.get().strip()
    subj = entry_subject.get().strip()
    body = txt_body.get("1.0", tk.END).strip()
    if not to:
        messagebox.showerror("Missing", "Enter recipient email.")
        return
    send_email_threadsafe(to, subj, body)

def on_schedule():
    s = entry_schedule.get().strip()
    to = entry_to.get().strip()
    subj = entry_subject.get().strip()
    body = txt_body.get("1.0", tk.END).strip()
    if not s or not to:
        messagebox.showerror("Missing", "Enter schedule and recipient.")
        return
    try:
        run_dt = datetime.strptime(s, "%Y-%m-%d %H:%M")
    except Exception:
        messagebox.showerror("Bad format", "Schedule format must be YYYY-MM-DD HH:MM")
        return
    try:
        job = schedule_email(run_dt, to, subj, body)
        messagebox.showinfo("Scheduled", f"Email scheduled at {run_dt} (job id {job.id})")
    except Exception as e:
        messagebox.showerror("Schedule failed", str(e))

btn_set_pw = tk.Button(frm_actions, text="Set Password", command=on_set_password)
btn_set_pw.grid(row=2, column=0, padx=6, pady=6)
btn_send_now = tk.Button(frm_actions, text="Send Now", command=on_send_now)
btn_send_now.grid(row=2, column=1, padx=6, pady=6)
btn_schedule = tk.Button(frm_actions, text="Schedule Send", command=on_schedule)
btn_schedule.grid(row=2, column=2, padx=6, pady=6)

# Graceful shutdown
def on_closing():
    if messagebox.askokcancel("Quit", "Quit and stop scheduler?"):
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass
        root.destroy()
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start app
if __name__ == "__main__":
    # Optionally load a default template into body if wanted
    root.mainloop()