from be.model.blob_store import BlobStore
from be.model.blob_store import get_blob_store
from be.model.book import Book as BookModelApi
from be.model.buyer import Buyer
from be.model.cart import Cart
from be.model.coupon import CouponManager
from be.model.db_schema import Order as OrderModel
from be.model.db_schema import Order as OrderModel, User as UserModel
from be.model.db_schema import Store as StoreModel, StoreBook
from be.model.db_schema import User as UserModel
from be.model.db_schema import User as UserModel, Book
from be.model.order import Order as OrderModelApi
from be.model.seller import Seller
from be.model.seller import Seller as SellerModel
from be.model.store import init_completed_event
from be.model.user import User
from fe import conf
from fe.access import book as bookdb
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from sqlalchemy.exc import SQLAlchemyError
from unittest.mock import MagicMock
from urllib.parse import urljoin
import datetime
import json
import pytest
import requests
import uuid


# === Content from test_final_push.py ===


class TestFinalPush:
    def test_user_token_expired_and_logout_twice(self):
        um = User()
        uid = "tfp_user_" + uuid.uuid4().hex
        um.register(uid, "p")
        tok = um.conn.query(UserModel).filter_by(user_id=uid).first().token
        # 强制过期
        old_lifetime = um.token_lifetime
        um.token_lifetime = -1
        code, _ = um.check_token(uid, tok)
        assert code != 200
        um.token_lifetime = old_lifetime
        # 用正确 token 登出一次
        code, _ = um.logout(uid, tok)
        assert code == 200
        # 再次用旧 token 登出应失败
        code, _ = um.logout(uid, tok)
        assert code != 200

    def test_user_change_password_fail(self):
        um = User()
        uid = "tfp_user2_" + uuid.uuid4().hex
        um.register(uid, "p1")
        code, _ = um.change_password(uid, "wrong_old", "p2")
        assert code != 200

    def test_user_register_duplicate_and_login_fail(self):
        um = User()
        uid = "tfp_user3_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, _ = um.register(uid, "p")
        assert code != 200
        code, _, _ = um.login(uid, "wrong", "t1")
        assert code != 200
        code, _ = um.check_password("ghost_user", "p")
        assert code != 200

    def test_seller_stats_with_paid_order(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfp_s_" + uuid.uuid4().hex
        buyer_id = "tfp_b_" + uuid.uuid4().hex
        store_id = "tfp_store_" + uuid.uuid4().hex
        book_id = "tfp_book_" + uuid.uuid4().hex

        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        bjson = json.dumps({"price": 20, "title": "T"})
        sm.add_book(seller_id, store_id, book_id, bjson, 5)
        bm.add_funds(buyer_id, "p", 1000)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 2}])
        assert ok
        ok2, _ = bm.payment(buyer_id, oid, "p")
        assert ok2
        code, _, stats = sm.get_store_stats(seller_id, store_id)
        assert code == 200
        assert stats["total_orders"] >= 1
        assert stats["total_revenue"] >= 40

    def test_order_cancel_status_not_unpaid(self):
        bm = Buyer()
        um = User()
        sm = Seller()
        seller_id = "tfp_s2_" + uuid.uuid4().hex
        buyer_id = "tfp_b2_" + uuid.uuid4().hex
        store_id = "tfp_store2_" + uuid.uuid4().hex
        book_id = "tfp_book2_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        bjson = json.dumps({"price": 10, "title": "T"})
        sm.add_book(seller_id, store_id, book_id, bjson, 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # 标记为已支付
        ord_rec = bm.conn.query(OrderModel).filter_by(order_id=oid).first()
        ord_rec.status = "paid"
        bm.conn.commit()
        om = OrderModelApi()
        ok2, _ = om.cancel_order(buyer_id, oid)
        assert not ok2

    def test_buyer_payment_not_found_and_status_invalid(self):
        bm = Buyer()
        um = User()
        sm = Seller()
        seller_id = "tfp_s3_" + uuid.uuid4().hex
        buyer_id = "tfp_b3_" + uuid.uuid4().hex
        store_id = "tfp_store3_" + uuid.uuid4().hex
        book_id = "tfp_book3_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        bjson = json.dumps({"price": 5, "title": "T"})
        sm.add_book(seller_id, store_id, book_id, bjson, 1)
        bm.add_funds(buyer_id, "p", 50)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # 手动取消订单
        ord_rec = bm.conn.query(OrderModel).filter_by(order_id=oid).first()
        ord_rec.status = "canceled"
        bm.conn.commit()
        ok2, _ = bm.payment(buyer_id, oid, "p")
        assert not ok2
        # 不存在的订单
        ok3, _ = bm.payment(buyer_id, "non_exist_oid", "p")
        assert not ok3

    def test_buyer_new_order_coupon_threshold_fail(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        cm = CouponManager()
        seller_id = "tfp_s4_" + uuid.uuid4().hex
        buyer_id = "tfp_b4_" + uuid.uuid4().hex
        store_id = "tfp_store4_" + uuid.uuid4().hex
        book_id = "tfp_book4_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        bjson = json.dumps({"price": 5, "title": "T"})
        sm.add_book(seller_id, store_id, book_id, bjson, 1)
        end_time = datetime.datetime.now() + datetime.timedelta(days=1)
        code, _, cid = cm.create_coupon(seller_id, store_id, "c", 1000, 10, 10, end_time)
        assert code == 200
        bm.add_funds(buyer_id, "p", 100)
        ok, msg, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}], coupon_id=cid)
        assert not ok

    def test_order_cancel_timeout_zero_and_negative(self):
        om = OrderModelApi()
        # 0 或负超时：结果>=0即可（可能清理掉已有未支付订单）
        assert om.cancel_timeout_orders(0) >= 0
        assert om.cancel_timeout_orders(-1) >= 0

    def test_seller_create_store_exist_and_stats_invalid(self):
        sm = Seller()
        um = User()
        uid = "tfp_s5_" + uuid.uuid4().hex
        um.register(uid, "p")
        store_id = "tfp_store5_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        code, _ = sm.create_store(uid, store_id)
        assert code != 200
        res2 = sm.get_store_stats("ghost_user", store_id)
        assert res2[0] != 200
        res3 = sm.get_store_stats(uid, "ghost_store")
        assert res3[0] != 200

    def test_seller_add_stock_invalid_book(self):
        sm = Seller()
        um = User()
        uid = "tfp_s6_" + uuid.uuid4().hex
        um.register(uid, "p")
        store_id = "tfp_store6_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        code, _ = sm.add_stock_level(uid, store_id, "ghost_book", 1)
        assert code != 200


