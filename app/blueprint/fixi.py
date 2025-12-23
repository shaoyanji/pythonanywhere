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
from app.init import init
from app.helpers.pantry_wrapper import get_contents, create_basket
from app.helpers import bind_to_globals
from jinja2 import Environment, FileSystemLoader
from jinjaMarkdown.markdownExtension import markdownExtension

pantry_id = os.getenv("PANTRY_ID")
messages, navigation, posts, navigation2 = [], [], [], []
prompt = ""

bind_to_globals(init())


fixi = Blueprint("fixi", __name__, template_folder="templates")


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


# fixi works too
@fixi.route("/", methods=["GET", "POST"])
def fixiindex():
    return render_template(
        "fixi.html", messages=messages, navigation=
        [
            {"href": "home", "caption": "home"},
            {"href": "uc", "caption": "ai"},
            {"href": "uc", "caption": "shell"},
            {"href": "blog", "caption": "blog"},
        ], svg=svg, style=style
    )

# fixi added buttons
@fixi.route("/blog", methods=["GET", "POST"])
def blog():
    results_html = ""
    results_html += f"""
            <details>
                <summary> This can be... </summary>
                <p>a blog entry</p>
                <button fx-action="uc" 
                    fx-method="get"
                    fx-trigger="click"
                    fx-target="#output"
                    fx-swap="outerHTML">
                    Get Content
                </button>
                <output id="output"></output>
            </details>
            """
    return results_html
@fixi.route("/uc", methods=["GET", "POST"])
def uc():
    results_html = ""
    results_html += f"""
            <details>
                <summary> This page is under construction </summary>
                <p>I'm still learning how to enable some features with fixi, especially key-up listen events</p>
                <button fx-action="blog" 
                    fx-method="get"
                    fx-trigger="click"
                    fx-target="#output"
                    fx-swap="outerHTML">
                    Get Content
                </button>
                <output id="output"></output>
            </details>
            """
    return results_html
@fixi.route("/home", methods=["GET", "POST"])
def homepage():
    results_html = ""
    results_html += f"""
            <h1>Welcome to the fixi section of this site</h1>
            <details>
                <summary> This page is under construction </summary>
                <p>I'm still learning how to enable some features with fixi, especially key-up listen events</p>
                <button fx-action="blog" 
                    fx-method="get"
                    fx-trigger="click"
                    fx-target="#output"
                    fx-swap="outerHTML">
                    Get Content
                </button>
                <output id="output"></output>
            </details>
            """
    return results_html

