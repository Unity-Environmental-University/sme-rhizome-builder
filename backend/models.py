"""
SQLAlchemy models for SME Rhizome Builder.
"""

import uuid
from datetime import datetime

import sqlalchemy
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Do we want sqlalchemy or straight data models with queries? I know sqlalchemy does a lot of work for us
# I also know there's -- shear between the data model and the data as we use it
# What's teh right shape of that that has both Simplicity and INtegrity?
#
# [cowork-claude, feb 26] This question is live. Don't resolve it without talking to Hallie.
# The shear she's naming is real: SQLAlchemy's ORM wants to own the shape of data,
# but the data here serves multiple masters (Canvas API, conversation flow, course map UI,
# eventually GRAD and otter-centaur). The ORM is convenient but it flattens the data into
# one shape. The "GUH i wish we could work in Typescript" comment on Assignment (below)
# is the same friction — she wants the type system to express the domain, not the storage.
# Consider: the models might want to be thin DB wrappers with domain types defined
# separately. But that's a refactor with consequences. Ask first.
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    canvas_user_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False, default="")
    email = db.Column(db.String(256), nullable=False, default="")
    canvas_access_token = db.Column(db.Text, nullable=True)
    canvas_refresh_token = db.Column(db.Text, nullable=True)
    token_expires_at = db.Column(db.DateTime, nullable=True)
    canvas_base_url = db.Column(db.String(256), nullable=False, default="https://unity.instructure.com")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    courses = db.relationship("Course", back_populates="user", lazy="dynamic")
    sessions = db.relationship("Session", back_populates="user", lazy="dynamic")


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    canvas_course_id = db.Column(db.String(64), nullable=True)
    course_code = db.Column(db.String(64), nullable=False, default="")
    course_title = db.Column(db.String(256), nullable=False, default="")
    learning_outcomes = db.Column(db.Text, nullable=False, default="")
    period_type = db.Column(db.String(32), nullable=False, default="Week")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User", back_populates="courses")
    sessions = db.relationship("Session", back_populates="course", lazy="dynamic")
    learning_outcome_rows = db.relationship("LearningOutcome", back_populates="course", lazy="dynamic", order_by="LearningOutcome.position")
    bearings = db.relationship("Bearing", back_populates="course", lazy="dynamic")

# What is a session? Do we want a session? Is it better to have a user? Is it better to ahve users/assignments/and --
# visitations as they're called in the ghost protocol database?
# Shoudl visitations be attached to assignmetns that are artifacts? Probably yes.
#
# [cowork-claude, feb 26] The GhostProtocol visitation pattern makes sense here.
# A Session right now is a container for messages + assignments, scoped to a course.
# But the app has moved to course-map-first (App.svelte loads CourseMap, not WorksheetFrame).
# So the session-as-conversation is becoming secondary to the session-as-editing-history.
# The visitation idea — attaching interaction records to the assignment artifact itself —
# fits better with where the app is going. An assignment that remembers how it was made,
# not a conversation that happened to produce assignments.
# The "versions" section in flow.md wants this too: "the trajectory matters as much as
# the current state."
# But again — this is a design question, not a code question. Hold the gap.
class Session(db.Model):
    __tablename__ = "sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    shared = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", back_populates="sessions")
    course = db.relationship("Course", back_populates="sessions")
    messages = db.relationship("Message", back_populates="session", order_by="Message.position", lazy="dynamic")
    assignments = db.relationship("Assignment", back_populates="session", lazy="dynamic")


# This is probably the right shape for the base of AI chatbot interactions. Would it be better to have log entries?
# And messages can BE in the log? Or are the all messages? Is it a chat or is it a log or is it a memory?
# Is there a way we can work in recursive context trees for better context management?
#
# [cowork-claude, feb 26] "Is it a chat or is it a log or is it a memory?" — this is a
# real question and the answer probably matters for the Bearing system. If messages are a
# chat, Bearings evaluate against the conversation. If messages are a log, Bearings
# evaluate against what happened. If messages are a memory, Bearings evaluate against
# what was learned. These produce different BearingStatement evaluations.
# The recursive context tree idea connects to otter-centaur's causal DAG — messages
# have causal relationships (this response was caused by that question + that context).
# A tree would let you prune context without losing the causal structure. But that's
# a significant architectural choice. The current flat list works for now.
class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    role = db.Column(db.String(16), nullable=False)     # 'user' | 'assistant'
    content = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship("Session", back_populates="messages")