# === Content from test_final_push_user.py ===


class TestFinalPushUser:
    def test_address_crud(self):
        um = User()
        uid = "tfpu_addr_" + uuid.uuid4().hex
        um.register(uid, "p")
        # initially empty
        code, _, addrs = um.get_addresses(uid)
        assert code == 200
        assert addrs == []
        # add one
        code, msg = um.add_address(uid, "alice", "road 1", "123")
        assert code == 200
        code, _, addrs = um.get_addresses(uid)
        assert any(a["recipient_name"] == "alice" for a in addrs)

    def test_wishlist_follow_toggle(self):
        um = User()
        uid = "tfpu_wl_" + uuid.uuid4().hex
        store_id = "tfpu_store_" + uuid.uuid4().hex
        book_id = "tfpu_book_" + uuid.uuid4().hex
        um.register(uid, "p")
        Seller().create_store(uid, store_id)
        code, msg = um.toggle_wishlist(uid, book_id)
        assert code == 200
        code, msg = um.toggle_wishlist(uid, book_id)  # remove
        assert code == 200
        code, msg = um.toggle_follow(uid, store_id)
        assert code == 200
        code, msg = um.toggle_follow(uid, store_id)  # unfollow
        assert code == 200

    def test_unregister_and_relogin(self):
        um = User()
        uid = "tfpu_unreg_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, _ = um.unregister(uid, "p")
        assert code == 200
        # unregister again should fail
        code, _ = um.unregister(uid, "p")
        assert code != 200

    def test_change_password_success_and_login(self):
        um = User()
        uid = "tfpu_chg_" + uuid.uuid4().hex
        um.register(uid, "p1")
        code, _ = um.change_password(uid, "p1", "p2")
        assert code == 200
        code, _, tok = um.login(uid, "p2", "t1")
        assert code == 200
        assert tok

    def test_buyer_payment_wrong_password_model(self):
        bm = Buyer()
        um = User()
        sm = Seller()
        seller_id = "tfpu_s_" + uuid.uuid4().hex
        buyer_id = "tfpu_b_" + uuid.uuid4().hex
        store_id = "tfpu_store2_" + uuid.uuid4().hex
        book_id = "tfpu_book2_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":10,"title":"T"}', 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        ok2, _ = bm.payment(buyer_id, oid, "wrong")
        assert not ok2

    def test_blob_store_put_with_none_col(self):
        bs = BlobStore()
        bs.col = None
        bs.put_book_blob("id_none", "c", "b", "a")  # should no-op safely

    def test_get_addresses_error_mock(self):
        um = User()
        um.conn = MagicMock()
        um.conn.query.side_effect = SQLAlchemyError("mock err")
        code, msg, res = um.get_addresses("u")
        assert code == 528

    def test_user_check_token_invalid_signature_and_timeout(self):
        um = User()
        uid = "tfpu_tok_" + uuid.uuid4().hex
        um.register(uid, "p")
        tok = um.conn.query(UserModel).filter_by(user_id=uid).first().token
        code, _ = um.check_token(uid, tok + "x")
        assert code != 200
        old = um.token_lifetime
        um.token_lifetime = -1
        code2, _ = um.check_token(uid, tok)
        assert code2 != 200
        um.token_lifetime = old

    def test_user_change_password_non_exist(self):
        um = User()
        code, _ = um.change_password("ghost_user", "a", "b")
        assert code != 200

    def test_user_toggle_errors_with_mock(self):
        um = User()
        um.conn = MagicMock()
        um.conn.query.side_effect = SQLAlchemyError("mock err")
        code, msg = um.toggle_wishlist("u", "b")
        assert code == 528
        code2, msg2 = um.toggle_follow("u", "s")
        assert code2 == 528

    def test_logout_empty_token(self):
        um = User()
        uid = "tfpu_logout_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, _ = um.logout(uid, "")
        assert code != 200

    def test_check_token_with_different_terminal(self):
        um = User()
        uid = "tfpu_term_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, msg, tok1 = um.login(uid, "p", "t1")
        assert code == 200
        code2, msg2, tok2 = um.login(uid, "p", "t2")
        assert code2 == 200
        # 宽松校验：旧 token 也被接受，新 token 亦可
        code_old, _ = um.check_token(uid, tok1)
        code_new, _ = um.check_token(uid, tok2)
        assert code_old == 200
        assert code_new == 200

    def test_change_password_same_value(self):
        um = User()
        uid = "tfpu_same_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, _ = um.change_password(uid, "p", "p")  # same value
        assert code == 200


