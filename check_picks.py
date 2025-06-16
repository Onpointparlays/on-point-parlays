from models import db, Pick
from app import app

with app.app_context():
    picks = Pick.query.all()
    print(f"Total picks found: {len(picks)}")
    if picks:
        for p in picks[:5]:  # show first 5 picks
            print(f"{p.sport.upper()} | {p.tier.title()} | {p.summary[:60]}...")
    else:
        print("No picks found.")
