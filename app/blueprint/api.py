from flask import Blueprint, render_template, abort, jsonify, request
from jinja2 import TemplateNotFound
from flask_mysqldb import MySQL

import os
import subprocess
import base64
from dotenv import load_dotenv
from app.ai import aiflow
import app.kc as kc
from app.db import mydb
from app.helpers.pantry_wrapper import get_contents, create_basket
from app.helpers import bind_to_globals

from dotenv import load_dotenv

api = Blueprint('api', __name__)
#mysql = MySQL(app)

#@api.route('/', defaults={'page': 'index'})
#@api.route('/api/<page>')
#def show(page):
#    try:
#        #return render_template(f'pages/{page}.html')
#        return render_template(f'hi.html')
#        #return '<h1>hi</h1>'
#    except TemplateNotFound:
#        abort(404)

@api.route("/messages", methods=["GET"])
def get_messages():
    cur = mydb.cursor()
    cur.execute("SELECT * FROM messages")
    result = cur.fetchall()
    #cur.close()
    #mydb.close()
    return jsonify(result)


@api.route("/messages", methods=["POST"])
def create_message():
    data = request.json
    query = (
        "INSERT INTO messages "
        "(title, content, aicontent, summary) "
        "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)"
    )
    cursor = mydb.cursor()
    cursor.execute(query, data)
    mydb.commit()
    #cursor.close()
    #mydb.close()
    return jsonify({"id": cursor.lastrowid}), 201


@api.route("/messages/<int:id>", methods=["GET"])
def get_message(id):
    query = "SELECT * FROM messages WHERE id = %s"
    cursor = mydb.cursor()
    cursor.execute(query, (id,))
    message = cursor.fetchone()
    #cursor.close()
    #mydb.close()

    if not message:
        return jsonify({"error": "Message not found"}), 404

    return jsonify(message)


@api.route("/messages/<int:id>", methods=["PUT"])
def update_message(id):
    query = (
        "UPDATE messages SET "
        "title = %s, content = %s, aicontent = %s, summary = %s "
        "WHERE id = %s"
    )
    data = request.json

    cursor = mydb.cursor()
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

    mydb.commit()
    #cursor.close()
    #mydb.close()

    return jsonify({"id": id}), 200


@api.route("/messages/<int:id>", methods=["DELETE"])
def delete_message(id):
    query = "DELETE FROM messages WHERE id = %s"
    cursor = mydb.cursor()
    cursor.execute(query, (id,))

    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404

    mydb.commit()
    #cursor.close()
    #mydb.close()

    return "", 204



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


@api.route("/reload", methods=["GET"])
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


def create_message_from_html(data):
    # Pass only the relevant data to create_message
    query = (
        "INSERT INTO messages "
        "(title, content, aicontent, summary) "
        "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)"
    )
    cursor = mydb.cursor()
    cursor.execute(query, data)
    mydb.commit()
   # cursor.close()
   # mydb.close()
@api.route("/llm", methods=["POST"])
def llm():
    data = request.json
    content = data.get("content")
    # Process form data
    # title = request.form['title']
    # content = request.form["content"]
    title = content
    # Validate form data
    
    if not content:
        return ((data)), 201
#        aicontent = aiflow(
#            "(provide an alternative to this approach): ",
#            ["content"],
#        )
    # need to add a bit to amend with an alternative using a SQL find ID and PUT
    else:
        aicontent = aiflow("",content)
        summary = "summary not available"
        query = (
            "INSERT INTO messages "
            "(title, content, aicontent, summary) "
            "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)"
        )
        data = {
            "title": title,
            "content": content,
            "aicontent": aicontent,
            "summary": summary,
        }
        cursor = mydb.cursor()
        cursor.execute(query, data)
        mydb.commit()
    #    cursor.close()
    #    mydb.close()
        return jsonify({"id": cursor.lastrowid}), 201

