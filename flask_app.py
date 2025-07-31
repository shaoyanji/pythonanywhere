from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from markdown2 import markdown as mdeee
from fuzzywuzzy import fuzz
import subprocess
import requests
import json
#import mysql.connector
#from flask_sqlalchemy import SQLAlchemy
# from datetime import datetime
from flask_mysqldb import MySQL

def shellcmd(message):
    command = f"{message.strip()}".split()
    try:
        result = subprocess.run(command, check=True, text=True, capture_output=True)
        output = result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        output = str(e)
    return output
shellcmd("echo y |age -d -i ~/.ssh/id_ed25519 .env.age >.env")
load_dotenv()
shellcmd("rm .env")
groq_api_key = os.getenv("GROQ_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
cohere_api_key = os.getenv("COHERE_API_KEY")
password = os.getenv('MYSQL_PASSWORD')
user = os.getenv('MYSQL_USER')
app = Flask(__name__)

#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://username:password@localhost/db_name'
#app.config['SQLALCHEMY_DATABASE_URI']= 'mysql+pymysql://'+user+':'+password+'@'+user+'.mysql.pythonanywhere-services.com/'+user+'$default'
#app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['MYSQL_USER'] = os.getenv('MYSQL_USER') 
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] =app.config['MYSQL_USER']+"$default"
app.config['MYSQL_HOST'] = app.config['MYSQL_USER']+".mysql.pythonanywhere-services.com"
mysql = MySQL(app)
    
def get_allmessages():
    cur = mysql.connection.cursor()
    try:
        query = "SELECT * FROM messages"
        cur.execute(query)
        messages = cur.fetchall()
        return jsonify(messages)
    finally:
        cur.close()

@app.route('/api/messages', methods=['GET'])
def get_messages():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM messages")
    result = cur.fetchall()
    return jsonify(result)

@app.route('/api/messages', methods=['POST'])
def create_message():
    
    data = request.json
    query = ("INSERT INTO messages "
             "(title, content, aicontent, summary) "
             "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)")
    cursor = mysql.connection.cursor()
    cursor.execute(query, data)
    mysql.connection.commit()
    
    return jsonify({'id': cursor.lastrowid}), 201

@app.route('/api/messages/<int:id>', methods=['GET'])
def get_message(id):
    
    query = "SELECT * FROM messages WHERE id = %s"
    cursor = mysql.connection.cursor()
    cursor.execute(query, (id,))
    message = cursor.fetchone()
    
    if not message:
        return jsonify({"error": "Message not found"}), 404
    
    return jsonify(message)

@app.route('/api/messages/<int:id>', methods=['PUT'])
def update_message(id):
    
    query = ("UPDATE messages SET "
             "title = %s, content = %s, aicontent = %s, summary = %s "
             "WHERE id = %s")
    data = request.json
    
    cursor = mysql.connection.cursor()
    cursor.execute(query, (
        data.get('title') or None,
        data.get('content') or None,
        data.get('aicontent') or None,
        data.get('summary') or None,
        id
    ))
    
    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404
    
    mysql.connection.commit()
    
    return jsonify({'id': id}), 200

@app.route('/api/messages/<int:id>', methods=['DELETE'])
def delete_message(id):
    
    query = "DELETE FROM messages WHERE id = %s"
    cursor = mysql.connection.cursor()
    cursor.execute(query, (id,))
    
    if cursor.rowcount == 0:
        return jsonify({"error": "Message not found"}), 404
    
    mysql.connection.commit()
    
    return '', 204

prompt = "You are a helpful assistant and your output is only in markdown and html"
messages=[{}]
def ai(prompt, message):
    return gemini_handler(prompt + message)




def groq_handler(message):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "messages": [{"role": "user", "content": message}],
        "model": "llama3-70B-8192",
    }
    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        return mdeee(
            response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return cohere_handler(message)


def cohere_handler(message):
    url = "https://api.cohere.com/v2/chat"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {cohere_api_key}",
        "Content-Type": "application/json",
    }
    data = {
        # "temperature": 0.3,
        "model": "command-a-03-2025",
        "messages": [{"role": "user", "content": message}],
    }
    response = requests.post(url=url, headers=headers, json=data)
    if response.status_code == 200:
        response_data = response.json()
        return mdeee(
            response_data.get("message", {}).get("content", {})[0].get("text", "")
        )
    else:
        print(f"Error: {response.status_code} - {response.text}")
        # return gemini_handler(message)


