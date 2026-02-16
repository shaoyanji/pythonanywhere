import base64
import json
import os
import subprocess

from flask import Blueprint, jsonify, request

from app.ai import aiflow
from app.db import ensure_schema, get_connection

api = Blueprint("api", __name__)


def _dict_cursor():
    conn = get_connection()
    return conn.cursor(dictionary=True)


def _ensure():
    ensure_schema()


def check_basic_auth():
    hdr = request.headers.get("Authorization")
    if not hdr or not hdr.startswith("Basic "):
        return None
    try:
        user_pass = base64.b64decode(hdr[6:]).decode()
        username, password = user_pass.split(":", 1)
    except Exception:
        return None

    if username == os.getenv("MYSQL_USER") and password == os.getenv("MYSQL_PASSWORD"):
        return username
    return None


def require_basic_auth():
    user = check_basic_auth()
    if user is None:
        return (
            jsonify(error="Authentication required"),
            401,
            {"WWW-Authenticate": 'Basic realm="API"'},
        )
    return None


@api.before_app_request
def setup_schema_once():
    _ensure()


@api.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "pythonanywhere-api"})


# -------- Messages CRUD --------
@api.route("/messages", methods=["GET"])
def get_messages():
    cur = _dict_cursor()
    cur.execute("SELECT * FROM messages ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)


@api.route("/messages", methods=["POST"])
def create_message():
    data = request.json or {}
    query = """
        INSERT INTO messages (title, content, aicontent, summary)
        VALUES (%s, %s, %s, %s)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        query,
        (
            data.get("title"),
            data.get("content"),
            data.get("aicontent"),
            data.get("summary"),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.close()
    return jsonify({"id": new_id}), 201


@api.route("/messages/<int:message_id>", methods=["GET"])
def get_message(message_id):
    cur = _dict_cursor()
    cur.execute("SELECT * FROM messages WHERE id = %s", (message_id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({"error": "Message not found"}), 404
    return jsonify(row)


@api.route("/messages/<int:message_id>", methods=["PUT"])
def update_message(message_id):
    data = request.json or {}
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE messages
        SET title=%s, content=%s, aicontent=%s, summary=%s
        WHERE id=%s
        """,
        (
            data.get("title"),
            data.get("content"),
            data.get("aicontent"),
            data.get("summary"),
            message_id,
        ),
    )
    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "Message not found"}), 404
    conn.commit()
    cur.close()
    return jsonify({"id": message_id})


@api.route("/messages/<int:message_id>", methods=["DELETE"])
def delete_message(message_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE id = %s", (message_id,))
    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "Message not found"}), 404
    conn.commit()
    cur.close()
    return "", 204


# -------- Orchestrator board API (MySQL-backed) --------
@api.route("/orchestrator/tasks", methods=["GET"])
def orchestrator_tasks_list():
    limit = int(request.args.get("limit", 50))
    cur = _dict_cursor()
    cur.execute(
        """
        SELECT task_id, title, owner, status, priority, acceptance, created_at, updated_at
        FROM orchestrator_tasks
        ORDER BY updated_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)


@api.route("/orchestrator/tasks", methods=["POST"])
def orchestrator_task_create_or_upsert():
    auth_err = require_basic_auth()
    if auth_err:
        return auth_err

    data = request.json or {}
    task_id = data.get("task_id")
    title = data.get("title")
    if not task_id or not title:
        return jsonify({"error": "task_id and title are required"}), 400

    owner = data.get("owner")
    status = data.get("status", "queued")
    priority = data.get("priority", "normal")
    acceptance = data.get("acceptance")
    details_json = json.dumps(data.get("details", {}))

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orchestrator_tasks (task_id, title, owner, status, priority, acceptance, details_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          title=VALUES(title),
          owner=VALUES(owner),
          status=VALUES(status),
          priority=VALUES(priority),
          acceptance=VALUES(acceptance),
          details_json=VALUES(details_json)
        """,
        (task_id, title, owner, status, priority, acceptance, details_json),
    )
    conn.commit()
    cur.close()
    return jsonify({"task_id": task_id, "status": status})


