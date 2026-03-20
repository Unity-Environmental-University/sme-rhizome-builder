"""
SME Rhizome Builder — Flask backend.

Core endpoints (auth, courses, assignments, chat).
Canvas proxy routes → canvas.py
Bearing routes      → bearings.py
Admin dashboard     → admin.py

Endpoints:
    GET  /api/auth/login                 → redirect to Canvas OAuth
    GET  /api/auth/callback              → exchange code, set JWT cookie
    POST /api/auth/demo                  → demo login (no Canvas OAuth required)
    GET  /api/auth/me                    → current user (or 401)
    POST /api/auth/logout                → unset JWT cookie

    GET  /api/courses                    → list user's courses
    POST /api/courses                    → create or update a course

    GET  /api/modules?course_id=N        → list modules for a course

    GET  /api/assignments?course_id=N    → list assignments for a course
    POST /api/assignments                → create assignment from editor
    PATCH /api/assignments/<id>          → update position / title
    POST /api/assignments/<id>/snapshots → save a snapshot (manual or canvas push)

    GET  /api/log/<assignment_id>        → list log entries for an assignment
    POST /api/log/<assignment_id>        → append a log entry for an assignment

    POST /api/chat                       → conversation turn; persists to log

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

from datetime import datetime, timedelta, timezone

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
from ai import call_ai
from bearings import bearings_bp
from canvas import canvas_bp
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
app.register_blueprint(bearings_bp)
app.register_blueprint(canvas_bp)

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


def _assignment_dict(a, snapshot=None) -> dict:
    """Identity record + optional latest snapshot content for convenience."""
    out = {
        "id": a["id"],
        "module": a["module_label"],
        "title": a["title"],
        "position": a["position"],
        "createdAt": a["created_at"],
        "snapshot": None,
    }
    if snapshot:
        content = json.loads(snapshot["content"]) if isinstance(snapshot["content"], str) else snapshot["content"]
        out["snapshot"] = {
            "id": snapshot["id"],
            "label": snapshot["label"],
            "snapshotAt": snapshot["snapshot_at"],
            **content,
        }
    return out



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


# ── Module endpoints ──────────────────────────────────────────────────────────

@app.get("/api/modules")
@jwt_required()
def list_modules():
    conn = get_db()
    user_id = int(get_jwt_identity())
    course_id = request.args.get("course_id", type=int)
    if not course_id:
        return jsonify({"error": "course_id required"}), 400
    if not q.get_course(conn, course_id, user_id):
        return jsonify({"error": "not found"}), 404

    modules = q.list_modules(conn, course_id)
    return jsonify({"modules": [_module_dict(m) for m in modules]})


def _module_dict(m) -> dict:
    outcome_ids = json.loads(m["outcome_ids"]) if isinstance(m["outcome_ids"], str) else m["outcome_ids"]
    return {
        "id": m["id"],
        "courseId": m["course_id"],
        "title": m["title"],
        "description": m["description"],
        "position": m["position"],
        "outcomeIds": outcome_ids,
        "canvasModuleId": m["canvas_module_id"],
    }


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
    result = []
    for a in assignments:
        snap = q.latest_snapshot(conn, a["id"])
        result.append(_assignment_dict(a, snap))
    return jsonify({"assignments": result})


@app.post("/api/assignments")
@jwt_required()
def create_assignment():
    """Create an assignment identity record. The live document starts empty in the log."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    body = request.get_json(force=True)

    course_id = body.get("course_id")
    if not course_id:
        return jsonify({"error": "course_id required"}), 400

    course = q.get_course(conn, int(course_id), user_id)
    if not course:
        return jsonify({"error": "not found"}), 404

    module_label = body.get("module_label", "")
    position = q.next_position_in_module(conn, course["id"], user_id, module_label)
    title = body.get("title") or "Untitled"

    a = q.create_assignment(conn, user_id, course["id"], module_label, title, position)
    q.append_log(conn, user_id, "assignment", a["id"], "created", title)

    # If the frontend sent content, capture it as the first draft snapshot.
    description = body.get("description", "")
    aligned_outcome_ids = body.get("aligned_outcome_ids") or []
    snap = None
    if description or aligned_outcome_ids:
        content = {
            "format_version": "1",
            "title": title,
            "description": description,
            "aligned_outcome_ids": aligned_outcome_ids,
        }
        snap = q.create_snapshot(conn, a["id"], user_id, content, label="draft")

    return jsonify(_assignment_dict(a, snap)), 201


@app.patch("/api/assignments/<string:assignment_id>")
@jwt_required()
def patch_assignment(assignment_id: str):
    """Update position or title of an assignment identity record."""
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

    a = q.update_assignment(conn, assignment_id, user_id, **updates)
    snap = q.latest_snapshot(conn, assignment_id)
    return jsonify(_assignment_dict(a, snap))


