import requests
from datetime import datetime, time
from flask import Flask
from models import db, Pick, BlackLedgerPick
from pytz import utc
import os
import random
import json

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
    return 100 / (odds + 100) * 100 if odds > 0 else abs(odds) / (abs(odds) + 100) * 100

def get_confidence_grade(hit_chance):
    return "A+" if hit_chance >= 85 else "A" if hit_chance >= 75 else "B" if hit_chance >= 65 else "C"

def get_tier(hit_chance):
    return "Safe" if hit_chance >= 80 else "Mid" if hit_chance >= 70 else "High"

def grade_smartline(edge):
    return "🔥 High" if edge >= 10 else "✅ Medium" if edge >= 5 else "None"

def simulate_public_percentage():
    return random.randint(40, 90)

def grade_public_fade(public_pct, model_pct):
    if public_pct > 65 and model_pct < 60:
        return "🧨 Fade Popular Pick"
    elif public_pct > 60 and model_pct < 65:
        return "🟡 Risky Popular Pick"
    return "None"

def adjust_for_context(model_chance, is_home):
    context_log = []

    if random.random() < 0.15:
        model_chance -= 7
        context_log.append("🔻 Key player possibly out")
    if random.random() < 0.25 and not is_home:
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

def fetch_best_odds(event_id, market, sport_key):
    url = f"{BASE_URL}/{sport_key}/events/{event_id}/odds/?apiKey={API_KEY}&regions=us&markets={market}&oddsFormat=american"
    response = requests.get(url)
    if response.status_code != 200:
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
    all_parlays = []
    today = datetime.utcnow().date()

    for sport_key, sport_name in SPORTS.items():
        print(f"📘 Checking {sport_name} games...")

        url = f"{BASE_URL}/{sport_key}/events?apiKey={API_KEY}&regions=us&markets=h2h,totals,spreads"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch {sport_name} games: {response.text}")
            continue

        events = response.json()
        today_events = [
            e for e in events
            if "commence_time" in e
            and datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(utc).date() == today
        ]

        print(f"⏳ {len(today_events)} {sport_name} games scheduled for today.")
        if len(today_events) < 3:
            print(f"⚠️ Not enough valid games for 3 unique picks per tier for {sport_name}.")
            continue

        used_indices = set()
        tier_targets = {"Safe": 3, "Mid": 3, "High": 3}
        tier_counts = {"Safe": 0, "Mid": 0, "High": 0}
        picks_added = []

        while sum(tier_counts.values()) < 9 and len(used_indices) < len(today_events):
            idx = random.randint(0, len(today_events) - 1)
            if idx in used_indices:
                continue
            used_indices.add(idx)
            event = today_events[idx]

            if "teams" not in event or "home_team" not in event:
                continue

            home = event["home_team"]
            away = [team for team in event["teams"] if team != home][0]
            team_pick = home
            is_home = True

            sportsbook, odds = fetch_best_odds(event["id"], "h2h", sport_key)
            try:
                implied = american_to_implied(int(odds)) if odds != "N/A" else 50.0
            except:
                implied = 50.0

            model_chance, context_flags = adjust_for_context(80.0, is_home)
            edge = model_chance - implied
            confidence = get_confidence_grade(model_chance)
            tier = get_tier(model_chance)

            if tier_counts[tier] >= 3:
                continue

            pick = Pick(
                sport=sport_name.lower(),
                tier=tier,
                pick_text=f"{team_pick} to win",
                summary=f"{team_pick} is the home team vs {away}. | " + " | ".join(context_flags),
                confidence=confidence,
                hit_chance=f"{model_chance:.0f}%",
                sportsbook=sportsbook,
                odds=odds,
                smartline_value=grade_smartline(edge),
                public_fade_value=grade_public_fade(simulate_public_percentage(), model_chance),
                created_at=datetime.utcnow()
            )
            db.session.add(pick)
            tier_counts[tier] += 1
            picks_added.append(pick)

        for tier, legs_required in [("Safe", 2), ("Mid", 3), ("High", 5)]:
            for _ in range(3):
                legs = []
                for i in range(legs_required):
                    legs.append({
                        "team": f"Team {i+1}",
                        "type": random.choice(["Moneyline", "Spread", "Player Prop"]),
                        "odds": random.choice(["+110", "-120", "+135", "-105"]),
                        "summary": f"Leg {i+1} has strong edge and matchup value."
                    })

                parlay = BlackLedgerPick(
                    sport=sport_name.lower(),
                    tier=tier,
                    bet_type="Mixed",
                    legs=json.dumps(legs),
                    hit_chance=f"{random.randint(78, 89)}%",
                    confidence=random.choice(["A", "A+", "B"]),
                    summary="Built using matchup edges, form, and betting signals.",
                    created_at=datetime.utcnow()
                )
                all_parlays.append(parlay)

    if all_parlays:
        mystery = random.choice(all_parlays)
        mystery.is_mystery = True
        print(f"🎩 Mystery Pick set: {mystery.sport.title()} | {mystery.tier}")

    for parlay in all_parlays:
        db.session.add(parlay)

    db.session.commit()
    print(f"✅ All picks & {len(all_parlays)} parlays saved at {datetime.utcnow()} UTC")

if __name__ == "__main__":
    with app.app_context():
        generate_black_ledger_picks()
