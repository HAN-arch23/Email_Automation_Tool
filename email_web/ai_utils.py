import base64
import os
from cryptography.fernet import Fernet
from openai import OpenAI

# -------------------------------
# Encryption for storing API Keys
# -------------------------------
def _get_fernet():
    key = os.getenv("FERNET_KEY")
    if not key:
        key = Fernet.generate_key()
        print("WARNING: No FERNET_KEY found. Generated a temporary one.")
    return Fernet(key)

def encrypt_key(key: str) -> str:
    f = _get_fernet()
    return f.encrypt(key.encode()).decode()

def decrypt_key(enc_key: str) -> str:
    f = _get_fernet()
    return f.decrypt(enc_key.encode()).decode()

# -------------------------------
# Get OpenAI Client
# -------------------------------
def get_openai_client(enc_key=None):
    if enc_key:
        api_key = decrypt_key(enc_key)
    else:
        api_key = os.getenv("OPENAI_API_KEY")

    return OpenAI(api_key=api_key)

# -------------------------------
# AI FUNCTIONS
# -------------------------------

def ai_autocomplete(client, text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You complete emails professionally."},
            {"role": "user", "content": text}
        ],
        max_tokens=120
    )
    return response.choices[0].message.content

def ai_autoreply(client, text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You write helpful email replies."},
            {"role": "user", "content": f"Reply to this message:\n{text}"}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content

def ai_rewrite(client, text, style="professional"):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Rewrite text in a {style} tone."},
            {"role": "user", "content": text}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content

def ai_fix_grammar(client, text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Fix grammar but keep meaning the same."},
            {"role": "user", "content": text}
        ],
        max_tokens=150
    )
    return response.choices[0].message.content