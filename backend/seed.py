"""
Seed script for proto/course-map development.

Creates a demo user, MARI 515, and its five learning outcomes.
Run from the backend/ directory:

    python seed.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app import app
from models import db, User, Course, LearningOutcome

OUTCOMES = [
    (0, "Identify the physiological mechanisms underlying coral bleaching and evaluate "
        "the relative contribution of thermal stress, ocean acidification, and local stressors."),
    (1, "Analyze a reef system using field or remotely-sensed data and characterize its "
        "current health state, trajectory, and dominant stressors."),
    (2, "Evaluate restoration intervention strategies — including coral gardening, assisted "
        "gene flow, and substrate stabilization — against the ecological and logistical "
        "constraints of a specific site."),
    (3, "Articulate a monitoring protocol that could detect early warning signals of "
        "degradation before bleaching thresholds are reached."),
    (4, "Situate a conservation decision within the social and political context of the reef "
        "— including Indigenous stewardship, tourism economies, and fisheries — and defend "
        "the tradeoffs made."),
]

with app.app_context():
    # Demo user
    user = User.query.filter_by(canvas_user_id="demo").first()
    if user is None:
        user = User(canvas_user_id="demo", name="Demo User", email="demo@localhost")
        db.session.add(user)
        db.session.flush()
        print("Created demo user.")
    else:
        print("Demo user already exists.")

    # MARI 515
    course = Course.query.filter_by(course_code="MARI 515", user_id=user.id).first()
    if course is None:
        course = Course(
            user_id=user.id,
            course_code="MARI 515",
            course_title="Coral Ecology and Conservation",
            canvas_course_id=None,
            learning_outcomes="\n".join(text for _, text in OUTCOMES),
        )
        db.session.add(course)
        db.session.flush()
        print("Created MARI 515.")
    else:
        print("MARI 515 already exists.")

    # Learning outcome rows
    existing = course.learning_outcome_rows.count()
    if existing == 0:
        for position, text in OUTCOMES:
            db.session.add(LearningOutcome(
                course_id=course.id,
                text=text,
                position=position,
            ))
        print(f"Seeded {len(OUTCOMES)} learning outcomes.")
    else:
        print(f"Learning outcomes already seeded ({existing} rows).")

    db.session.commit()
    print("Done.")