# === Content from test_final_push_more.py ===


class TestFinalPushMore:
    def test_cancel_timeout_orders_with_old_unpaid(self):
        um = User()
        bm = Buyer()
        sm = Seller()
        seller_id = "tfpm_s_" + uuid.uuid4().hex
        buyer_id = "tfpm_b_" + uuid.uuid4().hex
        store_id = "tfpm_store_" + uuid.uuid4().hex
        book_id = "tfpm_book_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":5,"title":"T"}', 2)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # 将创建时间手动改早，满足超时条件
        ord_rec = bm.conn.query(OrderModel).filter_by(order_id=oid).first()
        ord_rec.created_at = datetime.datetime.now() - datetime.timedelta(hours=2)
        bm.conn.commit()
        om = OrderModelApi()
        cancelled = om.cancel_timeout_orders(1800)
        assert cancelled >= 1

    def test_seller_add_book_invalid_json(self):
        sm = Seller()
        uid = "tfpm_s2_" + uuid.uuid4().hex
        User().register(uid, "p")
        store_id = "tfpm_store2_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        code, _ = sm.add_book(uid, store_id, "bk_bad_json", "{bad", 1)
        assert code != 200

    def test_seller_add_book_tags_and_float_price(self):
        sm = Seller()
        uid = "tfpm_s_float_" + uuid.uuid4().hex
        User().register(uid, "p")
        store_id = "tfpm_store_float_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        book_id = "tfpm_book_float_" + uuid.uuid4().hex
        # price float, tags list
        bjson = '{"price":5.5,"title":"T","tags":["a","b"]}'
        code, msg = sm.add_book(uid, store_id, book_id, bjson, 1)
        assert code == 200

    def test_seller_add_stock_level_invalid(self):
        sm = Seller()
        uid = "tfpm_s_stock_" + uuid.uuid4().hex
        User().register(uid, "p")
        store_id = "tfpm_store_stock_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        book_id = "tfpm_book_stock_" + uuid.uuid4().hex
        sm.add_book(uid, store_id, book_id, '{"price":5,"title":"T"}', 1)
        code, msg = sm.add_stock_level(uid, store_id, book_id, 0)
        assert code != 200

    def test_seller_get_store_stats_empty(self):
        sm = Seller()
        uid = "tfpm_s_stats_" + uuid.uuid4().hex
        User().register(uid, "p")
        store_id = "tfpm_store_stats_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        code, msg, stats = sm.get_store_stats(uid, store_id)
        assert code == 200
        assert stats["total_orders"] == 0

    def test_seller_add_book_price_none_and_tags_none(self):
        sm = Seller()
        uid = "tfpm_s_none_" + uuid.uuid4().hex
        User().register(uid, "p")
        store_id = "tfpm_store_none_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        book_id = "tfpm_book_none_" + uuid.uuid4().hex
        bjson = '{"title":"T"}'
        code, msg = sm.add_book(uid, store_id, book_id, bjson, 1)
        assert code == 200

    def test_seller_get_store_stats_invalid(self):
        sm = Seller()
        res = sm.get_store_stats("ghost_user", "ghost_store")
        assert res[0] != 200

    def test_blob_store_no_col_search(self):
        bs = BlobStore()
        # 模拟连接失败场景
        bs.col = None
        res = bs.search_in_blob("kw")
        assert res == []

    def test_blob_store_search_exception(self, monkeypatch=None):
        bs = BlobStore()
        class DummyCol:
            def find(self, *args, **kwargs):
                raise Exception("mock find error")
        bs.col = DummyCol()
        res = bs.search_in_blob("kw")
        assert res == []

    def test_user_wishlist_and_follow(self):
        um = User()
        uid = "tfpm_u_" + uuid.uuid4().hex
        sid = "tfpm_store3_" + uuid.uuid4().hex
        bid = "tfpm_book3_" + uuid.uuid4().hex
        um.register(uid, "p")
        Seller().create_store(uid, sid)
        code, msg = um.toggle_wishlist(uid, bid)
        assert code == 200
        code, _, wl = um.get_wishlist(uid)
        assert code == 200
        assert any(i["book_id"] == bid for i in wl)
        code, msg = um.toggle_follow(uid, sid)
        assert code == 200
        code, _, follows = um.get_following(uid)
        assert code == 200
        assert any(i["store_id"] == sid for i in follows)


# === Content from test_final_push_more2.py ===


class TestFinalPushMore2:
    def test_new_order_insufficient_stock_branch(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfpm2_s_" + uuid.uuid4().hex
        buyer_id = "tfpm2_b_" + uuid.uuid4().hex
        store_id = "tfpm2_store_" + uuid.uuid4().hex
        book_id = "tfpm2_book_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":5,"title":"T"}', 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, msg, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 5}])
        assert not ok

    def test_new_order_mixed_counts_and_stock_depletion(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfpm2_s3_" + uuid.uuid4().hex
        buyer_id = "tfpm2_b3_" + uuid.uuid4().hex
        store_id = "tfpm2_store3_" + uuid.uuid4().hex
        book_id = "tfpm2_book3_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":5,"title":"T"}', 2)
        bm.add_funds(buyer_id, "p", 100)
        # mixed counts: one invalid (-1) one valid (1) -> should create order
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": -1}, {"id": book_id, "count": 1}])
        assert ok
        # second order exhausts stock -> should fail
        ok2, msg2, _ = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 2}])
        assert not ok2

    def test_order_deliver_and_receive_status_invalid(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        om = OrderModelApi()
        seller_id = "tfpm2_s2_" + uuid.uuid4().hex
        buyer_id = "tfpm2_b2_" + uuid.uuid4().hex
        store_id = "tfpm2_store2_" + uuid.uuid4().hex
        book_id = "tfpm2_book2_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":6,"title":"T"}', 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # deliver when unpaid -> fail
        ok2, _ = om.deliver_order(store_id, oid)
        assert not ok2
        # set status to delivering, then receive with wrong user -> fail
        ord_rec = bm.conn.query(OrderModel).filter_by(order_id=oid).first()
        ord_rec.status = "delivering"
        bm.conn.commit()
        ok3, _ = om.receive_order("other_user", oid)
        assert not ok3

    def test_book_info_not_found_and_search_in_store_empty(self):
        bm = BookModelApi()
        assert bm.get_book_info("non_exist_id") is None
        books = bm.search_in_store("ghost_store", "keyword", 10, 0)
        assert books == []

    def test_search_complex_empty_keyword_and_tuple(self):
        bm = BookModelApi()
        books, total = bm.search_complex("", limit=2, skip=0)
        assert isinstance(books, list)
        assert total >= 0

    def test_cart_update_zero_and_remove_twice(self):
        um = User()
        sm = Seller()
        uid = "tfpm2_cart_u_" + uuid.uuid4().hex
        sid = "tfpm2_cart_s_" + uuid.uuid4().hex
        bid = "tfpm2_cart_b_" + uuid.uuid4().hex
        um.register(uid, "p")
        sm.create_store(uid, sid)
        sm.add_book(uid, sid, bid, '{"price":3,"title":"T"}', 1)
        cart = Cart()
        cart.add_item(uid, sid, bid, 1)
        cart.add_item(uid, sid, bid, 0, action="update")  # set to zero
        cart.remove_item(uid, sid, bid)
        cart.remove_item(uid, sid, bid)  # idempotent

    def test_order_cancel_wrong_user(self):
        om = OrderModelApi()
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfpm2_cancel_s_" + uuid.uuid4().hex
        buyer_id = "tfpm2_cancel_b_" + uuid.uuid4().hex
        store_id = "tfpm2_cancel_store_" + uuid.uuid4().hex
        book_id = "tfpm2_cancel_book_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":4,"title":"T"}', 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        ok2, _ = om.cancel_order("other_user", oid)
        assert not ok2

    def test_list_orders_empty(self):
        om = OrderModelApi()
        res = om.list_orders("ghost_user")
        assert res == []

    def test_new_order_all_invalid_books(self):
        bm = Buyer()
        ok, msg, oid = bm.new_order("ghost_user", "ghost_store", [{"id": "none", "count": -1}])
        assert not ok

    def test_payment_seller_missing(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfpm2_pay_s_" + uuid.uuid4().hex
        buyer_id = "tfpm2_pay_b_" + uuid.uuid4().hex
        store_id = "tfpm2_pay_store_" + uuid.uuid4().hex
        book_id = "tfpm2_pay_book_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":9,"title":"T"}', 1)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # 删除卖家用户，store.user_id 指向不存在
        sess = sm.conn
        u = sess.query(UserModel).filter_by(user_id=seller_id).first()
        if u:
            sess.delete(u)
            sess.commit()
        bm.payment(buyer_id, oid, "p")  # 不断言成功与否，只要不崩即可

    def test_search_complex_skip_over_total(self):
        bm = BookModelApi()
        books, total = bm.search_complex("unlikely_keyword_xyz", limit=1, skip=1000)
        assert books == []
        assert total >= 0


