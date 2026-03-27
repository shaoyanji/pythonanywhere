from flask import Blueprint, jsonify, render_template, request

from app.blueprints.public import build_page_title, build_public_patch, wants_json_patch


experiments_bp = Blueprint("experiments_demo", __name__)


def kelly_fraction(probability: float, reward: float, risk: float) -> float:
    if reward == 0:
        return 0.0
    return probability - ((100 - probability) * (risk / reward))


@experiments_bp.route("/experiments/wasm-kelly-criterion/demo", methods=["GET", "POST"])
def wasm_kelly_demo():
    defaults = {"probability": 60, "reward": 50, "risk": 50}
    values = defaults.copy()
    result = None

    if request.args:
        values = {
            "probability": float(request.args.get("probability", defaults["probability"])),
            "reward": float(request.args.get("reward", defaults["reward"])),
            "risk": float(request.args.get("risk", defaults["risk"])),
        }
        result = round(
            kelly_fraction(values["probability"], values["reward"], values["risk"]),
            2,
        )

    if wants_json_patch():
        return jsonify(
            build_public_patch(
                content_template="partials/public/wasm_demo_content.html",
                page_title="Kelly Demo",
                values=values,
                result=result,
            )
        )

    return render_template("pages/wasm_demo.html", values=values, result=result)


@experiments_bp.get("/experiments/wasm-kelly-criterion/demo/calculate")
def wasm_kelly_calculate():
    defaults = {"probability": 60, "reward": 50, "risk": 50}
    values = {
        "probability": float(request.args.get("probability", defaults["probability"])),
        "reward": float(request.args.get("reward", defaults["reward"])),
        "risk": float(request.args.get("risk", defaults["risk"])),
    }
    result = round(kelly_fraction(values["probability"], values["reward"], values["risk"]), 2)
    return jsonify(
        {
            "#demo-result": {
                "innerHTML": render_template(
                    "partials/public/demo_result.html",
                    values=values,
                    result=result,
                )
            },
            "title": {"textContent": build_page_title("Kelly Demo")},
        }
    )
