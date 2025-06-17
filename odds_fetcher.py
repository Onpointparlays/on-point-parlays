import requests
import json
import os
from datetime import datetime, timedelta
from functools import reduce

API_KEY = "e3482b5a5079c3f265cdd620880a610d"
BASE_URL = "https://api.the-odds-api.com/v4/sports"
CACHE_FILE = "odds_cache.json"
CACHE_EXPIRY = timedelta(minutes=20)

def is_cache_valid():
    if not os.path.exists(CACHE_FILE):
        return False
    cache_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
    return cache_age < CACHE_EXPIRY

def load_cached_odds():
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_odds_to_cache(data):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def fetch_best_odds_for_game(sport_key, market="h2h"):
    """
    Pulls the best available odds for each team in upcoming matchups.
    :param sport_key: 'baseball_mlb', 'basketball_nba', etc.
    :param market: 'h2h' (moneyline), 'spreads', or 'totals'
    :return: List of dicts with team, opponent, best odds, sportsbook
    """
    url = f"{BASE_URL}/{sport_key}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": market,
        "oddsFormat": "american"
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        print(f"❌ Failed to fetch odds: {response.status_code}")
        return []

    data = response.json()
    picks = []

    for game in data:
        team_names = game.get("teams", [])
        bookmakers = game.get("bookmakers", [])

        for side_index, team in enumerate(team_names):
            best_odd = None
            best_site = None

            for book in bookmakers:
                for market_data in book.get("markets", []):
                    if market_data["key"] != market:
                        continue

                    outcomes = market_data.get("outcomes", [])
                    if side_index >= len(outcomes):
                        continue

                    outcome = outcomes[side_index]
                    price = outcome.get("price")
                    if not best_odd or int(price) > int(best_odd):
                        best_odd = price
                        best_site = book["title"]

            if best_odd:
                picks.append({
                    "team": team,
                    "opponent": team_names[1 - side_index],
                    "sport": sport_key,
                    "market": market,
                    "odds": best_odd,
                    "sportsbook": best_site
                })

    return picks

def get_cached_or_fresh_odds(sport_key, market="h2h"):
    """
    Returns cached odds if valid, otherwise fetches fresh odds and caches them.
    """
    if is_cache_valid():
        print("✅ Using cached odds.")
        all_cached = load_cached_odds()
        return all_cached.get(f"{sport_key}_{market}", [])

    print("🔄 Fetching and caching fresh odds.")
    odds = fetch_best_odds_for_game(sport_key, market)

    cache = {}
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)

    cache[f"{sport_key}_{market}"] = odds
    save_odds_to_cache(cache)
    return odds

def get_combined_parlay_value(legs):
    """
    Takes a list of pick dicts with 'odds' and 'sportsbook'.
    Returns combined decimal odds, American odds, best sportsbooks, and smartline value score.
    """
    decimal_odds_list = []
    all_sportsbooks = []

    for leg in legs:
        try:
            american = int(leg.get("odds", -110))
            sportsbook = leg.get("sportsbook", "Unknown")
            all_sportsbooks.append(sportsbook)

            if american > 0:
                decimal = (american / 100) + 1
            else:
                decimal = (100 / abs(american)) + 1

            decimal_odds_list.append(decimal)
        except:
            continue

    if not decimal_odds_list:
        return None

    combined_odds = reduce(lambda x, y: x * y, decimal_odds_list)
    avg_odds = sum(decimal_odds_list) / len(decimal_odds_list)
    expected = avg_odds ** len(decimal_odds_list)
    value_score = round(((combined_odds - expected) / expected) * 100, 2)

    return {
        "combined_decimal": round(combined_odds, 2),
        "combined_american": decimal_to_american(combined_odds),
        "best_sportsbooks": list(set(all_sportsbooks)),
        "smartline_value": value_score
    }

def decimal_to_american(decimal_odds):
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

