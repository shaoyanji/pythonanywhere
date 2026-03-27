from flask import Blueprint, render_template, request


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

    if request.method == "POST":
        values = {
            "probability": float(request.form.get("probability", defaults["probability"])),
            "reward": float(request.form.get("reward", defaults["reward"])),
            "risk": float(request.form.get("risk", defaults["risk"])),
        }
        result = round(
            kelly_fraction(values["probability"], values["reward"], values["risk"]),
            2,
        )

    return render_template("pages/wasm_demo.html", values=values, result=result)

