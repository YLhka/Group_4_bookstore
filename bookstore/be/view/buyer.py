from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.buyer import Buyer
from be.model.order import Order
from be.model.user import User
from be.model.cart import Cart
from be.model.coupon import CouponManager

bp_buyer = Blueprint("buyer", __name__, url_prefix="/buyer")

def check_token(user_id: str, token: str):
    um = User()
    code, _ = um.check_token(user_id, token)
    return code == 200

@bp_buyer.route("/add_funds", methods=["POST"])
def add_funds():
    body = request.get_json()
    user_id = body.get("user_id")
    password = body.get("password")
    add_value = int(body.get("add_value", 0))

    bm = Buyer()
    ok, msg = bm.add_funds(user_id, password, add_value)
    if not ok:
        if msg == "authorization fail":
            return jsonify({"message": msg}), 401
        return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/new_order", methods=["POST"])
def new_order():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    store_id = body.get("store_id")
    books = body.get("books", [])
    coupon_id = body.get("coupon_id") # Optional

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    bm = Buyer()
    ok, msg, order_id = bm.new_order(user_id, store_id, books, coupon_id)
    if not ok:
        return jsonify({"message": msg}), 500
    return jsonify({"order_id": order_id}), 200


@bp_buyer.route("/payment", methods=["POST"])
def payment():
    body = request.get_json()
    user_id = body.get("user_id")
    order_id = body.get("order_id")
    password = body.get("password")

    bm = Buyer()
    ok, msg = bm.payment(user_id, order_id, password)
    if not ok:
        if msg == "authorization fail":
            return jsonify({"message": msg}), 401
        return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200


@bp_buyer.route("/receive_order", methods=["POST"])
def receive_order():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    order_id = body.get("order_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    om = Order()
    ok, msg = om.receive_order(user_id, order_id)
    if not ok:
        return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/list_orders", methods=["GET"])
def list_orders():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id", "")
    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    limit = int(request.args.get("limit", 20))
    skip = int(request.args.get("skip", 0))

    om = Order()
    orders = om.list_orders(user_id, limit=limit, skip=skip)
    return jsonify({"message": "ok", "orders": orders}), 200

@bp_buyer.route("/cancel_order", methods=["POST"])
def cancel_order():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    order_id = body.get("order_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    om = Order()
    ok, msg = om.cancel_order(user_id, order_id)
    if not ok:
        return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200

# === Extensions ===
@bp_buyer.route("/add_address", methods=["POST"])
def add_address():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    recipient = body.get("recipient")
    address = body.get("address")
    phone = body.get("phone")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    um = User()
    code, msg = um.add_address(user_id, recipient, address, phone)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/get_addresses", methods=["GET"])
def get_addresses():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401
    
    um = User()
    code, msg, data = um.get_addresses(user_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "addresses": data}), 200

# === Advanced Extensions: Wishlist & Follow ===

@bp_buyer.route("/wishlist", methods=["POST"])
def toggle_wishlist():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    book_id = body.get("book_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    um = User()
    code, msg = um.toggle_wishlist(user_id, book_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": msg}), 200

@bp_buyer.route("/wishlist", methods=["GET"])
def get_wishlist():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")
    
    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    um = User()
    code, msg, data = um.get_wishlist(user_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "wishlist": data}), 200

@bp_buyer.route("/follow", methods=["POST"])
def toggle_follow():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    store_id = body.get("store_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    um = User()
    code, msg = um.toggle_follow(user_id, store_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": msg}), 200

@bp_buyer.route("/follow", methods=["GET"])
def get_following():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")
    
    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    um = User()
    code, msg, data = um.get_following(user_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "following": data}), 200

# === Advanced Extensions: Shopping Cart ===

@bp_buyer.route("/cart", methods=["POST"])
def update_cart():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    store_id = body.get("store_id")
    book_id = body.get("book_id")
    count = int(body.get("count", 1))
    action = body.get("action", "add") # "add" or "update"

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    cart = Cart()
    code, msg = cart.add_item(user_id, store_id, book_id, count, action)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/cart", methods=["DELETE"])
def remove_cart_item():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    store_id = body.get("store_id")
    book_id = body.get("book_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    cart = Cart()
    code, msg = cart.remove_item(user_id, store_id, book_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/cart", methods=["GET"])
def get_cart():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    cart = Cart()
    code, msg, data = cart.get_cart(user_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "cart": data}), 200

@bp_buyer.route("/coupon", methods=["POST"])
def collect_coupon():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    coupon_id = int(body.get("coupon_id"))

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    cm = CouponManager()
    code, msg = cm.collect_coupon(user_id, coupon_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200

@bp_buyer.route("/coupon", methods=["GET"])
def get_coupons():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")
    store_id = request.args.get("store_id") # Optional

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    cm = CouponManager()
    code, msg, data = cm.get_available_coupons(user_id, store_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "coupons": data}), 200