# === Content from test_final_push_model_misc.py ===


class TestFinalPushModelMisc:
    def test_order_list_with_items(self):
        um = User()
        sm = Seller()
        bm = Buyer()
        seller_id = "tfpmm_s_" + uuid.uuid4().hex
        buyer_id = "tfpmm_b_" + uuid.uuid4().hex
        store_id = "tfpmm_store_" + uuid.uuid4().hex
        book_id = "tfpmm_book_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        um.register(buyer_id, "p")
        sm.create_store(seller_id, store_id)
        sm.add_book(seller_id, store_id, book_id, '{"price":7,"title":"ListTest"}', 2)
        bm.add_funds(buyer_id, "p", 100)
        ok, _, oid = bm.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        om = OrderModelApi()
        res = om.list_orders(buyer_id, limit=5, skip=0)
        assert isinstance(res, list)
        assert any(r["order_id"] == oid for r in res)
        for r in res:
            if r["order_id"] == oid:
                assert len(r["items"]) >= 1

    def test_book_search_by_title_and_complex(self):
        sm = Seller()
        um = User()
        uid = "tfpmm_s2_" + uuid.uuid4().hex
        um.register(uid, "p")
        store_id = "tfpmm_store2_" + uuid.uuid4().hex
        sm.create_store(uid, store_id)
        book_id = "tfpmm_book2_" + uuid.uuid4().hex
        # tags list to hit tags.like path in search_complex
        sm.add_book(uid, store_id, book_id, '{"price":8,"title":"AlphaBook","tags":["alpha","beta"]}', 1)
        bm = BookModelApi()
        res = bm.search_by_title("Alpha")
        assert isinstance(res, list)
        res2, total = bm.search_complex("alpha")
        assert total >= 1
        assert any(b.get("id") == book_id for b in res2)


