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


htmz = Blueprint("htmz", __name__, template_folder="templates")

# htmz works
@htmz.route("/", methods=["GET", "POST"])
def htmzpage():
    return render_template(
        "htmz.html", messages=messages, navigation= [
            {"href": "cat", "caption": "cat"},
            {"href": "dog", "caption": "dog"},
            {"href": "horse", "caption": "horse"},
            {"href": "htmz", "caption": "htmz"},
        ], svg=svg, style=style
    )


@htmz.route("/cat", methods=["GET", "POST"])
def cat():
    return "<div id='content'>this is a cat</div>"

@htmz.route("/dog", methods=["GET", "POST"])
def dog():
    return  "<div id='content'>this is a dog</div>"

@htmz.route("/horse", methods=["GET", "POST"])
def horse():
    return "<div id='content'>this is a god damn horse</div>"
@htmz.route("/htmz", methods=["GET", "POST"])
def htmz2():
    return "<div id='content'>this is htmz within htmz</div>"

