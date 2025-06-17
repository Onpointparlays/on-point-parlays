import requests
from datetime import datetime
from flask import Flask
from models import db, Pick
from pytz import utc
import os

app = Flask(__name__)

# ✅ Shared DB path across all Render services
if os.environ.get("RENDER"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db.init_app(app)  # ✅ Init before context
app.app_context().push()

API_KEY = "e3482b5a5079c3f265cdd620880a610d"
BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORTS = {
    "basketball_nba": "NBA",
    "americanfootball_nfl": "NFL",
    "baseball_mlb": "MLB",
    "icehockey_nhl": "NHL"
}

def fetch_best_odds(event_id, market):
    url = f"{BASE_URL}/baseball_mlb/events/{event_id}/odds/?apiKey={API_KEY}&regions=us&markets={market}&oddsFormat=american"
    response = requests.get(url)

    if response.status_code != 200:
        print(f"❌ Failed to fetch odds for event {event_id}: {response.text}")
        return "Unavailable", "N/A"

    data = response.json()
    best_odd = None
    best_book = None

    for bookmaker in data.get("bookmakers", []):
        for market_entry in bookmaker.get("markets", []):
            if market_entry["key"] != market:
                continue
            for outcome in market_entry.get("outcomes", []):
                if not best_odd or outcome["price"] > best_odd:
                    best_odd = outcome["price"]
                    best_book = bookmaker["title"]

    return best_book or "Unavailable", f"{best_odd:+}" if best_odd is not None else "N/A"

def generate_black_ledger_picks():
    for sport_key, sport_name in SPORTS.items():
        print(f"📘 Checking {sport_name} games...")

        url = f"{BASE_URL}/{sport_key}/events?apiKey={API_KEY}&regions=us&markets=h2h,totals,spreads"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch {sport_name} games: {response.text}")
            continue

        events = response.json()
        upcoming = [
            e for e in events
            if "commence_time" in e and datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(utc) > datetime.utcnow().replace(tzinfo=utc)
        ]

        print(f"⏳ {len(upcoming)} upcoming {sport_name} games found.")

        if not upcoming:
            print(f"🕒 No valid games found for {sport_name}. Might be offseason.")
            continue

        pick_count = 0

        for tier, count in [("Safe", 2), ("Mid", 2), ("High", 2)]:
            for i in range(count):
                event = upcoming[i % len(upcoming)]

                if "teams" not in event or "home_team" not in event:
                    print(f"⚠️ Skipping invalid event: {event}")
                    continue

                home = event["home_team"]
                away_candidates = [team for team in event["teams"] if team != home]
                away = away_candidates[0] if away_candidates else "Unknown"
                team_pick = home

                sportsbook, odds = fetch_best_odds(event["id"], "h2h")

                pick = Pick(
                    sport=sport_name.lower(),
                    tier=tier,
                    pick_text=f"{team_pick} to win",
                    summary=f"{team_pick} has the edge at home. Odds auto-pulled.",
                    confidence="A",
                    hit_chance="80%",
                    sportsbook=sportsbook,
                    odds=odds,
                    created_at=datetime.utcnow()  # ✅ ensures /picks will show them
                )
                db.session.add(pick)
                pick_count += 1

        db.session.commit()
        print(f"✅ {sport_name} picks saved at {datetime.utcnow()} UTC. Total picks: {pick_count}")

# ✅ Manual trigger
if __name__ == "__main__":
    with app.app_context():
        generate_black_ledger_picks()