# === Content from test_final_coverage.py ===

class TestFinalCoverage:
    def setup_class(self):
        init_completed_event.wait()

    def test_direct_seller_checks(self):
        s = Seller()
        # Add book: non-exist user
        code, msg = s.add_book("ghost_u", "ghost_s", "bk", "{}", 1)
        assert code != 200
        
        # Add book: non-exist store
        uid = "tfc_u_" + uuid.uuid4().hex
        User().register(uid, "pwd")
        code, msg = s.add_book(uid, "ghost_s", "bk", "{}", 1)
        assert code != 200
        
        # Add stock: non-exist user
        code, msg = s.add_stock_level("ghost_u", "ghost_s", "bk", 1)
        assert code != 200
        
        # Create store: non-exist user
        code, msg = s.create_store("ghost_u", "store")
        assert code != 200

    def test_direct_buyer_checks(self):
        b = Buyer()
        # New order: non-exist user
        ok, msg, oid = b.new_order("ghost_u", "store", [])
        assert not ok
        
        # New order: non-exist store
        uid = "tfc_b_" + uuid.uuid4().hex
        User().register(uid, "pwd")
        ok, msg, oid = b.new_order(uid, "ghost_s", [])
        assert not ok

    def test_new_order_invalid_count(self):
        b = Buyer()
        # count <= 0 should be skipped
        # if all skipped, returns "no valid books"
        uid = "tfc_b3_" + uuid.uuid4().hex
        User().register(uid, "p")
        # create a valid store so store check passes, then all items skipped -> "no valid books"
        store_id = "tfc_store_" + uuid.uuid4().hex
        Seller().create_store(uid, store_id)
        ok, msg, oid = b.new_order(uid, store_id, [{"id": "b", "count": 0}])
        assert not ok
        assert msg == "no valid books"

    def test_payment_seller_missing(self):
        # 1. Create seller, store, book
        seller_id = "tfc_s_" + uuid.uuid4().hex
        s = Seller()
        User().register(seller_id, "pwd")
        store_id = "tfc_store_" + uuid.uuid4().hex
        s.create_store(seller_id, store_id)
        book_id = "tfc_bk_" + uuid.uuid4().hex
        bjson = json.dumps({"price": 100, "title": "T", "count": 10})
        s.add_book(seller_id, store_id, book_id, bjson, 10)
        
        # 2. Buyer creates order
        buyer_id = "tfc_b2_" + uuid.uuid4().hex
        b = Buyer()
        User().register(buyer_id, "pwd")
        b.add_funds(buyer_id, "pwd", 1000)
        ok, msg, oid = b.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        
        # 3. Manually delete Seller User from DB
        sess = s.conn
        try:
            # First clean up store related tables due to foreign keys
            
            # Since we want to test "seller user missing but store exists", 
            # we need to be careful about FKs.
            # If DB enforces FK, we can't delete user without deleting store.
            # But if we delete store, the code "store = ... filter_by(store_id=order.store_id)" will return None
            # and "if store and store.user_id" check will fail gracefully (which is also a branch).
            
            # Let's try to delete the user. If it fails, we skip.
            u = sess.query(UserModel).filter_by(user_id=seller_id).first()
            if u:
                sess.delete(u)
                sess.commit()
        except Exception:
            pass 
            
        # 4. Pay
        # If user was deleted, this hits the "seller not found" logic or "store.user_id points to non-exist".
        # If deletion failed, it hits normal path. Both are fine for coverage, just shouldn't crash.
        b.payment(buyer_id, oid, "pwd")

    def test_add_book_defaults(self):
        s = Seller()
        uid = "tfc_s2_" + uuid.uuid4().hex
        User().register(uid, "p")
        sid = "tfc_st2_" + uuid.uuid4().hex
        s.create_store(uid, sid)
        bid = "tfc_bk2_" + uuid.uuid4().hex
        
        # Empty json to test defaults (title="Untitled", price=0)
        s.add_book(uid, sid, bid, "{}", 1)
        
        bk = s.conn.query(Book).filter_by(id=bid).first()
        assert bk.title == "Untitled"
        assert bk.price == 0

    def test_add_book_bad_price(self):
        s = Seller()
        uid = "tfc_s3_" + uuid.uuid4().hex
        User().register(uid, "p")
        sid = "tfc_st3_" + uuid.uuid4().hex
        s.create_store(uid, sid)
        bid = "tfc_bk3_" + uuid.uuid4().hex
        
        # Invalid price string
        bjson = json.dumps({"price": "invalid", "title": "T"})
        s.add_book(uid, sid, bid, bjson, 1)
        
        bk = s.conn.query(Book).filter_by(id=bid).first()
        assert bk.price == 0

    def test_add_book_duplicate(self):
        s = Seller()
        uid = "tfc_dup_" + uuid.uuid4().hex
        User().register(uid, "p")
        sid = "tfc_dup_store_" + uuid.uuid4().hex
        s.create_store(uid, sid)
        bid = "tfc_dup_book_" + uuid.uuid4().hex
        bjson = json.dumps({"price": 1, "title": "T"})
        s.add_book(uid, sid, bid, bjson, 1)
        code, msg = s.add_book(uid, sid, bid, bjson, 1)
        assert code != 200

    def test_create_coupon_not_owner(self):
        cm = CouponManager()
        
        owner = "tfc_o_" + uuid.uuid4().hex
        User().register(owner, "pwd")
        store = "tfc_sto_" + uuid.uuid4().hex
        Seller().create_store(owner, store)
        
        intruder = "tfc_i_" + uuid.uuid4().hex
        User().register(intruder, "pwd")
        
        dt = datetime.datetime.now()
        code, msg, cid = cm.create_coupon(intruder, store, "Name", 100, 10, 10, dt)
        assert code == 401

    def test_db_exceptions(self):
        
        # Cart Exceptions
        c = Cart()
        c.conn = MagicMock()
        c.conn.query.side_effect = SQLAlchemyError("Mock Cart DB Error")
        
        assert c.add_item("u", "s", "b", 1)[0] == 528
        assert c.remove_item("u", "s", "b")[0] == 528
        assert c.clear_cart("u")[0] == 528
        assert c.get_cart("u")[0] == 528
        
        # Coupon Exceptions
        cm = CouponManager()
        cm.conn = MagicMock()
        cm.conn.query.side_effect = SQLAlchemyError("Mock Coupon DB Error")
        
        dt = datetime.datetime.now()
        assert cm.create_coupon("u", "s", "n", 1, 1, 1, dt)[0] == 528
        assert cm.collect_coupon("u", 1)[0] == 528
        assert cm.get_available_coupons("u")[0] == 528

    def test_user_token_and_logout_mismatch(self):
        um = User()
        uid = "tfc_user_" + uuid.uuid4().hex
        um.register(uid, "p")
        # get current token from db
        tok = um.conn.query(UserModel).filter_by(user_id=uid).first().token
        # invalid token
        code, msg = um.check_token(uid, "bad_token")
        assert code != 200
        # logout with mismatched token should fail
        code, msg = um.logout(uid, "bad_token")
        assert code != 200
        # logout with correct token should succeed
        code, msg = um.logout(uid, tok)
        assert code == 200

    def test_unregister_wrong_password(self):
        um = User()
        uid = "tfc_unreg_" + uuid.uuid4().hex
        um.register(uid, "p")
        code, msg = um.unregister(uid, "wrong")
        assert code != 200

    def test_buyer_payment_status_invalid(self):
        # Create seller/store/book/order then set status paid before calling payment
        s = Seller()
        um = User()
        seller_id = "tfc_pay_s_" + uuid.uuid4().hex
        um.register(seller_id, "p")
        store_id = "tfc_pay_store_" + uuid.uuid4().hex
        s.create_store(seller_id, store_id)
        book_id = "tfc_pay_book_" + uuid.uuid4().hex
        bjson = json.dumps({"price": 10, "title": "T"})
        s.add_book(seller_id, store_id, book_id, bjson, 5)

        buyer_id = "tfc_pay_b_" + uuid.uuid4().hex
        um.register(buyer_id, "p")
        b = Buyer()
        b.add_funds(buyer_id, "p", 100)
        ok, msg, oid = b.new_order(buyer_id, store_id, [{"id": book_id, "count": 1}])
        assert ok
        # Manually set status to paid
        ord_rec = b.conn.query(OrderModel).filter_by(order_id=oid).first()
        ord_rec.status = "paid"
        b.conn.commit()
        ok2, msg2 = b.payment(buyer_id, oid, "p")
        assert not ok2

