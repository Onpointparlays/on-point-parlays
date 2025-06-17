import requests
from datetime import datetime, timedelta
from models import db, Pick
import pytz
from app import app
import json  # ✅ Added for cached odds reading

class BlackLedgerEngine:
    def __init__(self):
        self.odds_api_key = '67428de6e7860f6c46fd3fba43b8d395'
        self.weather_api_key = 'YOUR_WEATHER_API_KEY'
        self.used_api_calls = 0
        self.api_limit = 500
        self.timezone = pytz.timezone('US/Central')

    def generate_nba_picks(self):
        today = datetime.now(self.timezone).strftime('%Y-%m-%d')
        print(f"[{today}] 🧠 Running Black Ledger Engine for NBA")

        games = self.fetch_today_games()
        odds_data = self.fetch_odds()

        for game in games:
            if not game or 'home_team' not in game or 'visitor_team' not in game or 'id' not in game:
                print("⚠️ Skipping game due to missing keys:", game)
                continue

            home = game['home_team']
            away = game['visitor_team']
            game_id = game['id']

            weather_data = self.get_weather(home)
            injury_data = self.get_injuries(home, away)
            players = self.get_players_for_game(game_id)

            for player in players:
                if 'id' not in player or 'name' not in player:
                    print("⚠️ Skipping player with missing info:", player)
                    continue

                stats = self.get_recent_stats(player['id'])
                matchup_context = self.analyze_matchup(player, game, stats, weather_data)
                sportsbook_line = self.get_sportsbook_line(player['name'], odds_data)

                if not sportsbook_line:
                    continue

                expected_value = matchup_context['projection']
                line = sportsbook_line['line']

                if expected_value > line * 1.1:
                    confidence = self.grade_confidence(expected_value, line, injury_data, matchup_context)
                    tier = self.get_confidence_tier(confidence)

                    if tier:
                        self.save_pick(player['name'], game, line, expected_value, tier, confidence, matchup_context)

    def fetch_today_games(self):
        return [
            {
                "home_team": "Lakers",
                "visitor_team": "Warriors",
                "id": 123,
                "teams": ["Lakers", "Warriors"]
            },
            {
                "home_team": "Heat",
                "visitor_team": "Celtics",
                "id": 456
            }
        ]

    def fetch_odds(self):
        try:
            with open("odds_cache.json", "r") as f:
                cached_data = json.load(f)
            print("✅ Loaded odds from cache.")
            return cached_data.get("basketball_nba", {}).get("player_points", [])
        except Exception as e:
            print("⚠️ Failed to load cached odds:", e)
            return []

    def get_weather(self, team):
        return {"condition": "Clear", "temp": 72}

    def get_injuries(self, team1, team2):
        return {
            "team1_injuries": [],
            "team2_injuries": [],
            "key_players_out": []
        }

    def get_players_for_game(self, game_id):
        return [
            {"id": 1, "name": "LeBron James"},
            {"id": 2, "name": "Stephen Curry"}
        ]

    def get_recent_stats(self, player_id):
        return {}

    def analyze_matchup(self, player, game, stats, weather):
        location = game.get('location', 'Home')
        return {
            "projection": 24.5,
            "reason": "Averages 26.1 at home vs weak defenses. Opponent allows 4th-most to SGs. Clear weather.",
            "location": location
        }

    def get_sportsbook_line(self, player_name, odds_data):
        return {
            "book": "PrizePicks",
            "line": 21.5,
            "odds": -119
        }

    def grade_confidence(self, expected, line, injuries, context):
        difference = expected - line
        base = 75 + (difference * 2)

        if "out" in injuries["key_players_out"]:
            base -= 5

        if "Clear" in context["reason"]:
            base += 2

        return min(95, max(60, round(base)))

    def get_confidence_tier(self, confidence):
        if confidence >= 80:
            return "Safe"
        elif 70 <= confidence < 80:
            return "Mid"
        elif 60 <= confidence < 70:
            return "High Risk"
        else:
            return None

    def save_pick(self, player_name, game, line, expected, tier, confidence, context):
        reason = f"{context['reason']} Line: {line}, Our Projection: {expected}."
        with app.app_context():
            new_pick = Pick(
                sport="nba",
                pick_text=f"{player_name} OVER {line} points",
                tier=tier.lower(),
                confidence=confidence,
                hit_chance=confidence,
                summary=reason,
                sportsbook="PrizePicks",
                odds=line
            )
            db.session.add(new_pick)
            db.session.commit()
            print(f"✅ Saved {tier} pick: {player_name} over {line} – {confidence}%")

# === Run the engine ===
if __name__ == '__main__':
    with app.app_context():
        engine = BlackLedgerEngine()
        engine.generate_nba_picks()
