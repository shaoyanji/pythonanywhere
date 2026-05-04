from flask import Blueprint, jsonify, render_template, request

from app.helpers.response import build_page_title, build_public_patch, wants_json_patch


experiments_bp = Blueprint("experiments_demo", __name__)


def validate_kelly_inputs(probability: float, reward: float, risk: float) -> dict:
    """Validate Kelly criterion inputs and return errors if any."""
    errors = {}
    if not 0 <= probability <= 100:
        errors["probability"] = "Probability must be between 0 and 100"
    if reward < 0:
        errors["reward"] = "Reward must be non-negative"
    if risk < 0:
        errors["risk"] = "Risk must be non-negative"
    return errors


def kelly_fraction(probability: float, reward: float, risk: float) -> float:
    if reward == 0:
        return 0.0
    return probability - ((100 - probability) * (risk / reward))


@experiments_bp.route("/experiments/wasm-kelly-criterion/demo", methods=["GET", "POST"])
def wasm_kelly_demo():
    defaults = {"probability": 60, "reward": 50, "risk": 50}
    values = defaults.copy()
    result = None
    errors = {}

    if request.args:
        try:
            values = {
                "probability": float(request.args.get("probability", defaults["probability"])),
                "reward": float(request.args.get("reward", defaults["reward"])),
                "risk": float(request.args.get("risk", defaults["risk"])),
            }
            errors = validate_kelly_inputs(**values)
            if not errors:
                result = round(
                    kelly_fraction(values["probability"], values["reward"], values["risk"]),
                    2,
                )
        except (ValueError, TypeError):
            errors = {"invalid": "Invalid input values"}

    if wants_json_patch():
        return jsonify(
            build_public_patch(
                content_template="partials/public/wasm_demo_content.html",
                page_title="Kelly Demo",
                values=values,
                result=result,
                errors=errors,
            )
        )

    return render_template("pages/wasm_demo.html", values=values, result=result, errors=errors)


@experiments_bp.get("/experiments/wasm-kelly-criterion/demo/calculate")
def wasm_kelly_calculate():
    defaults = {"probability": 60, "reward": 50, "risk": 50}
    try:
        values = {
            "probability": float(request.args.get("probability", defaults["probability"])),
            "reward": float(request.args.get("reward", defaults["reward"])),
            "risk": float(request.args.get("risk", defaults["risk"])),
        }
        errors = validate_kelly_inputs(**values)
        if errors:
            return jsonify({"error": errors}), 400
        result = round(kelly_fraction(values["probability"], values["reward"], values["risk"]), 2)
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid input values"}), 400

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
