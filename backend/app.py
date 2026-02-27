"""
SME Rhizome Builder — Flask backend.

Endpoints:
    GET  /api/auth/login                 → redirect to Canvas OAuth
    GET  /api/auth/callback              → exchange code, set JWT cookie
    GET  /api/auth/me                    → current user (or 401)
    POST /api/auth/logout                → unset JWT cookie

    GET  /api/courses                    → list user's courses
    POST /api/courses                    → create or update a course

    GET  /api/sessions/by-course/<id>    → get (or create) session for course
    GET  /api/sessions/<id>              → full session: messages + assignments

    POST /api/chat                       → conversation turn; persists to DB
    POST /api/canvas/assignment          → push draft to Canvas (uses stored token)
    GET  /api/canvas/assignments         → list Canvas assignments for a course
    GET  /api/canvas/courses             → list Canvas courses user teaches

Environment:
    ANTHROPIC_API_KEY
    CANVAS_CLIENT_ID
    CANVAS_CLIENT_SECRET
    CANVAS_OAUTH_REDIRECT_URI   default http://localhost:5050/api/auth/callback
    CANVAS_BASE_URL             default https://unity.instructure.com
    JWT_SECRET_KEY
    DATABASE_URL                default sqlite:///rhizome.db
"""

import json
import os
import re
import sys

import sqlalchemy
from datetime import datetime, timezone

import anthropic
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    get_jwt_identity,
    jwt_required,
    set_access_cookies,
    unset_jwt_cookies,
)

from admin import admin_bp
from models import Assignment, Bearing, BearingStatement, Course, LearningOutcome, Message, Session, User, db
from prompts import build_system_prompt

load_dotenv()

app = Flask(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
# Can we make this a method?
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///rhizome.db"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
_jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
if not _jwt_secret:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY is not set — using an insecure dev default. "
        "Set JWT_SECRET_KEY in your environment before deploying.",
        stacklevel=2,
    )
    _jwt_secret = "dev-secret-change-me"
app.config["JWT_SECRET_KEY"] = _jwt_secret
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False          # True in production (HTTPS)
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False   # long-lived for dev; restrict in prod

db.init_app(app)
jwt = JWTManager(app)
app.register_blueprint(admin_bp)

# Can you help me understand this syntax? Is CORS just a function? Why is it caps?
# [cowork-claude, feb 26] CORS is a class, instantiated here as a side effect.
# It's caps because it's a class name (Python convention). The constructor
# mutates `app` by registering hooks. It's a common Flask pattern but yeah,
# it looks weird — a class used as a function with no assignment.
CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]}},
    supports_credentials=True,
)

# Once again, begging to be some sort of config object
# [cowork-claude, feb 26] Agreed. These + the JWT config above + the CORS origins
# want to be a config class or .env-driven config object. When this moves to
# production (HTTPS, real JWT expiry, multiple Canvas instances), a Config class
# with dev/staging/prod variants would pay for itself.
CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://unity.instructure.com").rstrip("/")
CANVAS_CLIENT_ID = os.environ.get("CANVAS_CLIENT_ID", "")
CANVAS_CLIENT_SECRET = os.environ.get("CANVAS_CLIENT_SECRET", "")
CANVAS_REDIRECT_URI = os.environ.get(
    "CANVAS_OAUTH_REDIRECT_URI", "http://localhost:5050/api/auth/callback"
)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")


# ── DB init ──────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    # Additive column migrations — silently skipped if column already exists
    _additive_columns = [
        "ALTER TABLE courses ADD COLUMN period_type VARCHAR(32) NOT NULL DEFAULT 'Week'",
        "ALTER TABLE assignments ADD COLUMN position INTEGER",
    ]
    for _stmt in _additive_columns:
        try:
            db.session.execute(sqlalchemy.text(_stmt))
            db.session.commit()
        except Exception:
            db.session.rollback()


# System prompt and course-context rendering → backend/prompts.py


