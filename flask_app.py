from flask import Flask, render_template, request, flash, redirect, url_for, jsonify 
import os
from dotenv import load_dotenv
from markdown2 import markdown as mdeee
from fuzzywuzzy import fuzz
import subprocess

load_dotenv()
api_key = os.getenv('GROQ_API_KEY')
app = Flask(__name__)

prompt = "You are a helpful assistant"


def ai(prompt, message):
    command = [
        'tgpt',
        '--provider',
        'groq',
        '--key',
        api_key,
        '--model',
        'llama3-70b-8192',
        '-w',
        '-q',
        message
    ]
    # command = ['tgpt', '--img', '-q', message]
    result = subprocess.run(command, check=True,
                            text=True, capture_output=True)
    return mdeee(result.stdout)


messages = [
    {
        "title": "Message One",
        "content": "Message One Content",
        "aicontent": "AI Generated Content",
        "summary": "AI Generated Summary",
    },
    {
        "title": "Message Two",
        "content": "Message Two Content",
        "aicontent": "Message Three Content",
        "summary": "AI Generated Summary",
    },
]


@app.route("/", methods=['GET', 'POST'])
def hello_world():
    if request.method == 'GET':
                command = ["ls"]
                result = subprocess.run(command, check=True,
                                        text=True, capture_output=True)
                return mdeee(result.stdout)

    elif request.method == 'POST':
        data = request.get_json()  # Get JSON data from the request body
        if data:
            # Extract 'name' from JSON, default to 'Unknown'
            name = data.get('name', 'Unknown')
            # 200 OK status code

            return jsonify({'message': f'Hello, {name}! This is a POST request with data.'}), 200
        else:
            # 400 Bad Request
            return "Hello, World! This is a POST request, but no data was provided.", 400
    else:
        return "Method not allowed.", 405  # 405 Method Not Allowed


@app.route("/echo", methods=['POST'])
def echo():
    data = request.get_json()
    if data:
        return jsonify(data), 200  # Just return the same data you received
    else:
        return "No data provided to echo.", 400
# @app.route("/")
# def index():
    #    return render_template("create2.html", messages=messages)


@app.route("/create2/", methods=["GET", "POST"])
def create2():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        aicontent = ai("", content)
        summary = "this is a summary placeholder"
        if not title:
            flash("Title is required!")
        elif not content:
            flash("Content is required!")
        else:
            messages.append(
                {
                    "title": title,
                    "content": content,
                    "aicontent": aicontent,
                    "summary": summary,
                }
            )
            # Redirect to the same page after successful submission
            return redirect(url_for("create2"))

    return render_template("create2.html", messages=messages)


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
        messages.append(
            {
                "title": title,
                "content": content,
                "aicontent": aicontent,
                "summary": summary,
            }
        )

    # Render the updated message container HTML
    return render_template("message_card.html", message=messages[-1])


@app.route("/search", methods=["POST"])
def search():
    search_term = request.form["search"]
    results_html = ""
    for message in reversed(messages):  # Iterate in reverse order
        if (
            fuzz.partial_ratio(search_term.lower(),
                               message["title"].lower()) >= 90
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
                    <h3> {message['title']}  {message['summary']}</h3>
                </div>
                {message['aicontent']}
            </div>
            """
    return results_html


@app.route("/page")
def page():
    return render_template("page.html", messages=messages)


# if __name__ == '__main__':
#  app.run(host='0.0.0.0', port=8080)
