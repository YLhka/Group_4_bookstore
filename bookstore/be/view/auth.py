from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.user import User

bp_auth = Blueprint("auth", __name__, url_prefix="/auth")


@bp_auth.route("/login", methods=["POST"])
def login():
    body = request.get_json()
    user_id = body.get("user_id")
    password = body.get("password")
    terminal = body.get("terminal", "terminal")

    um = User()
    code, msg, token = um.login(user_id, password, terminal)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "token": token}), 200


@bp_auth.route("/logout", methods=["POST"])
def logout():
    body = request.get_json()
    user_id = body.get("user_id")
    token = request.headers.get("token", "")

    um = User()
    code, msg = um.logout(user_id, token)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200


@bp_auth.route("/register", methods=["POST"])
def register():
    body = request.get_json()
    user_id = body.get("user_id")
    password = body.get("password")

    um = User()
    code, msg = um.register(user_id, password)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200


@bp_auth.route("/unregister", methods=["POST"])
def unregister():
    body = request.get_json()
    user_id = body.get("user_id")
    password = body.get("password")
    # token = body.get("token") 

    um = User()
    # The new logic relies on password verification, which is safer and standard for deletion
    code, msg = um.unregister(user_id, password)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200


@bp_auth.route("/password", methods=["POST", "PUT"])
def change_password():
    body = request.get_json()
    user_id = body.get("user_id")
    # Accept both camelCase and snake_case for backward compatibility
    old_password = body.get("oldPassword") if "oldPassword" in body else body.get("old_password")
    new_password = body.get("newPassword") if "newPassword" in body else body.get("new_password")
    # token = body.get("token")

    um = User()
    code, msg = um.change_password(user_id, old_password, new_password)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200
