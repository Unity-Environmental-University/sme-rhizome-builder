"""
SME Rhizome Builder — Flask backend.

Endpoints:
    GET  /api/auth/login                 → redirect to Canvas OAuth
    GET  /api/auth/callback              → exchange code, set JWT cookie
    POST /api/auth/demo                  → demo login (no Canvas OAuth required)
    GET  /api/auth/me                    → current user (or 401)
    POST /api/auth/logout                → unset JWT cookie

    GET  /api/courses                    → list user's courses
    POST /api/courses                    → create or update a course

    GET  /api/assignments?course_id=N    → list assignments for a course
    POST /api/assignments                → create assignment from editor
    PATCH /api/assignments/<id>          → update position / title / description

    POST /api/chat                       → conversation turn; persists messages to context
    POST /api/canvas/assignment          → push draft to Canvas
    GET  /api/canvas/assignments         → list Canvas assignments for a course
    GET  /api/canvas/courses             → list Canvas courses user teaches

    GET  /api/bearings?course_id=N       → list bearings for a course
    POST /api/bearings                   → create a bearing
    PATCH /api/bearings/<id>             → update weight / likelihood / text
    DELETE /api/bearings/<id>            → remove bearing + statements
    POST /api/bearings/<id>/statements   → add observable statement
    PATCH /api/statements/<id>           → mark observed / disconfirmed / reset

Environment:
    ANTHROPIC_API_KEY
    CANVAS_CLIENT_ID
    CANVAS_CLIENT_SECRET
    CANVAS_OAUTH_REDIRECT_URI   default http://localhost:5050/api/auth/callback
    CANVAS_BASE_URL             default https://unity.instructure.com
    JWT_SECRET_KEY
    DATABASE_PATH               default backend/rhizome.db
"""

import json
import os
import re
import sys

from datetime import datetime, timedelta, timezone

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
from db import get_db, init_db
from prompts import build_system_prompt
import queries as q

load_dotenv()

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

_jwt_secret = os.environ.get("JWT_SECRET_KEY", "")
if not _jwt_secret:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY is not set — using an insecure dev default. "
        "Set JWT_SECRET_KEY before deploying.",
        stacklevel=2,
    )
    _jwt_secret = "dev-secret-change-me"

app.config["JWT_SECRET_KEY"] = _jwt_secret
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_SECURE"] = False          # True in production (HTTPS)
app.config["JWT_COOKIE_SAMESITE"] = "Lax"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = False   # long-lived for dev; restrict in prod

jwt = JWTManager(app)
app.register_blueprint(admin_bp)

# CORS is a class mutating app as a side effect — common Flask pattern.
# See CORS docs; origins can be env-driven when this moves to production.
CORS(
    app,
    resources={r"/api/*": {"origins": [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
    ]}},
    supports_credentials=True,
)

CANVAS_BASE_URL = os.environ.get("CANVAS_BASE_URL", "https://unity.instructure.com").rstrip("/")
CANVAS_CLIENT_ID = os.environ.get("CANVAS_CLIENT_ID", "")
CANVAS_CLIENT_SECRET = os.environ.get("CANVAS_CLIENT_SECRET", "")
CANVAS_REDIRECT_URI = os.environ.get(
    "CANVAS_OAUTH_REDIRECT_URI", "http://localhost:5050/api/auth/callback"
)
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

init_db(app)


# ── Response helpers ──────────────────────────────────────────────────────────

def _course_dict(course, outcome_rows) -> dict:
    return {
        "id": course["id"],
        "courseCode": course["course_code"],
        "courseTitle": course["course_title"],
        "periodType": course["period_type"],
        "learningOutcomes": course["learning_outcomes"],
        "learningOutcomeRows": [
            {"id": lo["id"], "text": lo["text"], "position": lo["position"]}
            for lo in outcome_rows
        ],
        "canvasCourseId": course["canvas_course_id"],
    }


