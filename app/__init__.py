from flask import Flask, render_template, request, jsonify
from flask_minify import Minify
import os
import subprocess
import base64
from dotenv import load_dotenv
from flask_mysqldb import MySQL

from jinja2 import Environment, FileSystemLoader
from jinjaMarkdown.markdownExtension import markdownExtension
from app.blueprint.simple_page import simple_page
from app.blueprint.fixi import fixi
from app.blueprint.aki import aki
from app.blueprint.cssr import cssr
from app.blueprint.htmz import htmz
from app.blueprint.wasm import wasm
from app.blueprint.api import api

# from fuzzywuzzy import fuzz
# import app.ai as ai
# import app.kc as kc
# from app.helpers.pantry_wrapper import get_contents, create_basket
# from app.helpers import bind_to_globals
env = Environment(loader=FileSystemLoader("templates"))
load_dotenv()

app = Flask(__name__)
app.register_blueprint(aki)
# app.register_blueprint(aki, url_prefix="/aki")
app.register_blueprint(cssr, url_prefix="/cssr")
app.register_blueprint(simple_page, url_prefix="/htmx")
app.register_blueprint(fixi, url_prefix="/fixi")
app.register_blueprint(htmz, url_prefix="/htmz")
app.register_blueprint(wasm, url_prefix="/wasm")
app.register_blueprint(api, url_prefix="/api/v1")

Minify(app=app, html=True, js=True, cssless=True)

app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = app.config["MYSQL_USER"] + "$default"
app.config["MYSQL_HOST"] = (
    app.config["MYSQL_USER"] + ".mysql.pythonanywhere-services.com"
)
mysql = MySQL(app)

app.jinja_env.add_extension(markdownExtension)

def dbexport():
    return mysql

def check_basic_auth():
    """Return the username or None if the header is missing/invalid."""
    hdr = request.headers.get("Authorization")  # 'Basic dXNlcjpwYXNz'
    if not hdr or not hdr.startswith("Basic "):
        return None
    try:
        user_pass = base64.b64decode(hdr[6:]).decode()  # 'user:pass'
        username, password = user_pass.split(":", 1)  # split on first  ':'
    except Exception:
        return None
    # ---- here you validate the pair ----
    if username == os.getenv("MYSQL_USER") and password == os.getenv("MYSQL_PASSWORD"):
        return username
    return None


@app.route("/reload", methods=["GET"])
def protected():
    user = check_basic_auth()
    if user is None:
        # 401 + WWW-Authenticate tells curl to retry with -u
        return (
            jsonify(error="Authentication required"),
            401,
            {"WWW-Authenticate": 'Basic realm="API"'},
        )
    command = [
        "git",
        "-C",
        "/home/jisifu/pythonanywhere",
        "pull",
    ]
    subprocess.run(command, check=True, text=True, capture_output=True)
    # if result.returncode == 0:
    subprocess.run(["doit", "webappreload"], text=True, capture_output=True)
    # return jsonify(message="successful")
    # else:
    # return jsonify(message=f"Hello {user}")


@app.route("/api/messages", methods=["GET"])
def get_messages():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM messages")
    result = cur.fetchall()
    return jsonify(result)


@app.route("/api/messages", methods=["POST"])
def create_message():
    data = request.json
    query = (
        "INSERT INTO messages "
        "(title, content, aicontent, summary) "
        "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)"
    )
    cursor = mysql.connection.cursor()
    cursor.execute(query, data)
    mysql.connection.commit()
    return jsonify({"id": cursor.lastrowid}), 201


@app.route("/api/messages/<int:id>", methods=["GET"])
def get_message(id):
    query = "SELECT * FROM messages WHERE id = %s"
    cursor = mysql.connection.cursor()
    cursor.execute(query, (id,))
    message = cursor.fetchone()
    if not message:
        return jsonify({"error": "Message not found"}), 404

    return jsonify(message)


@app.route("/api/messages/<int:id>", methods=["PUT"])
def update_message(id):
    query = (
        "UPDATE messages SET "
        "title = %s, content = %s, aicontent = %s, summary = %s "
        "WHERE id = %s"
    )
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute(
        query,
        (
            data.get("title") or None,
            data.get("content") or None,
            data.get("aicontent") or None,
            data.get("summary") or None,
            id,
        ),
    )
    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404
    mysql.connection.commit()
    return jsonify({"id": id}), 200


@app.route("/api/messages/<int:id>", methods=["DELETE"])
def delete_message(id):
    query = "DELETE FROM messages WHERE id = %s"
    cursor = mysql.connection.cursor()
    cursor.execute(query, (id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404

    mysql.connection.commit()

    return "", 204
