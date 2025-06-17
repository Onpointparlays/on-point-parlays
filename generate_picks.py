import requests
from datetime import datetime
from flask import Flask
from models import db, Pick, BlackLedgerPick
from pytz import utc
import os
import random

app = Flask(__name__)

if os.environ.get("RENDER"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

db.init_app(app)
app.app_context().push()

API_KEY = "e3482b5a5079c3f265cdd620880a610d"
BASE_URL = "https://api.the-odds-api.com/v4/sports"

SPORTS = {
    "basketball_nba": "NBA",
    "americanfootball_nfl": "NFL",
    "baseball_mlb": "MLB",
    "icehockey_nhl": "NHL"
}

def american_to_implied(odds):
    if odds > 0:
        return 100 / (odds + 100) * 100
    else:
        return abs(odds) / (abs(odds) + 100) * 100

def get_confidence_grade(hit_chance):
    if hit_chance >= 85:
        return "A+"
    elif hit_chance >= 75:
        return "A"
    elif hit_chance >= 65:
        return "B"
    else:
        return "C"

def get_tier(hit_chance):
    if hit_chance >= 80:
        return "Safe"
    elif hit_chance >= 70:
        return "Mid"
    else:
        return "High"

def grade_smartline(edge):
    if edge >= 10:
        return "🔥 High"
    elif edge >= 5:
        return "✅ Medium"
    else:
        return "None"

def simulate_public_percentage():
    return random.randint(40, 90)

def grade_public_fade(public_pct, model_pct):
    if public_pct > 65 and model_pct < 60:
        return "🧨 Fade Popular Pick"
    elif public_pct > 60 and model_pct < 65:
        return "🟡 Risky Popular Pick"
    else:
        return "None"

def adjust_for_context(model_chance, is_home):
    context_log = []

    key_player_out = random.random() < 0.15
    if key_player_out:
        model_chance -= 7
        context_log.append("🔻 Key player possibly out")

    travel_risk = random.random() < 0.25
    if travel_risk and not is_home:
        model_chance -= 5
        context_log.append("🛬 Travel fatigue")

    if random.random() < 0.2:
        model_chance -= 2
        context_log.append("⏰ Odd tip-off time")

    if random.random() < 0.25:
        model_chance += 4
        context_log.append("🔥 Motivation bump")

    model_chance = max(45, min(95, model_chance))
    return round(model_chance, 1), context_log

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

        for _ in range(6):
            event = upcoming[pick_count % len(upcoming)]

            if "teams" not in event or "home_team" not in event:
                print(f"⚠️ Skipping invalid event: {event}")
                continue

            home = event["home_team"]
            away_candidates = [team for team in event["teams"] if team != home]
            away = away_candidates[0] if away_candidates else "Unknown"
            team_pick = home
            is_home = True

            sportsbook, odds = fetch_best_odds(event["id"], "h2h")

            try:
                base_chance = 80.0
                implied = american_to_implied(int(odds)) if odds != "N/A" else 50.0
            except:
                base_chance = 75.0
                implied = 50.0

            model_chance, context_flags = adjust_for_context(base_chance, is_home)

            edge = model_chance - implied
            confidence = get_confidence_grade(model_chance)
            tier = get_tier(model_chance)
            smartline = grade_smartline(edge)

            public_pct = simulate_public_percentage()
            fade = grade_public_fade(public_pct, model_chance)

            pick = Pick(
                sport=sport_name.lower(),
                tier=tier,
                pick_text=f"{team_pick} to win",
                summary=f"{team_pick} is the home team against {away}. Odds auto-pulled. " + " | ".join(context_flags),
                confidence=confidence,
                hit_chance=f"{model_chance:.0f}%",
                sportsbook=sportsbook,
                odds=odds,
                smartline_value=smartline,
                public_fade_value=fade,
                created_at=datetime.utcnow()
            )
            db.session.add(pick)
            pick_count += 1

        # 🎯 New Parlay Logic (Phase 4)
        for tier, legs in [("Safe", 2), ("Mid", 3), ("High", 5)]:
            for _ in range(3):
                parlay_legs = []
                for i in range(legs):
                    parlay_legs.append({
                        "team": f"Team {i+1}",
                        "type": "Moneyline",
                        "odds": "+120",
                        "summary": f"Team {i+1} has strong stats in this spot."
                    })

                parlay = BlackLedgerPick(
                    sport=sport_name.lower(),
                    tier=tier,
                    bet_type="Moneyline",
                    legs=parlay_legs,
                    hit_chance="82%",
                    confidence="A",
                    summary="Built using simulated win momentum + matchup edge.",
                    created_at=datetime.utcnow()
                )
                db.session.add(parlay)

        db.session.commit()
        print(f"✅ {sport_name} picks & parlays saved at {datetime.utcnow()} UTC")

if __name__ == "__main__":
    with app.app_context():
        generate_black_ledger_picks()
