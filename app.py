from flask import Flask, render_template, request, redirect, url_for, session
import json
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "onpoint-secret-key-change-later"  # needed for admin login

# Password for the admin page
ADMIN_PASSWORD = "$WEDONTQUIT2026$"

# Path to the picks data file
DATA_FILE = os.path.join("data", "picks.json")

# List of sports we support
SPORTS = ["NFL", "NBA", "WNBA", "CFB", "NHL", "MLB"]


def load_picks():
    """Load all picks from the JSON file"""
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_picks(picks):
    """Save picks back to the JSON file"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(picks, f, indent=2, ensure_ascii=False)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/picks")
def picks():
    all_picks = load_picks()
    
    # Get the date from the URL (example: /picks?date=2026-09-30)
    selected_date = request.args.get("date")
    
    # If no date is chosen, use today
    if not selected_date:
        selected_date = date.today().isoformat()
    
    # Get the picks for the selected date (or empty if none)
    day_picks = all_picks.get(selected_date, {})
    
    # Make a sorted list of all dates that have picks (newest first)
    available_dates = sorted(all_picks.keys(), reverse=True)
    
    return render_template(
        "picks.html",
        selected_date=selected_date,
        day_picks=day_picks,
        available_dates=available_dates,
        sports=SPORTS
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    # Check if already logged in
    if not session.get("admin_logged_in"):
        if request.method == "POST" and request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin"))
        return render_template("admin.html", logged_in=False)
    
    # --- Logged in section ---
    if request.method == "POST" and "date" in request.form:
        # User is submitting new picks
        selected_date = request.form.get("date")
        all_picks = load_picks()
        
        day_data = {}
        for sport in SPORTS:
            day_data[sport] = request.form.get(sport, "No games available").strip()
        
        all_picks[selected_date] = day_data
        save_picks(all_picks)
        
        return redirect(url_for("picks", date=selected_date))
    
    # Show the admin form
    today = date.today().isoformat()
    return render_template("admin.html", logged_in=True, sports=SPORTS, today=today)


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)