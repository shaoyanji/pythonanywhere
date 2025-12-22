from flask import Blueprint, render_template, abort, jsonify, request
from jinja2 import TemplateNotFound
import app.kc as kc

wasm = Blueprint('wasm', __name__)


@wasm.route('/', defaults={'page': 'index'})
@wasm.route('/wasm/<page>')
def show(page):
    try:
        #return render_template(f'pages/{page}.html')
        return render_template(f'hi.html')
        #return '<h1>hi</h1>'
    except TemplateNotFound:
        abort(404)

@wasm.route("/run_wasm", methods=["POST"])
def run_wasm():
    data = request.json
    probability = data.get("prob")
    reward = data.get("reward")
    risk = data.get("risk")
    return jsonify({"result": kc.run(probability, reward, risk)}), 200

@wasm.route("/kc", methods=["GET", "POST"])
def kccccc():
    p = request.args.get('p')
    reward = request.args.get('reward')
    risk = request.args.get('risk')
    if p:
        p=int(p)
        reward=int(reward)
        risk=int(risk)
    #kelly_fraction = p - ((100 - p) * risk / reward)
    kelly_fraction = kc.run(p,reward,risk) 
    return f'{kelly_fraction}' 
@wasm.route("/test")
def test():
    return "hi"
