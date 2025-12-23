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


aki = Blueprint("aki", __name__, template_folder="templates")
# akiworks
@aki.route("/", methods=["GET", "POST"])
def index():
    return render_template(
        "aki.html", messages=messages, navigation=
        [
            {"href": "home", "caption": "home"},
            {"href": "aipage", "caption": "ai"},
            {"href": "shell", "caption": "shell"},
            {"href": "blog", "caption": "blog"},
        ],svg=svg, style=style
    )
@aki.route("/home", methods=["GET", "POST"])
def homepage():
    return jsonify({
        "title": {"innerText": "home"},
        "h1": {"style": "color:navy;","innerText": "you have been aki-ed"},
        "p": {"innerText": "this is now my page! a shell page"}
    })

@aki.route("/aipage", methods=["GET", "POST"])
def aipage():
    return jsonify({
        "h1": {"style": "color:navy;","innerText": "you have been aki-ed"},
        "p": {"innerText": "this is now my page!"}
    })
@aki.route("/blog", methods=["GET", "POST"])
def blog():
    return jsonify({
        "h1": {"style": "color:navy;","innerText": "you have been aki-ed"},
        "p": {"innerText": "this is now my page! a blog page specifically!"}
    })
@aki.route("/shell", methods=["GET", "POST"])
def shell():
    return jsonify({
        "h1": {"style": "color:navy;","innerText": "you have been aki-ed"},
        "p": {"innerText": "this is now my page! a shell page"}
    })

