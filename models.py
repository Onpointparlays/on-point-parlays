from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    xp = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)

class Pick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(50))
    tier = db.Column(db.String(50))
    pick_text = db.Column(db.String(300))
    summary = db.Column(db.String(500))
    confidence = db.Column(db.String(10))
    hit_chance = db.Column(db.String(10))
    sportsbook = db.Column(db.String(100))
    odds = db.Column(db.String(100))
    smartline_value = db.Column(db.String(10))
    public_fade_value = db.Column(db.String(10))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlackLedgerPick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sport = db.Column(db.String(50))
    tier = db.Column(db.String(50))
    bet_type = db.Column(db.String(50))
    legs = db.Column(db.Text)  # stored as JSON string
    hit_chance = db.Column(db.String(10))
    confidence = db.Column(db.String(10))
    summary = db.Column(db.Text)
    smartline_value = db.Column(db.String(10))
    public_fade_value = db.Column(db.String(10))
    result = db.Column(db.String(10), default='pending')  # hit, miss, pending
    is_mystery = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LockedPick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sport = db.Column(db.String(50), nullable=False)
    legs = db.Column(db.Text, nullable=False)  # stored as JSON string
    status = db.Column(db.String(20), default='pending')  # hit, miss, pending
    user = db.relationship('User', backref=db.backref('locked_picks', lazy=True))
