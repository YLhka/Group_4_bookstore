import requests
import simplejson
from urllib.parse import urljoin
from fe.access.auth import Auth


class Buyer:
    def __init__(self, url_prefix, user_id, password):
        self.url_prefix = urljoin(url_prefix, "buyer/")
        self.user_id = user_id
        self.password = password
        self.token = ""
        self.terminal = "my terminal"
        self.auth = Auth(url_prefix)
        code, self.token = self.auth.login(self.user_id, self.password, self.terminal)
        assert code == 200

    def new_order(self, store_id: str, book_id_and_count: [(str, int)]) -> (int, str):
        books = []
        for id_count_pair in book_id_and_count:
            books.append({"id": id_count_pair[0], "count": id_count_pair[1]})
        json = {"user_id": self.user_id, "store_id": store_id, "books": books}
        # print(simplejson.dumps(json))
        url = urljoin(self.url_prefix, "new_order")
        headers = {"token": self.token}
        r = requests.post(url, headers=headers, json=json)
        response_json = r.json()
        return r.status_code, response_json.get("order_id")

    def payment(self, order_id: str):
        json = {
            "user_id": self.user_id,
            "password": self.password,
            "order_id": order_id,
        }
        url = urljoin(self.url_prefix, "payment")
        headers = {"token": self.token}
        r = requests.post(url, headers=headers, json=json)
        return r.status_code

    def add_funds(self, add_value: str) -> int:
        json = {
            "user_id": self.user_id,
            "password": self.password,
            "add_value": add_value,
        }
        url = urljoin(self.url_prefix, "add_funds")
        headers = {"token": self.token}
        r = requests.post(url, headers=headers, json=json)
        return r.status_code

    # --- Extensions for compatibility with legacy tests ---
    def cancel_order(self, order_id: str) -> int:
        """Cancel an order (legacy test helper)."""
        url = urljoin(self.url_prefix, "cancel_order")
        headers = {"token": self.token}
        json = {"user_id": self.user_id, "order_id": order_id}
        r = requests.post(url, headers=headers, json=json)
        try:
            return r.status_code
        except Exception:
            return r.status_code

    def search_book(self, keyword: str, store_id: str = None, page: int = 1, limit: int = 20):
        """
        Legacy search wrapper used by older tests.
        Tests pass page,limit; convert to skip=(page-1)*limit.
        """
        from fe import conf
        url = urljoin(conf.URL, "book/search")
        skip = max(0, (page - 1) * limit)
        params = {"q": keyword, "limit": limit, "skip": skip}
        if store_id:
            params["store_id"] = store_id
        r = requests.get(url, params=params)
        if r.status_code != 200:
            return r.status_code, []
        data = r.json()
        return r.status_code, data.get("books", [])
