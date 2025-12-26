from flask import Blueprint, render_template, abort, request, jsonify
from jinja2 import TemplateNotFound
from flask_minify import Minify
import os
import subprocess
import base64
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from flask_mysqldb import MySQL
import app.ai as ai
import app.kc as kc
from app.db import mydb
from app.init import init
from app.helpers.pantry_wrapper import get_contents, create_basket
from app.helpers import bind_to_globals
from jinja2 import Environment, FileSystemLoader
from jinjaMarkdown.markdownExtension import markdownExtension

pantry_id = os.getenv("PANTRY_ID")
messages, navigation, posts = [], [], []
prompt = ""


bind_to_globals(init())

simple_page = Blueprint("simple_page", __name__, template_folder="templates")

# @simple_page.route('/', defaults={'page': 'index'})
# @simple_page.route('/<page>')
# def show(page):
#    try:
#        return render_template(f'{page}.html')
#        #return render_template(f'hi.html')
#        #return '<h1>hi</h1>'
#    except TemplateNotFound:
#        abort(404)


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



@simple_page.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "index.html", messages=messages, navigation=navigation, svg=svg, style=style
    )


@simple_page.route("/aipage", methods=["GET", "POST"])
def aipage():
    return render_template(
        "create2.html", messages=messages, navigation=navigation, svg=svg, style=style
    )


@simple_page.route("/shell", methods=["GET", "POST"])
def shell():
    return render_template(
        "shell.html", messages=messages, navigation=navigation, svg=svg, style=style
    )


@simple_page.route("/blog", methods=["GET", "POST"])
def blog():
    return render_template(
        "blog.html",
        messages=messages,
        navigation=navigation,
        svg=svg,
        style=style,
        posts=posts,
    )


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
    cursor.close()
    mydb.close()

#   return render_template("create2.html", messages=messages)
@simple_page.route("/shell_submit", methods=["POST"])
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
            "provide only a short sentence for the following: <prompt>"
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


@simple_page.route("/submit_message", methods=["POST"])
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
            "provide only a short sentence for the following: "
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


@simple_page.route("/search", methods=["POST"])
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
            <details>
                <summary> {message["title"]}  {message["summary"]}</summary>
                {message["aicontent"]}
            </details>
         """
    return results_html
