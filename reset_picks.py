from models import db, Pick
from app import app

with app.app_context():
    Pick.query.delete()
    db.session.commit()
    print("🧹 All picks cleared.")
