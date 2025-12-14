import uuid
import pytest
import requests

from fe import conf
from fe.access.new_seller import register_new_seller
from fe.access.new_buyer import register_new_buyer
from fe.access import book as bookdb


class TestOrderQueryAndCancel:
    @pytest.fixture(autouse=True)
    def prepare(self):
        # 卖家
        self.seller_id = f"s_{uuid.uuid1()}"
        self.store_id = f"st_{uuid.uuid1()}"
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)
        assert self.seller.create_store(self.store_id) == 200

        # 买家
        self.buyer_id = f"b_{uuid.uuid1()}"
        self.buyer_pwd = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_pwd)

        # 书
        bk = bookdb.BookDB(conf.Use_Large_DB).get_book_info(0, 1)[0]
        self.book_id = bk.id
        assert self.seller.add_book(self.store_id, 10, bk) == 200

        # 充值
        assert self.buyer.add_funds(100000) == 200

        # 下单但先不付款，方便测试取消
        code, order_id = self.buyer.new_order(self.store_id, [(self.book_id, 1)])
        assert code == 200
        self.order_id = order_id

        # 登录获取 token
        login_url = f"{conf.URL}/auth/login"
        self.buyer_token = requests.post(
            login_url,
            json={"user_id": self.buyer_id, "password": self.buyer_pwd, "terminal": "t1"},
        ).json()["token"]

        yield

    def test_list_orders(self):
        url = f"{conf.URL}/buyer/list_orders"
        resp = requests.get(
            url,
            headers={"token": self.buyer_token},
            params={"user_id": self.buyer_id, "limit": 10, "skip": 0},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["message"] == "ok"
        # 至少能看到刚刚那一单
        assert any(o["order_id"] == self.order_id for o in data["orders"])

    def test_cancel_order(self):
        url = f"{conf.URL}/buyer/cancel_order"
        resp = requests.post(
            url,
            headers={"token": self.buyer_token},
            json={"user_id": self.buyer_id, "order_id": self.order_id},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "ok"
