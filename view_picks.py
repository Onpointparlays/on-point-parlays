from models import db, Pick
from app import app

with app.app_context():
    picks = Pick.query.order_by(Pick.created_at.desc()).limit(10).all()
    for pick in picks:
        print(f"{pick.created_at} | {pick.sport.upper()} | {pick.tier} | {pick.pick_text} | {pick.summary}")