def gemini_handler(message):
    data_payload = {"contents": [{"parts": [{"text": message}]}]}
    data_json = json.dumps(data_payload)
    # bypassing some gemini refusal issues
    command = [
        "curl",
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "-H",
        f"x-goog-api-key: {gemini_api_key}",
        "-H",
        "Content-Type: application/json",
        "-X",
        "POST",
        "-d",
        data_json,
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    if result.returncode == 0:
        try:
            response_data = json.loads(result.stdout)
            return mdeee(
                response_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
        except json.JSONDecodeError:
            return "json decoder return failed on the response"
    else:
        return groq_handler(message)


def gptimage_handler(message):
    # command = [
    #     "tgpt",
    #     "--provider",
    #     "gemini",
    #     # "groq",
    #     "--key",
    #     gemini_api_key,
    #     # groq_api_key,
    #     # "--model",
    #     # "llama3-70b-8192",
    #     "-w",
    #     "-q",
    #     message,
    # ]
    command = ["tgpt", "--img", "-q", message]
    result = subprocess.run(command, check=True, text=True, capture_output=True)
    return mdeee(result.stdout)



# @app.route("/", methods=["GET", "POST"])
# def hello_world():
#     if request.method == "GET":
#         command = ["ls"]
#         result = subprocess.run(command, check=True, text=True, capture_output=True)
#         return mdeee(result.stdout)

#     elif request.method == "POST":
#         data = request.get_json()  # Get JSON data from the request body
#         if data:
#             # Extract 'name' from JSON, default to 'Unknown'
#             name = data.get("name", "Unknown")
#             # 200 OK status code

#             return jsonify(
#                 {"message": f"Hello, {name}! This is a POST request with data."}
#             ), 200
#         else:
#             # 400 Bad Request
#             return (
#                 "Hello, World! This is a POST request, but no data was provided.",
#                 400,
#             )
#     else:
#         return "Method not allowed.", 405  # 405 Method Not Allowed


# @app.route("/echo", methods=["POST"])
# def echo():
#     data = request.get_json()
#     if data:
#         return jsonify(data), 200  # Just return the same data you received
#     else:
#         return "No data provided to echo.", 400


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


# @app.route("/create2/", methods=["GET", "POST"])
# def create2():
#     if request.method == "POST":
#         title = request.form["title"]
#         content = request.form["content"]
#         aicontent = ai("", content)
#         summary = "this is a summary placeholder"
#         if not title:
#             flash("Title is required!")
#         elif not content:
#             flash("Content is required!")
#         else:
#             messages.append(
#                 {
#                     "title": title,
#                     "content": content,
#                     "aicontent": aicontent,
#                     "summary": summary,
#                 }
#             )
#             # Redirect to the same page after successful submission
#             return redirect(url_for("create2"))

def create_message_from_html(data):
    # Pass only the relevant data to create_message
        query = ("INSERT INTO messages "
             "(title, content, aicontent, summary) "
             "VALUES (%(title)s, %(content)s, %(aicontent)s, %(summary)s)")
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
        aicontent = ai(
            "(provide an alternative to this approach): ",
            messages[int(title) - 1]["content"],
        )
# need to add a bit to amend with an alternative using a SQL find ID and PUT
    else:
        # Add message to the list
        aicontent = shellcmd(content)
        summary = ai(
            "",
            "provide only a short title for the following interaction with u123 and i123, do not write anything else: u123 says"
            + content
            + "i123 responds "
            + aicontent,
        )
        data = {
            'title': title,
            'content': request.form['content'],
            'aicontent': aicontent,
            'summary': summary
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
        aicontent = ai(
            "(provide an alternative to this approach): ",
            messages[int(title) - 1]["content"],
        )

    else:
        # Add message to the list
        aicontent = ai(prompt, content)
        summary = ai(
            "",
            "provide only a short title for the following interaction with u123 and i123, do not write anything else: u123 says"
            + content
            + "i123 responds "
            + aicontent,
        )
        data = {
                "title": title,
                "content": content,
                "aicontent": aicontent,
                "summary": summary,
            }
        messages.append(
           data 
        )
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
                <!-- Add edit and favorite buttons here -->
                <div class="message-buttons">
                    <button class="edit-button">Edit</button>
                    <button class="favorite-button">★</button>
                </div>
                <div class="message-header">
                    <h3> {message["title"]}  {message["summary"]}</h3>
                </div>
                {message["aicontent"]}
            </div>
         """
    return results_html


# Local Development
#if __name__ == "__main__":
#    app.run(host="127.0.0.1", port=6969)