# Why is this? What is it doing?
# [cowork-claude, feb 26] This is the bridge between conversation and artifact.
# The LLM's response may contain an <assignment>JSON</assignment> block inline
# with conversational text. This function separates the two: it pulls out the
# structured assignment data and returns the clean conversational text without it.
# The assignment JSON shape is defined in the "output_format" card in prompts.py.
# If the JSON is malformed, it logs the error and returns the full text as-is
# (graceful degradation — the conversation survives even if crystallization fails).
def _extract_assignment(text: str):
    """Pull <assignment>...</assignment> JSON from model response, if present."""
    match = re.search(r"<assignment>(.*?)</assignment>", text, re.DOTALL)
    if not match:
        return None, text
    raw = match.group(1).strip()
    clean = re.sub(r"<assignment>.*?</assignment>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(raw), clean
    except json.JSONDecodeError as e:
        app.logger.error("Failed to parse assignment JSON from model response: %s\nRaw: %.200s", e, raw)
        return None, text


# ── Auth endpoints ────────────────────────────────────────────────────────────
# All of these endpoints feel big enough to be their own files?
# [cowork-claude, feb 26] Yes, probably. Flask blueprints would be the natural
# split: auth_bp, course_bp, session_bp, canvas_bp, assignment_bp.
# admin.py is already a blueprint — same pattern. The app.py is ~775 lines
# and growing. But this is a "when it hurts enough" refactor, not urgent.
# The current structure is readable and the endpoints are well-labeled.
@app.post("/api/auth/demo")
def auth_demo():
    """Mint a JWT for a local demo user. Only works when Canvas OAuth is not configured."""
    if CANVAS_CLIENT_ID:
        return jsonify({"error": "Demo login is disabled when Canvas OAuth is configured"}), 403

    user = User.query.filter_by(canvas_user_id="demo").first()
    if user is None:
        user = User(canvas_user_id="demo", name="Demo User", email="demo@localhost")
        db.session.add(user)
        db.session.commit()

    jwt_token = create_access_token(identity=str(user.id))
    response = jsonify({"ok": True})
    set_access_cookies(response, jwt_token)
    return response


@app.get("/api/auth/login")
def auth_login():
    """Redirect to Canvas OAuth authorization page."""
    if not CANVAS_CLIENT_ID:
        return jsonify({"error": "Canvas OAuth not configured (CANVAS_CLIENT_ID missing)"}), 503

    # Allow per-request override of canvas base URL for multi-instance support
    base = request.args.get("canvas_base_url", CANVAS_BASE_URL).rstrip("/")
    auth_url = (
        f"{base}/login/oauth2/auth"
        f"?client_id={CANVAS_CLIENT_ID}"
        f"&response_type=code"
        f"&redirect_uri={CANVAS_REDIRECT_URI}"
    )
    return redirect(auth_url)


@app.get("/api/auth/callback")
def auth_callback():
    """Exchange OAuth code for token, upsert user, set JWT cookie."""
    code = request.args.get("code")
    if not code:
        return redirect(f"{FRONTEND_URL}/?auth_error=no_code")

    base = CANVAS_BASE_URL

    # Exchange code for token
    try:
        token_resp = requests.post(
            f"{base}/login/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "client_id": CANVAS_CLIENT_ID,
                "client_secret": CANVAS_CLIENT_SECRET,
                "redirect_uri": CANVAS_REDIRECT_URI,
                "code": code,
            },
            timeout=15,
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception as e:
        app.logger.error("Canvas token exchange failed: %s", e, exc_info=True)
        return redirect(f"{FRONTEND_URL}/?auth_error=token_exchange_failed")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")

    # Fetch user profile from Canvas
    try:
        me_resp = requests.get(
            f"{base}/api/v1/users/self",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        me_resp.raise_for_status()
        canvas_user = me_resp.json()
    except Exception as e:
        app.logger.error("Canvas profile fetch failed: %s", e, exc_info=True)
        return redirect(f"{FRONTEND_URL}/?auth_error=profile_fetch_failed")

    canvas_user_id = str(canvas_user.get("id", ""))
    name = canvas_user.get("name", "")
    email = canvas_user.get("email") or canvas_user.get("login_id", "")

    # Upsert user
    user = User.query.filter_by(canvas_user_id=canvas_user_id).first()
    if user is None:
        user = User(canvas_user_id=canvas_user_id)
        db.session.add(user)

    user.name = name
    user.email = email
    user.canvas_access_token = access_token
    user.canvas_refresh_token = refresh_token
    user.canvas_base_url = base
    if expires_in:
        from datetime import timedelta
        user.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error("DB commit failed during OAuth callback: %s", e, exc_info=True)
        return redirect(f"{FRONTEND_URL}/?auth_error=db_error")

    # Issue JWT
    jwt_token = create_access_token(identity=str(user.id))
    response = redirect(FRONTEND_URL)
    set_access_cookies(response, jwt_token)
    return response


@app.get("/api/auth/me")
@jwt_required()
def auth_me():
    user_id = get_jwt_identity()
    user = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "canvasBaseUrl": user.canvas_base_url,
    })


