from flask import Blueprint, request, jsonify
from be.model.book import Book
from be.model.user import User

bp_book = Blueprint("book", __name__, url_prefix="/book")

def check_token(user_id: str, token: str):
    um = User()
    code, _ = um.check_token(user_id, token)
    return code == 200

@bp_book.route("/search", methods=["GET"])
def search_book():
    keyword = request.args.get("q", "").strip()
    store_id = request.args.get("store_id")  
    limit = int(request.args.get("limit", 10))
    skip = int(request.args.get("skip", 0))

    book_model = Book()

    if store_id:
        books = book_model.search_in_store(store_id, keyword, limit, skip)
    else:
        books = book_model.search_complex(keyword, limit, skip)
        
    return jsonify({"message": "ok", "count": len(books), "books": books}), 200

@bp_book.route("/book", methods=["GET"])
def get_book_info():
    """Retrieve single book detail by id."""
    book_id = request.args.get("book_id")
    if not book_id:
        return jsonify({"message": "missing book_id"}), 400
    book_model = Book()
    info = book_model.get_book_info(book_id)
    if not info:
        return jsonify({"message": "not found"}), 404
    return jsonify({"message": "ok", "book": info}), 200

@bp_book.route("/review", methods=["POST"])
def add_review():
    token = request.headers.get("token", "")
    body = request.get_json()
    user_id = body.get("user_id")
    book_id = body.get("book_id")
    content = body.get("content")
    rating = int(body.get("rating", 5))
    
    if not check_token(user_id, token):
        return jsonify({"message": "authorization fail"}), 401
    
    book_model = Book()
    ok, msg = book_model.add_review(user_id, book_id, content, rating)
    if not ok:
         return jsonify({"message": msg}), 500
    return jsonify({"message": "ok"}), 200

@bp_book.route("/review", methods=["GET"])
def get_reviews():
    book_id = request.args.get("book_id")
    book_model = Book()
    reviews = book_model.get_reviews(book_id)
    return jsonify({"message": "ok", "reviews": reviews}), 200
