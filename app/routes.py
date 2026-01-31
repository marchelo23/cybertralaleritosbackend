from flask import Blueprint, jsonify

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@bp.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Cybertralaleritos API"})
