from flask import Flask
from datetime import datetime
import requests
import pytz
from models import db, Pick

# ==== SETUP FLASK APP FOR CONTEXT ====
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db' if __name__ == '__main__' else 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# ==== ENGINE CLASS ====
class BlackLedgerEngine:
    def __init__(self):
        self.odds_api_key = 'YOUR_ODDS_API_KEY'
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
        if self.used_api_calls >= self.api_limit:
            print("🚫 API limit reached. Using cached odds.")
            return []

        self.used_api_calls += 1
        url = f"https://api.the-odds-api.com/v4/sports/basketball_nba/odds/?apiKey={self.odds_api_key}&regions=us&markets=player_points"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                print("❌ Error fetching odds:", response.text)
        except Exception as e:
            print("❌ Request error:", e)
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
        try:
            new_pick = Pick(
                sport="NBA",
                pick_type="Player Prop",
                pick_text=f"{player_name} OVER {line} points",
                tier=tier,
                confidence=confidence,
                hit_chance=confidence,
                summary=reason
            )
            db.session.add(new_pick)
            db.session.commit()
            print(f"✅ Saved {tier} pick: {player_name} over {line} – {confidence}%")
        except Exception as e:
            print("❌ Failed to save pick:", e)

# ==== RUN ENTRY POINT ====
if __name__ == '__main__':
    with app.app_context():
        engine = BlackLedgerEngine()
        engine.generate_nba_picks()
