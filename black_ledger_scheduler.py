from flask import Flask
from flask_apscheduler import APScheduler
from datetime import datetime
from generate_picks import generate_black_ledger_picks
import pytz
import os
from models import db

# === Flask App Setup ===
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

if os.environ.get("RENDER"):
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////mnt/data/users.db'
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

app.config['SCHEDULER_API_ENABLED'] = True
db.init_app(app)

# === Scheduler Setup ===
scheduler = APScheduler()
central = pytz.timezone('US/Central')

# === Job Function ===
def run_black_ledger():
    now = datetime.now(central).strftime("%Y-%m-%d %I:%M %p")
    print(f"\n⏰ {now} CST — Running Black Ledger Pick Generator...")
    with app.app_context():
        generate_black_ledger_picks()
    print("✅ Done generating picks.\n")

# === Register Jobs ===
scheduler.init_app(app)
scheduler.start()

scheduler.add_job(
    id='Run_Black_Ledger_12pm',
    func=run_black_ledger,
    trigger='cron',
    hour=12,
    minute=0,
    timezone='US/Central'
)

scheduler.add_job(
    id='Run_Black_Ledger_3pm',
    func=run_black_ledger,
    trigger='cron',
    hour=15,
    minute=0,
    timezone='US/Central'
)

scheduler.add_job(
    id='Run_Black_Ledger_6pm',
    func=run_black_ledger,
    trigger='cron',
    hour=18,
    minute=0,
    timezone='US/Central'
)

# === Manual Trigger Route ===
@app.route('/run-now')
def manual_run():
    run_black_ledger()
    return "✅ Black Ledger Engine ran manually."

# === Launch Flask App ===
if __name__ == '__main__':
    app.run(debug=True)
