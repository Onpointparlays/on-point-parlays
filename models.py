from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Pick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(50))
    tier = db.Column(db.String(50))
    pick_text = db.Column(db.String(300))
    summary = db.Column(db.String(500))
    confidence = db.Column(db.String(10))
    hit_chance = db.Column(db.String(10))
    sportsbook = db.Column(db.String(100))
    odds = db.Column(db.String(50))
    smartline_value = db.Column(db.String(10))       # ✅ NEW
    public_fade_value = db.Column(db.String(10))     # ✅ NEW
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
