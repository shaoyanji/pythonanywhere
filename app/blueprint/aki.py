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
            {"href": "home", "caption": "~/"},
            {"href": "about", "caption": "~/about"},
            {"href": "projects", "caption": "~/projects"},
            {"href": "blog", "caption": "~/blog"},
            {"href": "shell", "caption": "~/cmd"},
            {"href": "kc?p=60&reward=50&risk=50", "caption": "~/kctest"},
        ], svg=svg, style=style
    )
@aki.route("/home", methods=["GET", "POST"])
def homepage():
    return jsonify({
        "title": {"innerText": "home"},
        "swap": {"innerText": "does this work?"}
    })

@aki.route("/about", methods=["GET", "POST"])
def about():
    return jsonify({
        "h1": {"innerText": "about"},
        "swap": {"innerText": "this is now my page!"}
    })
# stripped down blog2.html partial that is dynamically rendered
@aki.route("/blog", methods=["GET", "POST"])
def blog():
    dyntemp =render_template("blog2.html",posts=posts)
    return jsonify({
        "h1": {"innerText": "blog"},
        "swap": {"innerHTML": dyntemp},
        "swapcode": {"innerText": dyntemp}
    })
# embedding flask render template into aki
@aki.route("/projects", methods=["GET", "POST"])
def projects():
    return jsonify({
        "h1": {"innerText": "projects"},
        "swap": {"innerHTML": render_template("hi.html")}
    })

@aki.route("/shell", methods=["GET", "POST"])
def shell():
    return jsonify({
        "h1": {"innerText": "projects"},
        "swap": {"innerHTML": render_template("form2.html")}
    })
@aki.route("/kc", methods=["GET", "POST"])
def kcc():
    p = request.args.get('p')
    reward = request.args.get('reward')
    risk = request.args.get('risk')
    if p:
        p=int(p)
        reward=int(reward)
        risk=int(risk)
    #kelly_fraction = p - ((100 - p) * risk / reward)
    kelly_fraction = kc.run(p,reward,risk) 
    return jsonify({
        "h1": {"innerText": "projects"},
        "result": {"innerHTML": f'{kelly_fraction}'}
    })