def _assignment_dict(a) -> dict:
    def _j(val):
        return json.loads(val) if isinstance(val, str) else (val or [])

    return {
        "id": a["id"],
        "module": a["module_label"],
        "title": a["title"],
        "description": a["description"],
        "learning_outcomes": _j(a["learning_outcomes"]),
        "aligned_outcomes": _j(a["aligned_outcomes"]),
        "points_possible": a["points_possible"],
        "submission_types": _j(a["submission_types"]),
        "rubric": _j(a["rubric"]),
        "position": a["position"],
        "canvas_assignment_id": a["canvas_assignment_id"],
        "canvas_html_url": a["canvas_html_url"],
    }


def _bearing_dict(b, statements) -> dict:
    return {
        "id": b["id"],
        "courseId": b["course_id"],
        "learningOutcomeId": b["learning_outcome_id"],
        "text": b["text"],
        "weight": b["weight"],
        "likelihood": b["likelihood"],
        "delta": b["weight"] - b["likelihood"],
        "statements": [_statement_dict(s) for s in statements],
        "createdAt": b["created_at"],
        "updatedAt": b["updated_at"],
    }


def _statement_dict(s) -> dict:
    return {
        "id": s["id"],
        "bearingId": s["bearing_id"],
        "text": s["text"],
        "observed": s["observed"],
        "createdAt": s["created_at"],
    }


def _course_context_for_prompt(conn, course) -> dict:
    """Build the dict that build_system_prompt expects."""
    outcome_rows = q.list_learning_outcomes(conn, course["id"])
    bearings = q.list_bearings(conn, course["id"])
    bearing_dicts = []
    for b in bearings:
        statements = q.list_statements(conn, b["id"])
        bearing_dicts.append({
            "text": b["text"],
            "weight": b["weight"],
            "likelihood": b["likelihood"],
            "statements": [{"text": s["text"], "observed": s["observed"]} for s in statements],
        })
    return {
        "course_code": course["course_code"],
        "course_title": course["course_title"],
        "learning_outcomes": course["learning_outcomes"],
        "learning_outcome_rows": [{"id": lo["id"], "text": lo["text"], "position": lo["position"]} for lo in outcome_rows],
        "bearings": bearing_dicts,
    }


# ── Extract assignment from model response ────────────────────────────────────

def _extract_assignment(text: str):
    """Pull <assignment>...</assignment> JSON from model response, if present.

    Returns (assignment_dict_or_None, clean_text).
    If JSON is malformed, logs the error and returns (None, original_text) —
    the conversation survives even if crystallization fails.
    """
    match = re.search(r"<assignment>(.*?)</assignment>", text, re.DOTALL)
    if not match:
        return None, text
    raw = match.group(1).strip()
    clean = re.sub(r"<assignment>.*?</assignment>", "", text, flags=re.DOTALL).strip()
    try:
        return json.loads(raw), clean
    except json.JSONDecodeError as e:
        app.logger.error("Failed to parse assignment JSON: %s\nRaw: %.200s", e, raw)
        return None, text


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/api/auth/demo")
def auth_demo():
    """Mint a JWT for a local demo user. Only works when Canvas OAuth is not configured."""
    if CANVAS_CLIENT_ID:
        return jsonify({"error": "Demo login is disabled when Canvas OAuth is configured"}), 403

    conn = get_db()
    user = q.create_demo_user(conn)
    jwt_token = create_access_token(identity=str(user["id"]))
    response = jsonify({"ok": True})
    set_access_cookies(response, jwt_token)
    return response


@app.get("/api/auth/login")
def auth_login():
    """Redirect to Canvas OAuth authorization page."""
    if not CANVAS_CLIENT_ID:
        return jsonify({"error": "Canvas OAuth not configured (CANVAS_CLIENT_ID missing)"}), 503

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
    token_expires_at = None
    if expires_in:
        token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat()

    conn = get_db()
    try:
        user = q.upsert_user(
            conn, canvas_user_id, name, email,
            canvas_access_token=access_token,
            canvas_refresh_token=refresh_token,
            token_expires_at=token_expires_at,
            canvas_base_url=base,
        )
    except Exception as e:
        app.logger.error("DB upsert failed during OAuth callback: %s", e, exc_info=True)
        return redirect(f"{FRONTEND_URL}/?auth_error=db_error")

    jwt_token = create_access_token(identity=str(user["id"]))
    response = redirect(FRONTEND_URL)
    set_access_cookies(response, jwt_token)
    return response


