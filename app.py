from flask import Flask, render_template, request, redirect, session, url_for, flash
from models import db, User, Pick
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from sqlalchemy import func
import os
from pytz import utc
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ========================
# DATABASE CONFIGURATION
# ========================
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'users.db')
if os.environ.get("RENDER"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'

app.permanent_session_lifetime = timedelta(days=7)
db.init_app(app)

with app.app_context():
    db.create_all()

# ========================
# ROUTES
# ========================
@app.route('/')
def home():
    return render_template('home.html', now=datetime.now())

@app.route('/picks')
def picks():
    if not session.get('user_logged_in'):
        return render_template('locked.html')

    # Show picks from the last 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    picks = Pick.query.filter(Pick.created_at >= twenty_four_hours_ago).order_by(Pick.created_at.desc()).all()

    picks_by_sport = {
        'nba': {'safe': [], 'mid': [], 'high': []},
        'nfl': {'safe': [], 'mid': [], 'high': []},
        'mlb': {'safe': [], 'mid': [], 'high': []},
        'nhl': {'safe': [], 'mid': [], 'high': []},
        'mixed': {'safe': [], 'mid': [], 'high': []}
    }

    for pick in picks:
        sport_key = pick.sport.lower()
        tier_key = pick.tier.lower()
        if sport_key in picks_by_sport and tier_key in picks_by_sport[sport_key]:
            picks_by_sport[sport_key][tier_key].append(pick)

    return render_template('picks.html', picks_by_sport=picks_by_sport)

@app.route('/login', methods=['POST'])
def login():
    identifier = request.form.get('identifier')
    password = request.form.get('password')

    if not identifier or not password:
        flash("Missing username/email or password.", "danger")
        return redirect(url_for('home'))

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if user and check_password_hash(user.password, password):
        session.permanent = True
        session['user_logged_in'] = True
        session['username'] = user.username
        session['email'] = user.email
        flash('Logged in successfully!', 'success')
        return redirect(url_for('home'))
    else:
        flash('Invalid login credentials.', 'danger')
        return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/signup', methods=['POST'])
def signup():
    email = request.form.get('email')
    username = request.form.get('username')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm') or request.form.get('confirm_password')

    if password != confirm_password:
        flash('Passwords do not match.')
        return redirect(url_for('home'))

    existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
    if existing_user:
        flash('Email or username already taken.')
        return redirect(url_for('home'))

    hashed_password = generate_password_hash(password)
    new_user = User(email=email, username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    flash('Signup successful. Please log in.')
    return redirect(url_for('home'))

@app.route('/profile')
def profile():
    if not session.get('user_logged_in'):
        return redirect(url_for('home'))
    return render_template('profile.html', username=session.get('username'))

@app.route('/cleanup-mocks')
def cleanup_mocks():
    with app.app_context():
        mock_picks = Pick.query.filter(Pick.summary.contains('mock')).all()
        for pick in mock_picks:
            db.session.delete(pick)
        db.session.commit()
        return f"✅ Deleted {len(mock_picks)} mock picks from DB."

@app.route('/test-refresh')
def test_refresh():
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
        best_odd, best_book = None, None
        for bookmaker in data.get("bookmakers", []):
            for market_entry in bookmaker.get("markets", []):
                if market_entry["key"] != market:
                    continue
                for outcome in market_entry.get("outcomes", []):
                    if not best_odd or outcome["price"] > best_odd:
                        best_odd = outcome["price"]
                        best_book = bookmaker["title"]
        return best_book or "Unavailable", f"{best_odd:+}" if best_odd is not None else "N/A"

    for sport_key, sport_name in SPORTS.items():
        url = f"{BASE_URL}/{sport_key}/events?apiKey={API_KEY}&regions=us&markets=h2h,totals,spreads"
        response = requests.get(url)
        if response.status_code != 200:
            continue

        events = response.json()
        upcoming = [
            e for e in events
            if "commence_time" in e and datetime.fromisoformat(e["commence_time"].replace("Z", "+00:00")).astimezone(utc) > datetime.utcnow().replace(tzinfo=utc)
        ]

        for tier, count in [("Safe", 2), ("Mid", 2), ("High", 2)]:
            for i in range(count):
                event = upcoming[i % len(upcoming)] if upcoming else None
                if not event or "teams" not in event or "home_team" not in event:
                    continue
                home = event["home_team"]
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
                    created_at=datetime.utcnow()
                )
                db.session.add(pick)

    # Inject manual test pick for debugging
    test_pick = Pick(
        sport="nba",
        tier="Safe",
        pick_text="Lakers to win",
        summary="Lakers have strong momentum at home. (Test Pick)",
        confidence="A+",
        hit_chance="88%",
        sportsbook="TestBook",
        odds="+130",
        created_at=datetime.utcnow()
    )
    db.session.add(test_pick)

    db.session.commit()
    return "Manual refresh completed (via live app)."

# ========================
# LOCAL DEV INIT
# ========================
if __name__ == '__main__':
    os.makedirs('instance', exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
