"""
Bearing endpoints — the learning designer's compass.

Stars, not destinations. Course-level or outcome-level.
weight:     -1 to 1 (sail toward / sail away from)
likelihood: 0 to 1 (current read on whether we're there)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import get_db
import queries as q

bearings_bp = Blueprint("bearings", __name__)


# ── Response helpers ───────────────────────────────────────────────────────────

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


# ── Endpoints ──────────────────────────────────────────────────────────────────

@bearings_bp.get("/api/bearings")
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


@bearings_bp.post("/api/bearings")
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


@bearings_bp.patch("/api/bearings/<int:bearing_id>")
@jwt_required()
def update_bearing(bearing_id: int):
    """Update a bearing's weight, likelihood, or text.

    The delta between weight and likelihood is the signal:
    high weight + low likelihood = push harder toward this.
    """
    conn = get_db()
    user_id = int(get_jwt_identity())
    b = q.get_bearing(conn, bearing_id)
    if not b:
        return jsonify({"error": "not found"}), 404

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


@bearings_bp.delete("/api/bearings/<int:bearing_id>")
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


@bearings_bp.post("/api/bearings/<int:bearing_id>/statements")
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


@bearings_bp.patch("/api/statements/<int:statement_id>")
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
