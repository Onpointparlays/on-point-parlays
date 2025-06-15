import requests

API_KEY = "e3482b5a5079c3f265cdd620880a610d"
BASE_URL = "https://api.the-odds-api.com/v4/sports"

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
        if market not in game.get("bookmakers", [{}])[0].get("markets", [{}])[0]:
            continue

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
                    if not best_odd or int(outcome["price"]) > int(best_odd):
                        best_odd = outcome["price"]
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
