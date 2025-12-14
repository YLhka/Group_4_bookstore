from flask import Blueprint
from flask import request
from flask import jsonify
from be.model.seller import Seller
from be.model.order import Order
from be.model.user import User
from be.model.coupon import CouponManager
import json
from datetime import datetime

bp_seller = Blueprint("seller", __name__, url_prefix="/seller")

def check_token(user_id: str, token: str):
    um = User()
    code, _ = um.check_token(user_id, token)
    return code == 200

@bp_seller.route("/create_store", methods=["POST"])
def create_store():
    body = request.get_json()
    token = request.headers.get("token", "")

    user_id = body.get("user_id")
    store_id = body.get("store_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    sm = Seller()
    # Corrected argument order: user_id, store_id
    code, msg = sm.create_store(user_id, store_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200


@bp_seller.route("/add_book", methods=["POST"])
def add_book():
    body = request.get_json()
    token = request.headers.get("token", "")

    user_id = body.get("user_id")
    store_id = body.get("store_id")
    book_info = body.get("book_info")
    stock_level = int(body.get("stock_level", 0))

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    if not book_info or "id" not in book_info:
        return jsonify({"message": "invalid book_info"}), 500

    book_id = book_info["id"]
    book_json_str = json.dumps(book_info)

    sm = Seller()
    code, msg = sm.add_book(
        user_id,
        store_id,
        book_id,
        book_json_str,
        stock_level
    )
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200


@bp_seller.route("/add_stock_level", methods=["POST"])
def add_stock_level():
    body = request.get_json()
    token = request.headers.get("token", "")

    user_id = body.get("user_id")
    store_id = body.get("store_id")
    book_id = body.get("book_id")
    add_stock_level = int(body.get("add_stock_level", 0))

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    sm = Seller()
    code, msg = sm.add_stock_level(user_id, store_id, book_id, add_stock_level)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok"}), 200

@bp_seller.route("/deliver_order", methods=["POST"])
def deliver_order():
    token = request.headers.get("token", "")
    body = request.get_json()

    user_id = body.get("user_id")
    store_id = body.get("store_id")
    order_id = body.get("order_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401

    om = Order()
    ok, msg = om.deliver_order(store_id, order_id)
    if not ok:
        return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200

@bp_seller.route("/stats", methods=["GET"])
def get_store_stats():
    token = request.headers.get("token", "")
    user_id = request.args.get("user_id")
    store_id = request.args.get("store_id")

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401
        
    sm = Seller()
    code, msg, stats = sm.get_store_stats(user_id, store_id)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "stats": stats}), 200

# === Advanced Extensions: Coupon ===

@bp_seller.route("/create_coupon", methods=["POST"])
def create_coupon():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    store_id = body.get("store_id")
    name = body.get("name")
    threshold = int(body.get("threshold", 0))
    discount = int(body.get("discount", 0))
    stock = int(body.get("stock", 0))
    end_time_str = body.get("end_time") # Format: "YYYY-MM-DD HH:MM:SS"

    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401
        
    try:
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return jsonify({"message": "invalid date format"}), 400

    cm = CouponManager()
    code, msg, coupon_id = cm.create_coupon(user_id, store_id, name, threshold, discount, stock, end_time)
    if code != 200:
        return jsonify({"message": msg}), code
    return jsonify({"message": "ok", "coupon_id": coupon_id}), 200
