from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import uuid

db = SQLAlchemy()

def gen_id():
    return str(uuid.uuid4())

class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.String, primary_key=True, default=gen_id)
    email = db.Column(db.String(256), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    openai_enc_key = db.Column(db.Text, nullable=True)      # encrypted OpenAI key
    email_enc_password = db.Column(db.Text, nullable=True)  # encrypted email password
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Template(db.Model):
    __tablename__ = "template"
    id = db.Column(db.String, primary_key=True, default=gen_id)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(400), nullable=True)
    body = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    email_enc_password = db.Column(db.Text, nullable=True)