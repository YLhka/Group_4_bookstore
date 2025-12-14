import uuid
import requests
import pytest

from fe import conf
from fe.access.new_seller import register_new_seller
from fe.access.new_buyer import register_new_buyer
from fe.access import book as bookdb


class TestDeliverAndReceive:
    @pytest.fixture(autouse=True)
    def prepare(self):
        # 1. 注册卖家并开店
        self.seller_id = f"seller_{uuid.uuid1()}"
        self.store_id = f"store_{uuid.uuid1()}"
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)
        code = self.seller.create_store(self.store_id)
        assert code == 200

        # 2. 注册买家
        self.buyer_id = f"buyer_{uuid.uuid1()}"
        self.buyer_pwd = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_pwd)

        # 3. 卖家加一本书（从本地大库里拿一条）
        bk = bookdb.BookDB(conf.Use_Large_DB).get_book_info(0, 1)[0]
        self.book_id = bk.id
        code = self.seller.add_book(self.store_id, 100, bk)
        assert code == 200

        # 4. 买家充值
        code = self.buyer.add_funds(100000)
        assert code == 200

        # 5. 买家下单
        code, order_id = self.buyer.new_order(self.store_id, [(self.book_id, 2)])
        assert code == 200
        self.order_id = order_id

        # 6. 买家付款
        code = self.buyer.payment(self.order_id)
        assert code == 200

        # 7. 卖家登录拿 token（原来的 access 里应该有 token，可在 seller 对象里）
        # 这里我们直接再登录一次拿 token，方便下面的手写请求
        login_url = f"{conf.URL}/auth/login"
        resp = requests.post(
            login_url,
            json={"user_id": self.seller_id, "password": self.password, "terminal": "t1"},
        )
        assert resp.status_code == 200
        self.seller_token = resp.json()["token"]

        # 买家 token
        resp = requests.post(
            login_url,
            json={"user_id": self.buyer_id, "password": self.buyer_pwd, "terminal": "t1"},
        )
        assert resp.status_code == 200
        self.buyer_token = resp.json()["token"]

        yield

    def test_deliver_and_receive(self):
        # 卖家发货
        deliver_url = f"{conf.URL}/seller/deliver_order"
        resp = requests.post(
            deliver_url,
            headers={"token": self.seller_token},
            json={
                "user_id": self.seller_id,
                "store_id": self.store_id,
                "order_id": self.order_id,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "ok"

        # 买家收货
        receive_url = f"{conf.URL}/buyer/receive_order"
        resp = requests.post(
            receive_url,
            headers={"token": self.buyer_token},
            json={"user_id": self.buyer_id, "order_id": self.order_id},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "ok"