@app.post("/api/auth/logout")
def auth_logout():
    response = jsonify({"ok": True})
    unset_jwt_cookies(response)
    return response


# ── Course endpoints ──────────────────────────────────────────────────────────

@app.get("/api/courses")
@jwt_required()
def list_courses():
    user = db.session.get(User, int(get_jwt_identity()))
    courses = user.courses.order_by(Course.created_at.desc()).all()
    return jsonify({"courses": [_course_dict(c) for c in courses]})


@app.post("/api/courses")
@jwt_required()
def upsert_course():
    user = db.session.get(User, int(get_jwt_identity()))
    body = request.get_json(force=True)

    course_id = body.get("id")
    if course_id:
        course = db.session.get(Course, int(course_id))
        if not course or course.user_id != user.id:
            return jsonify({"error": "not found"}), 404
    else:
        course = Course(user_id=user.id)
        db.session.add(course)

    course.course_code = body.get("courseCode", course.course_code or "")
    course.course_title = body.get("courseTitle", course.course_title or "")
    course.learning_outcomes = body.get("learningOutcomes", course.learning_outcomes or "")
    course.canvas_course_id = body.get("canvasCourseId") or course.canvas_course_id

    db.session.commit()
    return jsonify(_course_dict(course))


def _course_dict(c: Course) -> dict:
    outcome_rows = [
        {"id": lo.id, "text": lo.text, "position": lo.position}
        for lo in c.learning_outcome_rows
    ]
    return {
        "id": c.id,
        "courseCode": c.course_code,
        "courseTitle": c.course_title,
        "periodType": c.period_type,
        "learningOutcomes": c.learning_outcomes,
        "learningOutcomeRows": outcome_rows,
        "canvasCourseId": c.canvas_course_id,
    }


# ── Session endpoints ─────────────────────────────────────────────────────────

@app.get("/api/sessions/by-course/<int:course_id>")
@jwt_required()
def session_by_course(course_id: int):
    """Get the most-recent session for a course, or create one."""
    user = db.session.get(User, int(get_jwt_identity()))
    course = db.session.get(Course, course_id)
    if not course or course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    sess = (
        Session.query
        .filter_by(user_id=user.id, course_id=course_id)
        .order_by(Session.updated_at.desc())
        .first()
    )
    if sess is None:
        sess = Session(user_id=user.id, course_id=course_id)
        db.session.add(sess)
        db.session.commit()

    return jsonify(_session_summary(sess))


@app.get("/api/sessions/<int:session_id>")
@jwt_required()
def get_session(session_id: int):
    """Full session: messages + assignments."""
    user = db.session.get(User, int(get_jwt_identity()))
    sess = db.session.get(Session, session_id)
    if not sess or sess.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    messages = [
        {"role": m.role, "content": m.content}
        for m in sess.messages.all()
    ]
    assignments = [_assignment_dict(a) for a in sess.assignments.order_by(Assignment.created_at).all()]

    return jsonify({
        **_session_summary(sess),
        "messages": messages,
        "assignments": assignments,
    })


def _session_summary(sess: Session) -> dict:
    return {
        "id": sess.id,
        "courseId": sess.course_id,
        "createdAt": sess.created_at.isoformat(),
        "updatedAt": sess.updated_at.isoformat(),
    }