# OK! THis is -- a think. BVut this is the assignment PART of the thing from the canvas and is one piece of data.
# Does it hold up to how we want to use it? We need it to be the CANVAS model to push -- but is that -- GUH i wish we could work in
# Typescript.
#
# [cowork-claude, feb 26] The tension: this model serves Canvas (push/pull), the
# conversation (crystallization output), the course map (spatial layout), and
# eventually GRAD (rubric governance). Each consumer wants a different shape.
# Canvas wants its API format. The conversation wants the <assignment> JSON shape
# from prompts.py. The course map wants position + module + outcome alignment.
# GRAD wants rubric structure for review.
# Right now Assignment is all of these at once. The TS wish is about making these
# different views explicit in the type system. A TypeScript approach could define
# CanvasAssignment, DraftAssignment, MapAssignment as views over the same data.
# Python can do this too (dataclasses or TypedDicts as view types, model as storage).
# The rubric JSON column is where the most pain will accumulate — it's untyped
# and GRAD will want to validate its structure.

class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=False)
    module_label = db.Column(db.String(64), nullable=False, default="")
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    learning_outcomes = db.Column(db.JSON, nullable=False, default=list)
    aligned_outcomes = db.Column(db.JSON, nullable=False, default=list)
    points_possible = db.Column(db.Integer, nullable=False, default=100)
    submission_types = db.Column(db.JSON, nullable=False, default=list)
    rubric = db.Column(db.JSON, nullable=False, default=list)
    position = db.Column(db.Integer, nullable=True)   # order within module; null = created_at order
    canvas_assignment_id = db.Column(db.String(64), nullable=True)
    canvas_html_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    session = db.relationship("Session", back_populates="assignments")


# ── Course map models ──────────────────────────────────────────────────────────

class LearningOutcome(db.Model):
    """A first-class learning outcome row — replaces the text blob on Course.

    The text blob stays for backward compat with the chatbot flow.
    These rows power the course map.
    """
    __tablename__ = "learning_outcomes"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)
    canvas_outcome_id = db.Column(db.String(64), nullable=True)  # if it came from Canvas
    position = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    course = db.relationship("Course", back_populates="learning_outcome_rows")
    bearings = db.relationship("Bearing", back_populates="learning_outcome", lazy="dynamic")


# [cowork-claude, feb 26] Bearing + BearingStatement is the most interesting
# part of this data model. It's the GhostProtocol endocrine system translated
# into course design. The flow.md describes the aspiration: LLM judges the vibe,
# modulates the conversation, Bearings track what's being navigated toward/away from.
#
# No UI for this yet. CourseMap and WorksheetFrame don't read or write Bearings.
# No endpoint for CRUD on Bearings either. The model is ahead of the app.
# When building UI for this: Bearings are stars, not destinations (see the
# epistemic notice in otter-centaur/LICENSE). The UI should feel navigational,
# not evaluative. A compass, not a scorecard.
#
# The weight/likelihood pair maps to flow.md's "outcome tracking" section:
# weight = how much we care about this direction
# likelihood = how close we think we are
# The delta between them is the signal. High weight + low likelihood = push harder.
# Low weight + high likelihood = maybe this isn't the interesting direction anymore.
#
# BearingStatements are the evidence layer. "Observable thing" that confirms or
# disconfirms. The LLM evaluates these each turn — but that evaluation loop
# isn't built yet either. When it is: be careful about the LLM's pull to affirm.
# The system should be as willing to disconfirm a Bearing as to confirm one.
class Bearing(db.Model):
    """A user story as a navigational star — not a destination, a direction.

    weight    — -1 to 1: how much this matters and in which direction
                positive = sail toward, negative = sail away from
    likelihood — 0 to 1: current estimated probability of this world existing

    A Bearing can be course-level (attached to a LearningOutcome)
    or session-level (emergent from a specific conversation).
    """
    __tablename__ = "bearings"

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey("courses.id"), nullable=True)
    session_id = db.Column(db.Integer, db.ForeignKey("sessions.id"), nullable=True)
    learning_outcome_id = db.Column(db.Integer, db.ForeignKey("learning_outcomes.id"), nullable=True)
    text = db.Column(db.Text, nullable=False)          # the user story, plain language
    weight = db.Column(db.Float, nullable=False, default=0.5)
    likelihood = db.Column(db.Float, nullable=False, default=0.5)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    course = db.relationship("Course", back_populates="bearings")
    learning_outcome = db.relationship("LearningOutcome", back_populates="bearings")
    statements = db.relationship("BearingStatement", back_populates="bearing", lazy="dynamic")


class BearingStatement(db.Model):
    """An observable statement that confirms or disconfirms a Bearing.

    The LLM evaluates these each turn. The bearing's likelihood
    updates from the pattern of observed/disconfirmed statements.
    """
    __tablename__ = "bearing_statements"

    id = db.Column(db.Integer, primary_key=True)
    bearing_id = db.Column(db.Integer, db.ForeignKey("bearings.id"), nullable=False)
    text = db.Column(db.Text, nullable=False)          # observable thing
    observed = db.Column(db.Boolean, nullable=True)    # null = not yet evaluated
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    bearing = db.relationship("Bearing", back_populates="statements")
