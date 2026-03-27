from flask import Blueprint, jsonify

from app.services.content import fetch_content_summary


api_bp = Blueprint("api", __name__)


@api_bp.get("/health")
def health():
    return jsonify({"ok": True})


@api_bp.get("/summary")
def summary():
    return jsonify(fetch_content_summary())