def _assignment_dict(a: Assignment) -> dict:
    return {
        "id": a.id,
        "module": a.module_label,
        "title": a.title,
        "description": a.description,
        "learning_outcomes": a.learning_outcomes,
        "aligned_outcomes": a.aligned_outcomes,
        "points_possible": a.points_possible,
        "submission_types": a.submission_types,
        "rubric": a.rubric,
        "position": a.position,
        "canvas_assignment_id": a.canvas_assignment_id,
        "canvas_html_url": a.canvas_html_url,
    }


# ── Assignment endpoints (editor-driven, no chat required) ────────────────────

@app.get("/api/assignments")
@jwt_required()
def list_assignments():
    """All assignments for a course, ordered by creation time."""
    user = db.session.get(User, int(get_jwt_identity()))
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = db.session.get(Course, course_id)
    if not course or course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    assignments = (
        Assignment.query
        .join(Session, Assignment.session_id == Session.id)
        .filter(Session.course_id == course_id, Session.user_id == user.id)
        .order_by(
            Assignment.position.is_(None),   # nulls last
            Assignment.position,
            Assignment.created_at,
        )
        .all()
    )
    return jsonify({"assignments": [_assignment_dict(a) for a in assignments]})


@app.post("/api/assignments")
@jwt_required()
def create_assignment():
    """Create an assignment from the editor (no conversation required).

    Gets or creates a default session for the course, then persists the assignment.
    """
    user = db.session.get(User, int(get_jwt_identity()))
    body = request.get_json(force=True)

    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = db.session.get(Course, int(course_id))
    if not course or course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    # Get or create the default session for this course
    sess = (
        Session.query
        .filter_by(user_id=user.id, course_id=course.id)
        .order_by(Session.updated_at.desc())
        .first()
    )
    if sess is None:
        sess = Session(user_id=user.id, course_id=course.id)
        db.session.add(sess)
        db.session.flush()

    # Resolve outcome IDs → text for aligned_outcomes
    outcome_ids = body.get("aligned_outcome_ids", [])
    aligned_texts = []
    if outcome_ids:
        rows = LearningOutcome.query.filter(
            LearningOutcome.id.in_(outcome_ids),
            LearningOutcome.course_id == course.id,
        ).all()
        aligned_texts = [lo.text for lo in rows]

    # Assign position = next after the last in this module
    module_label = body.get("module_label", "")
    last = (
        Assignment.query
        .join(Session, Assignment.session_id == Session.id)
        .filter(
            Session.course_id == course.id,
            Assignment.module_label == module_label,
            Assignment.position.isnot(None),
        )
        .order_by(Assignment.position.desc())
        .first()
    )
    next_position = (last.position + 1) if last else 0

    a = Assignment(
        session_id=sess.id,
        module_label=module_label,
        title=body.get("title") or "Untitled",
        description=body.get("description", ""),
        aligned_outcomes=aligned_texts,
        learning_outcomes=[],
        submission_types=["online_text_entry"],
        rubric=[],
        position=next_position,
    )
    db.session.add(a)
    sess.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify(_assignment_dict(a)), 201