@app.get("/api/auth/me")
@jwt_required()
def auth_me():
    conn = get_db()
    user = q.get_user(conn, int(get_jwt_identity()))
    if not user:
        return jsonify({"error": "user not found"}), 404
    return jsonify({
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "canvasBaseUrl": user["canvas_base_url"],
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
    conn = get_db()
    user_id = int(get_jwt_identity())
    courses = q.list_courses(conn, user_id)
    result = []
    for c in courses:
        outcome_rows = q.list_learning_outcomes(conn, c["id"])
        result.append(_course_dict(c, outcome_rows))
    return jsonify({"courses": result})


@app.post("/api/courses")
@jwt_required()
def upsert_course():
    conn = get_db()
    user_id = int(get_jwt_identity())
    body = request.get_json(force=True)

    course_id = body.get("id")
    if course_id:
        course = q.get_course(conn, int(course_id), user_id)
        if not course:
            return jsonify({"error": "not found"}), 404
        course = q.update_course(
            conn, course["id"],
            body.get("courseCode", course["course_code"]),
            body.get("courseTitle", course["course_title"]),
            body.get("learningOutcomes", course["learning_outcomes"]),
            body.get("canvasCourseId") or course["canvas_course_id"],
        )
    else:
        course = q.create_course(
            conn, user_id,
            course_code=body.get("courseCode", ""),
            course_title=body.get("courseTitle", ""),
            learning_outcomes=body.get("learningOutcomes", ""),
            canvas_course_id=body.get("canvasCourseId"),
        )

    outcome_rows = q.list_learning_outcomes(conn, course["id"])
    return jsonify(_course_dict(course, outcome_rows))


# ── Assignment endpoints ───────────────────────────────────────────────────────

@app.get("/api/assignments")
@jwt_required()
def list_assignments():
    conn = get_db()
    user_id = int(get_jwt_identity())
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    if not q.get_course(conn, course_id, user_id):
        return jsonify({"error": "not found"}), 404

    assignments = q.list_assignments(conn, course_id, user_id)
    return jsonify({"assignments": [_assignment_dict(a) for a in assignments]})


@app.post("/api/assignments")
@jwt_required()
def create_assignment():
    """Create an assignment from the editor. No conversation required."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    body = request.get_json(force=True)

    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = q.get_course(conn, int(course_id), user_id)
    if not course:
        return jsonify({"error": "not found"}), 404

    # Resolve outcome IDs → text
    outcome_ids = body.get("aligned_outcome_ids", [])
    aligned_texts = []
    if outcome_ids:
        rows = q.get_learning_outcomes_by_ids(conn, outcome_ids, course["id"])
        aligned_texts = [lo["text"] for lo in rows]

    module_label = body.get("module_label", "")
    position = q.next_position_in_module(conn, course["id"], user_id, module_label)

    a = q.create_assignment(
        conn,
        user_id=user_id,
        course_id=course["id"],
        module_label=module_label,
        title=body.get("title") or "Untitled",
        description=body.get("description", ""),
        aligned_outcomes=aligned_texts,
        submission_types=["online_text_entry"],
        position=position,
    )
    return jsonify(_assignment_dict(a)), 201


@app.patch("/api/assignments/<string:assignment_id>")
@jwt_required()
def patch_assignment(assignment_id: str):
    """Update position (reorder) or title/description of an assignment."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    a = q.get_assignment(conn, assignment_id, user_id)
    if not a:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    updates = {}
    if "position" in body:
        updates["position"] = int(body["position"])
    if "title" in body:
        updates["title"] = body["title"] or a["title"]
    if "description" in body:
        updates["description"] = body["description"]

    a = q.update_assignment(conn, assignment_id, user_id, **updates)
    return jsonify(_assignment_dict(a))


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/chat")
@jwt_required()
def chat():
    """Conversation turn.

    Persists messages to a context (context_type + context_id).
    context_type: 'assignment' | 'course' | 'thread'
    context_id:   id of that thing

    If course_id is provided, builds the system prompt from course context.
    If an assignment crystallizes, saves it to the course.
    """
    conn = get_db()
    user_id = int(get_jwt_identity())
    body = request.get_json(force=True)

    messages = body.get("messages", [])
    if not messages:
        return jsonify({"error": "no messages"}), 400

    context_type = body.get("context_type")
    context_id = str(body.get("context_id", ""))

    api_key = body.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    endpoint = body.get("endpoint", "anthropic")
    base_url = body.get("base_url") or None
    model_override = body.get("model") or None

    if not api_key and endpoint != "ollama":
        return jsonify({"error": "No API key — set one in Settings (⚙) or via ANTHROPIC_API_KEY env"}), 503

    # Build system prompt from course context if available
    course_id = body.get("course_id")
    course_data = None
    if course_id:
        course = q.get_course(conn, int(course_id), user_id)
        if course:
            course_data = _course_context_for_prompt(conn, course)

    system_prompt = build_system_prompt(course_data)

    anthropic_messages = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
    ]

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

    # Persist to log if we have a context
    if context_type and context_id:
        user_msg_content = messages[-1]["content"] if messages[-1]["role"] == "user" else None
        user_entry = None
        if user_msg_content:
            user_entry = q.append_log(conn, user_id, context_type, context_id, "ai_turn", user_msg_content)
        q.append_log(conn, user_id, context_type, context_id, "ai_turn", reply,
                     replied_to=user_entry["id"] if user_entry else None)

    # Persist crystallized assignment if we have a course
    if assignment_data and course_id:
        course = q.get_course(conn, int(course_id), user_id)
        if course:
            a = q.create_assignment(
                conn,
                user_id=user_id,
                course_id=course["id"],
                module_label=assignment_data.get("module", ""),
                title=assignment_data.get("title", "Untitled"),
                description=assignment_data.get("description", ""),
                learning_outcomes=assignment_data.get("learning_outcomes", []),
                aligned_outcomes=assignment_data.get("aligned_outcomes", []),
                points_possible=assignment_data.get("points_possible", 100),
                submission_types=assignment_data.get("submission_types", []),
                rubric=assignment_data.get("rubric", []),
            )
            assignment_data["id"] = a["id"]

    return jsonify({"reply": reply, "assignment": assignment_data})


# ── Bearing endpoints ──────────────────────────────────────────────────────────
# The learning designer's compass. Stars, not destinations.

@app.get("/api/bearings")
@jwt_required()
def list_bearings():
    conn = get_db()
    user_id = int(get_jwt_identity())
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    if not q.get_course(conn, course_id, user_id):
        return jsonify({"error": "not found"}), 404

    bearings = q.list_bearings(conn, course_id)
    result = []
    for b in bearings:
        statements = q.list_statements(conn, b["id"])
        result.append(_bearing_dict(b, statements))
    return jsonify({"bearings": result})


@app.post("/api/bearings")
@jwt_required()
def create_bearing():
    conn = get_db()
    user_id = int(get_jwt_identity())
    body = request.get_json(force=True)

    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    if not q.get_course(conn, int(course_id), user_id):
        return jsonify({"error": "not found"}), 404

    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required — what direction is this bearing?"}), 400

    b = q.create_bearing(
        conn,
        course_id=int(course_id),
        text=text,
        weight=body.get("weight", 0.5),
        likelihood=body.get("likelihood", 0.5),
        learning_outcome_id=body.get("learning_outcome_id"),
    )
    return jsonify(_bearing_dict(b, [])), 201


@app.patch("/api/bearings/<int:bearing_id>")
@jwt_required()
def update_bearing(bearing_id: int):
    """Update a bearing's weight, likelihood, or text.

    The delta between weight and likelihood is the signal:
    high weight + low likelihood = push harder.
    """
    conn = get_db()
    user_id = int(get_jwt_identity())
    b = q.get_bearing(conn, bearing_id)
    if not b:
        return jsonify({"error": "not found"}), 404

    # Ownership check via course
    if not q.get_course(conn, b["course_id"], user_id):
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    updates = {}
    if "text" in body:
        updates["text"] = body["text"]
    if "weight" in body:
        updates["weight"] = max(-1.0, min(1.0, float(body["weight"])))
    if "likelihood" in body:
        updates["likelihood"] = max(0.0, min(1.0, float(body["likelihood"])))

    b = q.update_bearing(conn, bearing_id, **updates)
    statements = q.list_statements(conn, bearing_id)
    return jsonify(_bearing_dict(b, statements))


@app.delete("/api/bearings/<int:bearing_id>")
@jwt_required()
def delete_bearing(bearing_id: int):
    conn = get_db()
    user_id = int(get_jwt_identity())
    b = q.get_bearing(conn, bearing_id)
    if not b:
        return jsonify({"error": "not found"}), 404

    if not q.get_course(conn, b["course_id"], user_id):
        return jsonify({"error": "not found"}), 404

    q.delete_bearing(conn, bearing_id)
    return jsonify({"ok": True})


@app.post("/api/bearings/<int:bearing_id>/statements")
@jwt_required()
def create_statement(bearing_id: int):
    """Add an observable statement to a bearing — the evidence layer."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    b = q.get_bearing(conn, bearing_id)
    if not b:
        return jsonify({"error": "not found"}), 404

    if not q.get_course(conn, b["course_id"], user_id):
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required — what would you observe?"}), 400

    s = q.create_statement(conn, bearing_id, text, observed=body.get("observed"))
    return jsonify(_statement_dict(s)), 201


@app.patch("/api/statements/<int:statement_id>")
@jwt_required()
def update_statement(statement_id: int):
    """Mark a statement as observed (true), disconfirmed (false), or reset (null)."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    s = q.get_statement(conn, statement_id)
    if not s:
        return jsonify({"error": "not found"}), 404

    # Ownership: statement → bearing → course → user
    b = q.get_bearing(conn, s["bearing_id"])
    if not b or not q.get_course(conn, b["course_id"], user_id):
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    updates = {}
    if "observed" in body:
        updates["observed"] = body["observed"]
    if "text" in body:
        updates["text"] = body["text"]

    s = q.update_statement(conn, statement_id, **updates)
    return jsonify(_statement_dict(s))


# ── Canvas endpoints ──────────────────────────────────────────────────────────

def _canvas_creds(user) -> tuple[str, str]:
    return user["canvas_access_token"] or "", user["canvas_base_url"].rstrip("/")


@app.post("/api/canvas/assignment")
@jwt_required()
def canvas_assignment():
    conn = get_db()
    user = q.get_user(conn, int(get_jwt_identity()))
    body = request.get_json(force=True)
    draft = body.get("assignment")
    if not draft:
        return jsonify({"error": "no assignment"}), 400

    token, base_url = _canvas_creds(user)
    canvas_course_id = body.get("canvas_course_id")

    if not token:
        return jsonify({"error": "No Canvas access token — please sign in via Canvas OAuth"}), 503
    if not canvas_course_id:
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

    url = f"{base_url}/api/v1/courses/{canvas_course_id}/assignments"
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

    # Update local assignment record if id provided
    assignment_id = body.get("assignment_id")
    if assignment_id:
        q.update_assignment(
            conn, str(assignment_id), user["id"],
            canvas_assignment_id=canvas_id,
            canvas_html_url=html_url,
        )

    return jsonify({"canvas_id": canvas_id, "html_url": html_url})


@app.get("/api/canvas/assignments")
@jwt_required()
def canvas_list_assignments():
    conn = get_db()
    user = q.get_user(conn, int(get_jwt_identity()))
    token, base_url = _canvas_creds(user)
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
    """List Canvas courses the user teaches."""
    conn = get_db()
    user = q.get_user(conn, int(get_jwt_identity()))
    token, base_url = _canvas_creds(user)

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
