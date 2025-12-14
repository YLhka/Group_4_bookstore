"""
测试订单相关的错误分支
"""
import uuid
import pytest
import requests

from fe import conf
from fe.access.new_seller import register_new_seller
from fe.access.new_buyer import register_new_buyer
from fe.access import book as bookdb


class TestOrderErrorCases:
    @pytest.fixture(autouse=True)
    def prepare(self):
        # 卖家
        self.seller_id = f"error_s_{uuid.uuid1()}"
        self.store_id = f"error_st_{uuid.uuid1()}"
        self.password = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.password)
        assert self.seller.create_store(self.store_id) == 200

        # 买家
        self.buyer_id = f"error_b_{uuid.uuid1()}"
        self.buyer_pwd = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_pwd)

        # 书
        bk = bookdb.BookDB(conf.Use_Large_DB).get_book_info(0, 1)[0]
        self.book_id = bk.id
        assert self.seller.add_book(self.store_id, 10, bk) == 200

        # 充值
        assert self.buyer.add_funds(100000) == 200

        # 下单并付款
        code, order_id = self.buyer.new_order(self.store_id, [(self.book_id, 1)])
        assert code == 200
        self.order_id = order_id
        assert self.buyer.payment(self.order_id) == 200

        # 登录获取 token
        login_url = f"{conf.URL}/auth/login"
        resp = requests.post(
            login_url,
            json={"user_id": self.buyer_id, "password": self.buyer_pwd, "terminal": "t1"},
        )
        self.buyer_token = resp.json()["token"]
        self.buyer.token = self.buyer_token # Fix: Update buyer object token

        resp = requests.post(
            login_url,
            json={"user_id": self.seller_id, "password": self.password, "terminal": "t1"},
        )
        self.seller_token = resp.json()["token"]
        self.seller.token = self.seller_token # Fix: Update seller object token

        yield

    def test_deliver_order_not_found(self):
        """测试发货时订单不存在"""
        url = f"{conf.URL}/seller/deliver_order"
        resp = requests.post(
            url,
            headers={"token": self.seller_token},
            json={
                "user_id": self.seller_id,
                "store_id": self.store_id,
                "order_id": "non_exist_order_id",
            },
        )
        assert resp.status_code == 500

    def test_deliver_order_wrong_store(self):
        """测试发货时订单不属于该店铺"""
        # 创建另一个店铺
        store_id2 = f"store2_{uuid.uuid1()}"
        assert self.seller.create_store(store_id2) == 200
        
        url = f"{conf.URL}/seller/deliver_order"
        resp = requests.post(
            url,
            headers={"token": self.seller_token},
            json={
                "user_id": self.seller_id,
                "store_id": store_id2,
                "order_id": self.order_id,
            },
        )
        assert resp.status_code == 500

    def test_deliver_order_not_paid(self):
        """测试发货时订单未付款"""
        # 创建新订单但不付款
        code, order_id2 = self.buyer.new_order(self.store_id, [(self.book_id, 1)])
        assert code == 200
        
        url = f"{conf.URL}/seller/deliver_order"
        resp = requests.post(
            url,
            headers={"token": self.seller_token},
            json={
                "user_id": self.seller_id,
                "store_id": self.store_id,
                "order_id": order_id2,
            },
        )
        assert resp.status_code == 500

    def test_receive_order_not_found(self):
        """测试收货时订单不存在"""
        url = f"{conf.URL}/buyer/receive_order"
        resp = requests.post(
            url,
            headers={"token": self.buyer_token},
            json={"user_id": self.buyer_id, "order_id": "non_exist_order_id"},
        )
        assert resp.status_code == 500

    def test_receive_order_wrong_user(self):
        """测试收货时订单不属于该用户"""
        # 创建另一个买家
        buyer_id2 = f"buyer2_{uuid.uuid1()}"
        buyer2 = register_new_buyer(buyer_id2, buyer_id2)
        assert buyer2.add_funds(100000) == 200
        
        login_url = f"{conf.URL}/auth/login"
        resp = requests.post(
            login_url,
            json={"user_id": buyer_id2, "password": buyer_id2, "terminal": "t1"},
        )
        buyer2_token = resp.json()["token"]
        
        url = f"{conf.URL}/buyer/receive_order"
        resp = requests.post(
            url,
            headers={"token": buyer2_token},
            json={"user_id": buyer_id2, "order_id": self.order_id},
        )
        assert resp.status_code == 500

    def test_receive_order_not_delivering(self):
        """测试收货时订单状态不是delivering"""
        url = f"{conf.URL}/buyer/receive_order"
        resp = requests.post(
            url,
            headers={"token": self.buyer_token},
            json={"user_id": self.buyer_id, "order_id": self.order_id},
        )
        # 订单状态是paid，不是delivering，应该失败
        assert resp.status_code == 500

    def test_cancel_order_not_cancelable(self):
        """测试取消已发货的订单"""
        # 先发货
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
        
        # 尝试取消已发货的订单
        cancel_url = f"{conf.URL}/buyer/cancel_order"
        resp = requests.post(
            cancel_url,
            headers={"token": self.buyer_token},
            json={"user_id": self.buyer_id, "order_id": self.order_id},
        )
        assert resp.status_code == 500