@app.patch("/api/assignments/<string:assignment_id>")
@jwt_required()
def patch_assignment(assignment_id: str):
    """Update position (reorder) or title/description of an assignment."""
    user = db.session.get(User, int(get_jwt_identity()))
    a = db.session.get(Assignment, assignment_id)
    if not a or a.session.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    if "position" in body:
        a.position = int(body["position"])
    if "title" in body:
        a.title = body["title"] or a.title
    if "description" in body:
        a.description = body["description"]

    db.session.commit()
    return jsonify(_assignment_dict(a))


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
@jwt_required()
def chat():
    user = db.session.get(User, int(get_jwt_identity()))
    body = request.get_json(force=True)

    messages = body.get("messages", [])
    if not messages:
        return jsonify({"error": "no messages"}), 400

    session_id = body.get("session_id")
    sess = None
    if session_id:
        sess = db.session.get(Session, int(session_id))
        if sess and sess.user_id != user.id:
            sess = None

    anthropic_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
    ]

    api_key = body.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    endpoint = body.get("endpoint", "anthropic")
    base_url = body.get("base_url") or None
    model_override = body.get("model") or None

    # Ollama doesn't need an API key; everything else does
    if not api_key and endpoint != "ollama":
        return jsonify({"error": "No API key — set one in Settings (⚙) or via ANTHROPIC_API_KEY env"}), 503

    # Build system prompt from course if session is linked
    course = None
    if sess and sess.course_id:
        course = db.session.get(Course, sess.course_id)
    system_prompt = build_system_prompt(course)

    try:
        if endpoint in ("openai", "ollama"):
            from openai import OpenAI
            defaults = {
                "ollama": ("http://localhost:11434/v1", "qwen2.5:7b", api_key or "ollama"),
                "openai": ("https://api.openai.com/v1", "gpt-4o-mini", api_key),
            }
            default_base, default_model, oa_key = defaults[endpoint]
            oa_client = OpenAI(api_key=oa_key, base_url=base_url or default_base)
            oa_response = oa_client.chat.completions.create(
                model=model_override or default_model,
                max_tokens=2048,
                messages=[{"role": "system", "content": system_prompt}] + anthropic_messages,
            )
            full_text = oa_response.choices[0].message.content or ""
        else:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model_override or "claude-haiku-4-5-20251001",
                max_tokens=2048,
                system=system_prompt,
                messages=anthropic_messages,
            )
            full_text = response.content[0].text
    except Exception as e:
        app.logger.error("AI API error (%s): %s", endpoint, e, exc_info=True)
        return jsonify({"error": str(e)}), 500
    assignment_data, reply = _extract_assignment(full_text)

    # Persist to DB if we have a session
    if sess:
        # Determine next position
        last_msg = sess.messages.order_by(Message.position.desc()).first()
        next_pos = (last_msg.position + 1) if last_msg else 0

        # The last message in `messages` is the new user message
        # We persist the user message + the assistant reply
        user_msg_content = messages[-1]["content"] if messages[-1]["role"] == "user" else None
        if user_msg_content:
            db.session.add(Message(
                session_id=sess.id,
                role="user",
                content=user_msg_content,
                position=next_pos,
            ))
            next_pos += 1

        db.session.add(Message(
            session_id=sess.id,
            role="assistant",
            content=reply,
            position=next_pos,
        ))

        if assignment_data:
            a = Assignment(
                session_id=sess.id,
                module_label=assignment_data.get("module", ""),
                title=assignment_data.get("title", "Untitled"),
                description=assignment_data.get("description", ""),
                learning_outcomes=assignment_data.get("learning_outcomes", []),
                aligned_outcomes=assignment_data.get("aligned_outcomes", []),
                points_possible=assignment_data.get("points_possible", 100),
                submission_types=assignment_data.get("submission_types", []),
                rubric=assignment_data.get("rubric", []),
            )
            db.session.add(a)
            db.session.flush()  # get a.id before commit
            assignment_data["id"] = a.id

        sess.updated_at = datetime.utcnow()
        db.session.commit()

    return jsonify({"reply": reply, "assignment": assignment_data})


# ── Bearing endpoints ────────────────────────────────────────────────────────
# The learning designer's compass. Stars, not destinations.
# Bearings are set before or after the SME conversation —
# they're the designer's sense of which directions matter
# and the record of what happened relative to those directions.

@app.get("/api/bearings")
@jwt_required()
def list_bearings():
    """All bearings for a course, with their statements."""
    user = db.session.get(User, int(get_jwt_identity()))
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = db.session.get(Course, course_id)
    if not course or course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    bearings = course.bearings.order_by(Bearing.created_at).all()
    return jsonify({"bearings": [_bearing_dict(b) for b in bearings]})