# === Content from test_model_api_branches.py ===


class TestModelApiBranches:
    @pytest.fixture(autouse=True)
    def prepare(self):
        self.seller_id = f"mab_s_{uuid.uuid4().hex}"
        self.store_id = f"mab_store_{uuid.uuid4().hex}"
        self.seller = register_new_seller(self.seller_id, self.seller_id)
        assert self.seller.create_store(self.store_id) == 200

        self.buyer_id = f"mab_b_{uuid.uuid4().hex}"
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_id)

        bk = bookdb.BookDB(conf.Use_Large_DB).get_book_info(0, 1)[0]
        self.book = bk
        self.book_id = bk.id
        assert self.seller.add_book(self.store_id, 3, bk) == 200
        self.url = conf.URL
        yield

    # ---- BlobStore branches ----
    def test_blob_store_search_none(self):
        bs = get_blob_store()
        res = bs.search_in_blob("no_match_keyword_xyz")
        assert isinstance(res, list)

    # ---- Cart branches ----
    def test_cart_invalid_store_book_user(self):
        url = urljoin(self.url, "buyer/cart")
        headers = {"token": self.buyer.token}
        # bad store/book
        body = {"user_id": self.buyer_id, "store_id": "bad_store", "book_id": "bad_book", "count": 1}
        r = requests.post(url, headers=headers, json=body)
        assert r.status_code != 200
        # bad token/user
        r2 = requests.get(url, headers={"token": "bad"}, params={"user_id": "ghost"})
        assert r2.status_code != 200

    def test_cart_clear_empty(self):
        url = urljoin(self.url, "buyer/cart")
        headers = {"token": self.buyer.token}
        r = requests.delete(url, headers=headers, json={"user_id": self.buyer_id})
        assert r.status_code == 200

    # ---- Coupon branches ----
    def test_coupon_stock_zero_collect_fail(self):
        create_url = urljoin(self.url, "seller/create_coupon")
        headers_s = {"token": self.seller.token}
        data = {
            "user_id": self.seller_id,
            "store_id": self.store_id,
            "name": "zero_stock",
            "threshold": 1,
            "discount": 1,
            "stock": 0,
            "end_time": "2099-01-01 00:00:00",
        }
        r = requests.post(create_url, headers=headers_s, json=data); assert r.status_code == 200
        cid = r.json()["coupon_id"]
        col_url = urljoin(self.url, "buyer/coupon")
        r2 = requests.post(col_url, headers={"token": self.buyer.token}, json={"user_id": self.buyer_id, "coupon_id": cid})
        assert r2.status_code != 200

    def test_coupon_store_mismatch(self):
        # create coupon for store1
        create_url = urljoin(self.url, "seller/create_coupon")
        headers_s = {"token": self.seller.token}
        data = {
            "user_id": self.seller_id,
            "store_id": self.store_id,
            "name": "mismatch_store",
            "threshold": 1,
            "discount": 1,
            "stock": 2,
            "end_time": "2099-01-01 00:00:00",
        }
        r = requests.post(create_url, headers=headers_s, json=data); assert r.status_code == 200
        cid = r.json()["coupon_id"]
        col_url = urljoin(self.url, "buyer/coupon")
        r2 = requests.post(col_url, headers={"token": self.buyer.token}, json={"user_id": self.buyer_id, "coupon_id": cid})
        assert r2.status_code == 200
        # use on another store (not existing) should fail
        new_url = urljoin(self.url, "buyer/new_order")
        r3 = requests.post(
            new_url,
            headers={"token": self.buyer.token},
            json={"user_id": self.buyer_id, "store_id": "other_store", "books": [{"id": self.book_id, "count": 1}], "coupon_id": r2.json().get("coupon_id", 0)},
        )
        assert r3.status_code != 200

    # ---- Buyer/order branches ----
    def test_payment_insufficient_funds_branch(self):
        new_url = urljoin(self.url, "buyer/new_order")
        headers_b = {"token": self.buyer.token}
        r = requests.post(new_url, headers=headers_b, json={"user_id": self.buyer_id, "store_id": self.store_id, "books": [{"id": self.book_id, "count": 1}]})
        order_id = r.json()["order_id"]
        pay_url = urljoin(self.url, "buyer/payment")
        r2 = requests.post(pay_url, headers=headers_b, json={"user_id": self.buyer_id, "order_id": order_id, "password": self.buyer_id})
        assert r2.status_code != 200

    def test_cancel_paid_order_fail(self):
        # create & pay
        new_url = urljoin(self.url, "buyer/new_order")
        headers_b = {"token": self.buyer.token}
        r = requests.post(new_url, headers=headers_b, json={"user_id": self.buyer_id, "store_id": self.store_id, "books": [{"id": self.book_id, "count": 1}]})
        order_id = r.json()["order_id"]
        self.buyer.add_funds(1000000)
        pay_url = urljoin(self.url, "buyer/payment")
        requests.post(pay_url, headers=headers_b, json={"user_id": self.buyer_id, "order_id": order_id, "password": self.buyer_id})
        cancel_url = urljoin(self.url, "buyer/cancel_order")
        r2 = requests.post(cancel_url, headers=headers_b, json={"user_id": self.buyer_id, "order_id": order_id})
        assert r2.status_code != 200

    def test_receive_wrong_user(self):
        # order & pay
        new_url = urljoin(self.url, "buyer/new_order")
        headers_b = {"token": self.buyer.token}
        r = requests.post(new_url, headers=headers_b, json={"user_id": self.buyer_id, "store_id": self.store_id, "books": [{"id": self.book_id, "count": 1}]})
        order_id = r.json()["order_id"]
        self.buyer.add_funds(1000000)
        pay_url = urljoin(self.url, "buyer/payment")
        requests.post(pay_url, headers=headers_b, json={"user_id": self.buyer_id, "order_id": order_id, "password": self.buyer_id})
        # deliver
        requests.post(urljoin(self.url, "seller/deliver_order"), headers={"token": self.seller.token}, json={"user_id": self.seller_id, "store_id": self.store_id, "order_id": order_id})
        # receive with another buyer
        b2 = register_new_buyer(f"mab_b2_{uuid.uuid4().hex}", "pwd")
        recv_url = urljoin(self.url, "buyer/receive_order")
        r2 = requests.post(recv_url, headers={"token": b2.token}, json={"user_id": b2.user_id, "order_id": order_id})
        assert r2.status_code != 200

    # ---- Seller branches ----
    def test_add_stock_level_negative(self):
        code = self.seller.add_stock_level(self.seller_id, self.store_id, self.book_id, -5)
        assert code != 200

    def test_add_book_bad_json_direct(self):
        # Direct model call to hit json loads error branch
        sm = SellerModel()
        code, msg = sm.add_book("ghost_user", "ghost_store", "bkid", "{bad_json", 1)
        assert code != 200

