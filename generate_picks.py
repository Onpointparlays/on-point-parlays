import requests
from datetime import datetime
from models import db, Pick
from pytz import utc

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
        print(f"📘 Checking {sport_name}...")

        url = f"{BASE_URL}/{sport_key}/events?apiKey={API_KEY}&regions=us&markets=h2h,totals,spreads"
        response = requests.get(url)

        if response.status_code != 200:
            print(f"❌ Failed to fetch {sport_name} games.")
            continue

        events = response.json()
        upcoming = [e for e in events if datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(utc) > datetime.utcnow().replace(tzinfo=utc)]

        if not upcoming:
            print(f"🕒 {sport_name} currently in offseason or no valid games.")
            continue

        for tier, count in [("Safe", 2), ("Mid", 2), ("High", 2)]:
            for i in range(count):
                event = upcoming[i % len(upcoming)]
                home = event["home_team"]
                away = [team for team in event["teams"] if team != home][0]
                team_pick = home  # Default to home for now

                sportsbook, odds = fetch_best_odds(event["id"], "h2h")

                pick = Pick(
                    sport=sport_name.lower(),
                    tier=tier,
                    pick_text=f"{team_pick} to win",
                    summary=f"{team_pick} has the edge at home. Odds auto-pulled.",
                    confidence="A",
                    hit_chance="80%",
                    sportsbook=sportsbook,
                    odds=odds
                )
                db.session.add(pick)

        db.session.commit()
        print(f"✅ {sport_name} picks saved.")
