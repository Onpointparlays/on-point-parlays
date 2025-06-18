from models import db, User, LockedPick
from app import app

# --- Simulated grading logic (replace later with real grading)
def simulate_parlay_grade(legs):
    # Pretend legs is a string like "Leg1, Leg2, Leg3"
    total_legs = len(legs.split(','))
    legs_hit = 0
    for leg in legs.split(','):
        if "hit" in leg.lower():
            legs_hit += 1

    if legs_hit == total_legs:
        return {"result": "hit", "legs_hit": legs_hit}
    else:
        return {"result": "miss", "legs_hit": legs_hit}

# --- XP + Level System
def award_xp(user, xp_change):
    user.xp = max(0, user.xp + xp_change)

    if user.xp >= user.level * 750 and user.level < 100:
        user.level += 1
        print(f"🎉 {user.username} leveled up to Level {user.level}!")

    db.session.commit()

# --- Grade picks and apply XP logic
def grade_locked_picks():
    with app.app_context():
        locked_picks = LockedPick.query.filter_by(status='pending').all()

        for pick in locked_picks:
            user = User.query.get(pick.user_id)
            if not user:
                continue

            result = simulate_parlay_grade(pick.legs)
            pick.status = result["result"]
            db.session.commit()

            if result["result"] == "hit":
                award_xp(user, 100)
            else:
                legs_hit = result["legs_hit"]
                total_legs = len(pick.legs.split(','))
                legs_missed = total_legs - legs_hit

                earned = legs_hit * 25
                penalty = legs_missed * 50
                net = earned - penalty

                print(f"👤 {user.username} | +{earned} XP | -{penalty} XP | Net: {net}")
                award_xp(user, net)

        print("✅ All pending picks graded.")

# --- Run this file directly to test grading
if __name__ == "__main__":
    grade_locked_picks()
