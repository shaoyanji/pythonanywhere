from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import subprocess
from flask_mysqldb import MySQL
import app.ai as ai

# import mysql.connector
# from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime
import base64

load_dotenv()

app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI']= 'mysql+pymysql://'+user+':'+password+'@'+user+'.mysql.pythonanywhere-services.com/'+user+'$default'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["MYSQL_USER"] = os.getenv("MYSQL_USER")
app.config["MYSQL_PASSWORD"] = os.getenv("MYSQL_PASSWORD")
app.config["MYSQL_DB"] = app.config["MYSQL_USER"] + "$default"
app.config["MYSQL_HOST"] = (
    app.config["MYSQL_USER"] + ".mysql.pythonanywhere-services.com"
)
mysql = MySQL(app)


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
    if username == "jisifu" and password == os.getenv("MYSQL_PASSWORD"):
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


prompt = (
    "You are a helpful assistant and your output is only in markdown unsafe allowed"
)
messages = [
    {
        "title": "title",
        "content": "content",
        "aicontent": "aicontent",
        "summary": "summary",
    }
]


def shellcmd(message):
    command = f"{message.strip()}".split()
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        output = result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        output = str(e)
    return output


def aiflow(prompt, message):
    return ai.aiflow(prompt, message)


@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html", messages=messages)


@app.route("/aipage", methods=["GET", "POST"])
def aipage():
    return render_template("create2.html", messages=messages)


@app.route("/shell", methods=["GET", "POST"])
def shell():
    return render_template("shell.html", messages=messages)


@app.route("/blog", methods=["GET", "POST"])
def blog():
    return render_template("index.html", messages=messages)


def create_message_from_html(data):
    # Pass only the relevant data to create_message
    query = (
        "INSERT INTO messages "
        "(title, content, aicontent, summary) "
        "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)"
    )
    cursor = mysql.connection.cursor()
    cursor.execute(query, data)
    mysql.connection.commit()


#     return render_template("create2.html", messages=messages)
@app.route("/shell_submit", methods=["POST"])
def shell_submit():
    # Process form data
    # title = request.form['title']
    content = request.form["content"]
    title = content
    # Validate form data
    if not content:
        aicontent = aiflow(
            "(provide an alternative to this approach): ",
            messages[int(title) - 1]["content"],
        )
    # need to add a bit to amend with an alternative using a SQL find ID and PUT
    else:
        # Add message to the list
        aicontent = shellcmd(content)
        summary = aiflow(
            "",
            "provide only a short title for the following: <prompt>"
            + content
            + "</prompt> response:"
            + aicontent,
        )
        data = {
            "title": title,
            "content": request.form["content"],
            "aicontent": aicontent,
            "summary": summary,
        }
        messages.append(data)
        create_message_from_html(data)

    # Render the updated message container HTML
    return render_template("message_card.html", message=messages[-1])


@app.route("/submit_message", methods=["POST"])
def submit_message():
    # Process form data
    # title = request.form['title']
    content = request.form["content"]
    title = str(len(messages))
    # Validate form data
    if not content:
        aicontent = aiflow(
            "(provide an alternative to this approach): ",
            messages[int(title) - 1]["content"],
        )

    else:
        # Add message to the list
        aicontent = aiflow(prompt, content)
        summary = aiflow(
            "",
            "provide only a short title for the following: "
            + content
            + "response: "
            + aicontent,
        )
        data = {
            "title": title,
            "content": content,
            "aicontent": aicontent,
            "summary": summary,
        }
        messages.append(data)
        create_message_from_html(data)

    # Render the updated message container HTML
    return render_template("message_card.html", message=messages[-1])


@app.route("/search", methods=["POST"])
def search():
    search_term = request.form["search"]
    results_html = ""
    for message in reversed(messages):  # Iterate in reverse order
        if (
            fuzz.partial_ratio(search_term.lower(), message["title"].lower()) >= 90
            or fuzz.partial_ratio(search_term.lower(), message["content"].lower()) >= 90
            or fuzz.partial_ratio(search_term.lower(), message["summary"].lower()) >= 90
            or fuzz.partial_ratio(search_term.lower(), message["aicontent"].lower())
            >= 50
        ):
            results_html += f"""
             <div class="max-w-sm bg-white border rounded-lg shadow-sm p-7 border-neutral-200/60" >
                <div class="message-header">
                    <h3> {message["title"]}  {message["summary"]}</h3>
                </div>
                {message["aicontent"]}
            </div>
         """
    return results_html


# Local Development
# if __name__ == "__main__":
#     app.run(host="127.0.0.1", port=6969)