@app.post("/api/bearings")
@jwt_required()
def create_bearing():
    """Set a new navigational star for a course.

    Optionally linked to a learning outcome — the star this bearing
    is oriented relative to.
    """
    user = db.session.get(User, int(get_jwt_identity()))
    body = request.get_json(force=True)

    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = db.session.get(Course, int(course_id))
    if not course or course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required — what direction is this bearing?"}), 400

    b = Bearing(
        course_id=course.id,
        session_id=body.get("session_id"),
        learning_outcome_id=body.get("learning_outcome_id"),
        text=text,
        weight=body.get("weight", 0.5),
        likelihood=body.get("likelihood", 0.5),
    )
    db.session.add(b)
    db.session.commit()

    return jsonify(_bearing_dict(b)), 201


@app.patch("/api/bearings/<int:bearing_id>")
@jwt_required()
def update_bearing(bearing_id: int):
    """Update a bearing's weight, likelihood, or text.

    The delta between weight and likelihood is the signal.
    High weight + low likelihood = push harder.
    Low weight + high likelihood = maybe this isn't the interesting direction anymore.
    """
    user = db.session.get(User, int(get_jwt_identity()))
    b = db.session.get(Bearing, bearing_id)
    if not b or not b.course or b.course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    if "text" in body:
        b.text = body["text"]
    if "weight" in body:
        b.weight = max(-1.0, min(1.0, float(body["weight"])))
    if "likelihood" in body:
        b.likelihood = max(0.0, min(1.0, float(body["likelihood"])))

    db.session.commit()
    return jsonify(_bearing_dict(b))


@app.delete("/api/bearings/<int:bearing_id>")
@jwt_required()
def delete_bearing(bearing_id: int):
    """Remove a bearing and its statements."""
    user = db.session.get(User, int(get_jwt_identity()))
    b = db.session.get(Bearing, bearing_id)
    if not b or not b.course or b.course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    # Remove statements first
    BearingStatement.query.filter_by(bearing_id=b.id).delete()
    db.session.delete(b)
    db.session.commit()
    return jsonify({"ok": True})


# ── BearingStatement endpoints ───────────────────────────────────────────────

@app.post("/api/bearings/<int:bearing_id>/statements")
@jwt_required()
def create_statement(bearing_id: int):
    """Add an observable statement to a bearing.

    These are the evidence layer — concrete things the designer
    expects to see (or not see) if this bearing is being sailed toward.
    """
    user = db.session.get(User, int(get_jwt_identity()))
    b = db.session.get(Bearing, bearing_id)
    if not b or not b.course or b.course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required — what would you observe?"}), 400

    s = BearingStatement(
        bearing_id=b.id,
        text=text,
        observed=body.get("observed"),  # null = not yet evaluated
    )
    db.session.add(s)
    db.session.commit()
    return jsonify(_statement_dict(s)), 201


@app.patch("/api/statements/<int:statement_id>")
@jwt_required()
def update_statement(statement_id: int):
    """Mark a statement as observed (true), disconfirmed (false), or reset (null)."""
    user = db.session.get(User, int(get_jwt_identity()))
    s = db.session.get(BearingStatement, statement_id)
    if not s or not s.bearing.course or s.bearing.course.user_id != user.id:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    if "observed" in body:
        s.observed = body["observed"]  # true, false, or null
    if "text" in body:
        s.text = body["text"]

    db.session.commit()
    return jsonify(_statement_dict(s))


def _bearing_dict(b: Bearing) -> dict:
    statements = [_statement_dict(s) for s in b.statements.all()]
    return {
        "id": b.id,
        "courseId": b.course_id,
        "sessionId": b.session_id,
        "learningOutcomeId": b.learning_outcome_id,
        "text": b.text,
        "weight": b.weight,
        "likelihood": b.likelihood,
        "delta": b.weight - b.likelihood,
        "statements": statements,
        "createdAt": b.created_at.isoformat(),
        "updatedAt": b.updated_at.isoformat(),
    }


def _statement_dict(s: BearingStatement) -> dict:
    return {
        "id": s.id,
        "bearingId": s.bearing_id,
        "text": s.text,
        "observed": s.observed,
        "createdAt": s.created_at.isoformat(),
    }


# ── Canvas endpoints ──────────────────────────────────────────────────────────