@api.route("/orchestrator/tasks/<task_id>", methods=["PATCH"])
def orchestrator_task_patch(task_id):
    auth_err = require_basic_auth()
    if auth_err:
        return auth_err

    data = request.json or {}
    fields = []
    vals = []
    for k in ("owner", "status", "priority", "title", "acceptance"):
        if k in data:
            fields.append(f"{k}=%s")
            vals.append(data[k])

    if "details" in data:
        fields.append("details_json=%s")
        vals.append(json.dumps(data["details"]))

    if not fields:
        return jsonify({"error": "no patch fields provided"}), 400

    vals.append(task_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE orchestrator_tasks SET {', '.join(fields)} WHERE task_id=%s", vals)
    if cur.rowcount == 0:
        cur.close()
        return jsonify({"error": "task not found"}), 404
    conn.commit()
    cur.close()
    return jsonify({"task_id": task_id, "updated": True})


@api.route("/orchestrator/events", methods=["GET"])
def orchestrator_events_list():
    limit = int(request.args.get("limit", 100))
    task_id = request.args.get("task_id")
    actor = request.args.get("actor")
    kind = request.args.get("kind")
    since_id = request.args.get("since_id")

    query = """
        SELECT id, task_id, actor, perspective, kind, status, summary, details_json, refs_json, source, created_at
        FROM orchestrator_events
        WHERE 1=1
    """
    vals = []

    if task_id:
        query += " AND task_id=%s"
        vals.append(task_id)
    if actor:
        query += " AND actor=%s"
        vals.append(actor)
    if kind:
        query += " AND kind=%s"
        vals.append(kind)
    if since_id:
        query += " AND id > %s"
        vals.append(int(since_id))

    query += " ORDER BY id DESC LIMIT %s"
    vals.append(limit)

    cur = _dict_cursor()
    cur.execute(query, tuple(vals))
    rows = cur.fetchall()
    cur.close()
    return jsonify(rows)


@api.route("/orchestrator/events", methods=["POST"])
def orchestrator_event_post():
    auth_err = require_basic_auth()
    if auth_err:
        return auth_err

    data = request.json or {}
    actor = data.get("actor")
    kind = data.get("kind")
    summary = data.get("summary")
    if not actor or not kind or not summary:
        return jsonify({"error": "actor, kind, summary are required"}), 400

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO orchestrator_events
              (task_id, actor, perspective, kind, status, summary, details_json, refs_json, dedupe_key, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                data.get("task_id"),
                actor,
                data.get("perspective", "executor"),
                kind,
                data.get("status"),
                summary,
                json.dumps(data.get("details", {})),
                json.dumps(data.get("refs", [])),
                data.get("dedupe_key"),
                data.get("source", "agent"),
            ),
        )
        conn.commit()
        event_id = cur.lastrowid
    except Exception as exc:
        conn.rollback()
        return jsonify({"error": str(exc)}), 409
    finally:
        cur.close()

    return jsonify({"id": event_id}), 201


@api.route("/llm", methods=["POST"])
def llm():
    data = request.json or {}
    content = data.get("content")
    if not content:
        return jsonify(data), 200

    aicontent = aiflow("", content)
    summary = "summary not available"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO messages (title, content, aicontent, summary)
        VALUES (%s, %s, %s, %s)
        """,
        (content, content, aicontent, summary),
    )
    conn.commit()
    new_id = cur.lastrowid
    cur.close()

    return jsonify({"id": new_id, "aicontent": aicontent}), 201


@api.route("/reload", methods=["GET"])
def protected_reload():
    auth_err = require_basic_auth()
    if auth_err:
        return auth_err

    subprocess.run(["git", "-C", "/home/jisifu/pythonanywhere", "pull"], check=True, text=True, capture_output=True)
    subprocess.run(["doit", "webappreload"], text=True, capture_output=True)
    return jsonify({"ok": True})
