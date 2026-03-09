"""
Canvas API proxy endpoints.

All routes prefixed /api/canvas/.
Translates between our data model and the Canvas REST API.
Response data is typed with alkahest Fluid types.
"""

import json
from dataclasses import asdict

import requests
from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from db import get_db
import queries as q
from canvas_types import CanvasCourse, CanvasAssignment, CanvasPushResult

canvas_bp = Blueprint("canvas", __name__)


def _canvas_creds(user) -> tuple[str, str]:
    return user["canvas_access_token"] or "", user["canvas_base_url"].rstrip("/")


@canvas_bp.post("/api/canvas/assignment")
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
    result = CanvasPushResult(
        assignment_id=str(data.get("id", "")),
        html_url=data.get("html_url", ""),
        course_id=str(canvas_course_id),
    )

    # Record the push as a canvas_push snapshot
    assignment_id = body.get("assignment_id")
    if assignment_id:
        a = q.get_assignment(conn, str(assignment_id), user["id"])
        if a:
            snap_content = {
                "format_version": "1",
                **draft,
                "canvas": asdict(result),
            }
            q.create_snapshot(conn, str(assignment_id), user["id"], snap_content, label="canvas_push")
            q.append_log(conn, user["id"], "assignment", str(assignment_id), "canvas_push",
                         json.dumps({"canvas_id": result.assignment_id, "html_url": result.html_url}))

    return jsonify(asdict(result))


@canvas_bp.get("/api/canvas/assignments")
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

    assignments = [
        CanvasAssignment(
            id=a.get("id"),
            name=a.get("name"),
            points_possible=a.get("points_possible"),
            html_url=a.get("html_url", ""),
            has_rubric=bool(a.get("rubric")),
        )
        for a in resp.json()
        if isinstance(a, dict)
    ]
    return jsonify({"assignments": [asdict(a) for a in assignments]})


@canvas_bp.get("/api/canvas/courses")
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

    courses = [
        CanvasCourse(
            id=c.get("id"),
            name=c.get("name"),
            course_code=c.get("course_code", ""),
        )
        for c in resp.json()
        if isinstance(c, dict)
    ]
    return jsonify({"courses": [asdict(c) for c in courses]})