def _canvas_token_and_base(user: User) -> tuple[str, str]:
    """Return (token, base_url) from stored user record."""
    return user.canvas_access_token or "", user.canvas_base_url.rstrip("/")


@app.post("/api/canvas/assignment")
@jwt_required()
def canvas_assignment():
    user = db.session.get(User, int(get_jwt_identity()))
    body = request.get_json(force=True)
    draft = body.get("assignment")
    if not draft:
        return jsonify({"error": "no assignment"}), 400

    token, base_url = _canvas_token_and_base(user)
    course_id = body.get("canvas_course_id")

    if not token:
        return jsonify({"error": "No Canvas access token — please sign in via Canvas OAuth"}), 503
    # [cowork-claude, feb 26] Fixed: course_id check was unreachable (after token return).
    if not course_id:
        return jsonify({"error": "canvas_course_id required"}), 400

    canvas_payload = {
        "assignment": {
            "name": draft.get("title", "Untitled Assignment"),
            "description": draft.get("description", ""),
            "points_possible": draft.get("points_possible", 100),
            "submission_types": draft.get("submission_types", ["online_text_entry"]),
            "published": False,
        }
    }

    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=canvas_payload, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.HTTPError as e:
        return jsonify({"error": f"Canvas API error: {e.response.status_code}"}), 502
    except requests.RequestException as e:
        return jsonify({"error": f"Canvas request failed: {e}"}), 502

    data = resp.json()
    canvas_id = str(data.get("id", ""))
    html_url = data.get("html_url", "")

    # Update Assignment record if id provided
    assignment_id = body.get("assignment_id")
    if assignment_id:
        a = db.session.get(Assignment, str(assignment_id))
        if a and a.session.user_id == user.id:
            a.canvas_assignment_id = canvas_id
            a.canvas_html_url = html_url
            db.session.commit()

    return jsonify({"canvas_id": canvas_id, "html_url": html_url})


@app.get("/api/canvas/assignments")
@jwt_required()
def canvas_list_assignments():
    user = db.session.get(User, int(get_jwt_identity()))
    token, base_url = _canvas_token_and_base(user)
    course_id = request.args.get("canvas_course_id")

    if not token:
        return jsonify({"error": "No Canvas access token"}), 503
    if not course_id:
        return jsonify({"error": "canvas_course_id required"}), 400

    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"per_page": 100, "include[]": "rubric"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
    except requests.HTTPError as e:
        return jsonify({"error": f"Canvas API error: {e.response.status_code}"}), 502
    except requests.RequestException as e:
        return jsonify({"error": f"Canvas request failed: {e}"}), 502

    simplified = [
        {
            "id": a.get("id"),
            "name": a.get("name"),
            "points_possible": a.get("points_possible"),
            "html_url": a.get("html_url"),
            "has_rubric": bool(a.get("rubric")),
        }
        for a in resp.json()
        if isinstance(a, dict)
    ]
    return jsonify({"assignments": simplified})


@app.get("/api/canvas/courses")
@jwt_required()
def canvas_list_courses():
    """List Canvas courses the user teaches (enrollment_type=teacher)."""
    user = db.session.get(User, int(get_jwt_identity()))
    token, base_url = _canvas_token_and_base(user)

    if not token:
        return jsonify({"error": "No Canvas access token"}), 503

    url = f"{base_url}/api/v1/courses"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"enrollment_type": "teacher", "per_page": 100, "state[]": "available"}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
    except requests.HTTPError as e:
        return jsonify({"error": f"Canvas API error: {e.response.status_code}"}), 502
    except requests.RequestException as e:
        return jsonify({"error": f"Canvas request failed: {e}"}), 502

    simplified = [
        {
            "id": c.get("id"),
            "name": c.get("name"),
            "course_code": c.get("course_code"),
        }
        for c in resp.json()
        if isinstance(c, dict)
    ]
    return jsonify({"courses": simplified})


if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 5050))
    print(f"sme-rhizome-builder backend → http://localhost:{port}")
    app.run(host="localhost", port=port, debug=True)
