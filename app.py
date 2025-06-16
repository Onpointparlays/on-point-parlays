from flask import Flask, render_template, request, redirect, session, url_for, flash
from models import db, User, Pick
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from generate_picks import generate_black_ledger_picks
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ✅ Correct Render-compatible path for SQLite
if os.environ.get("RENDER"):
    os.makedirs("/mnt/data", exist_ok=True)  # ensure directory exists
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/users.db'

app.permanent_session_lifetime = timedelta(days=7)
db.init_app(app)

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
    picks = Pick.query.order_by(Pick.created_at.desc()).all()

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
        return f"✅ Deleted {len(mock_picks)} mock picks from Render DB."

@app.route('/test-refresh')
def test_refresh():
    generate_black_ledger_picks()
    return "Manual refresh completed."

# ========================
# INIT
# ========================
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