@app.post("/api/assignments/<string:assignment_id>/snapshots")
@jwt_required()
def create_snapshot(assignment_id: str):
    """Save a snapshot — manual save point or Canvas push record."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    a = q.get_assignment(conn, assignment_id, user_id)
    if not a:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    content = body.get("content")
    if not content:
        return jsonify({"error": "content required"}), 400

    content.setdefault("format_version", "1")
    label = body.get("label")  # 'canvas_push' | 'manual' | None

    snap = q.create_snapshot(conn, assignment_id, user_id, content, label)
    q.append_log(conn, user_id, "assignment", assignment_id, "save",
                 json.dumps({"snapshot_id": snap["id"], "label": label}))

    return jsonify({"id": snap["id"], "snapshotAt": snap["snapshot_at"]}), 201


# ── Log endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/log/<string:assignment_id>")
@jwt_required()
def get_log(assignment_id: str):
    """Return all log entries for an assignment."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    if not q.get_assignment(conn, assignment_id, user_id):
        return jsonify({"error": "not found"}), 404
    rows = q.list_log(conn, "assignment", assignment_id)
    return jsonify({"entries": [dict(r) for r in rows]})


@app.post("/api/log/<string:assignment_id>")
@jwt_required()
def post_log(assignment_id: str):
    """Append a log entry for an assignment."""
    conn = get_db()
    user_id = int(get_jwt_identity())
    if not q.get_assignment(conn, assignment_id, user_id):
        return jsonify({"error": "not found"}), 404
    body = request.get_json(force=True)
    action_type = body.get("action_type", "comment")
    content = body.get("content", "")
    replied_to = body.get("replied_to") or None
    entry = q.append_log(conn, user_id, "assignment", assignment_id, action_type, content, replied_to)
    return jsonify(dict(entry)), 201


# ── Concierge endpoint ────────────────────────────────────────────────────────

@app.post("/api/concierge/<string:assignment_id>")
@jwt_required()
def concierge(assignment_id: str):
    """Respond to an sme_anchor: read context, produce a margin note.

    Body: { anchor_id, comment_id, ?endpoint, ?api_key, ?model }
    """
    conn = get_db()
    user_id = int(get_jwt_identity())

    assignment = q.get_assignment(conn, assignment_id, user_id)
    if not assignment:
        return jsonify({"error": "not found"}), 404

    body = request.get_json(force=True)
    anchor_id = body.get("anchor_id")
    comment_id = body.get("comment_id")
    if not anchor_id or not comment_id:
        return jsonify({"error": "anchor_id and comment_id required"}), 400

    # Read the anchor to get selection/mode info
    anchor = q.get_log_entry(conn, int(anchor_id))
    if not anchor:
        return jsonify({"error": "anchor not found"}), 404

    anchor_content = {}
    try:
        anchor_content = json.loads(anchor["content"])
    except (json.JSONDecodeError, TypeError):
        pass

    # Gather context
    snapshot = q.latest_snapshot(conn, assignment_id)
    draft_html = ""
    if snapshot:
        snap_content = json.loads(snapshot["content"]) if isinstance(snapshot["content"], str) else snapshot["content"]
        draft_html = snap_content.get("description", "")

    course = q.get_course(conn, assignment["course_id"], user_id)
    course_data = _course_context_for_prompt(conn, course) if course else None

    # Build the user message from what the SME is asking about
    selection_text = anchor_content.get("text", "")
    mode = anchor_content.get("mode", "unstuck")

    if anchor_content.get("from") and anchor_content.get("to"):
        user_msg = f"The SME selected this passage and asked for help:\n\n\"{selection_text}\"\n\nFull draft:\n{draft_html}"
    else:
        user_msg = f"The SME asked for help with the whole draft:\n\n{draft_html}"

    # Build prompt with margin_note card
    from prompts import CONCIERGE_DECK
    system_prompt = build_system_prompt(course_data, deck=CONCIERGE_DECK)

    # AI config — endpoint is swappable
    endpoint = body.get("endpoint") or os.environ.get("CONCIERGE_ENDPOINT", "local")
    api_key = body.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    model = body.get("model") or None

    try:
        response_text = call_ai(
            endpoint=endpoint,
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_msg}],
            api_key=api_key,
            model=model,
        )
    except Exception as e:
        app.logger.error("Concierge AI error (%s): %s", endpoint, e, exc_info=True)
        return jsonify({"error": str(e)}), 500

    # Log the agent's note — threaded to the anchor
    note_content = json.dumps({
        "comment_id": comment_id,
        "text": response_text,
        "source": "agent",
    })
    note = q.append_log(
        conn, user_id, "assignment", assignment_id,
        "agent_note", note_content, replied_to=int(anchor_id),
    )

    return jsonify(dict(note)), 201



if __name__ == "__main__":
    port = int(os.environ.get("BACKEND_PORT", 5050))
    print(f"sme-rhizome-builder backend → http://localhost:{port}")
    app.run(host="localhost", port=port, debug=True)
