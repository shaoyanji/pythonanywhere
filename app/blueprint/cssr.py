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

messages, navigation, posts = [], [], []
prompt = ""

bind_to_globals(init())

cssr = Blueprint("cssr", __name__, template_folder="templates")
@cssr.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "cssr.html", messages=messages, navigation=
        [
            {"href": "home", "caption": "~"},
            {"href": "about", "caption": "~/about"},
            {"href": "projects", "caption": "~/projects"},
            {"href": "blog", "caption": "~/blog"},
        ], svg=svg, style=style
    )

