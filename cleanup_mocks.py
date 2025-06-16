from models import db, Pick
from app import app

with app.app_context():
    mock_picks = Pick.query.filter(Pick.summary.contains('mock')).all()
    for pick in mock_picks:
        db.session.delete(pick)
    db.session.commit()
    print(f"✅ Deleted {len(mock_picks)} mock picks.")
