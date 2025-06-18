from models import db, BlackLedgerPick
from app import app

with app.app_context():
    picks = BlackLedgerPick.query.all()
    print(f"✅ Total Black Ledger Parlays Found: {len(picks)}")

    if picks:
        for p in picks[:5]:  # Show first 5 parlays
            legs = p.legs.split(",")
            print("────────────")
            print(f"Sport: {p.sport.upper()} | Tier: {p.tier.title()} | Bet Type: {p.bet_type}")
            print(f"Legs ({len(legs)}):")
            for leg in legs:
                print(f" - {leg.strip()}")
            print(f"Summary: {p.summary[:80]}...\n")
    else:
        print("⚠️ No Black Ledger parlays found.")
