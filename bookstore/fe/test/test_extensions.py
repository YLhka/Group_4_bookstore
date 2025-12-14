import pytest
import uuid
from fe.access.new_buyer import register_new_buyer
from fe.access.new_seller import register_new_seller
from fe.access import book as bookdb
from fe import conf
import requests
from urllib.parse import urljoin

class TestExtensions:
    @pytest.fixture(autouse=True)
    def prepare(self):
        # Prepare Seller
        self.seller_id = "test_ext_s_{}".format(str(uuid.uuid1()))
        self.store_id = "test_ext_st_{}".format(str(uuid.uuid1()))
        self.seller_pwd = self.seller_id
        self.seller = register_new_seller(self.seller_id, self.seller_pwd)
        code = self.seller.create_store(self.store_id)
        if code != 200:
            print(f"Create Store Failed: {code}")
            # Try to get more info if possible, but fe.access objects don't return msg easily
        assert code == 200

        # Prepare Buyer
        self.buyer_id = "test_ext_b_{}".format(str(uuid.uuid1()))
        self.buyer_pwd = self.buyer_id
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_pwd)

        # Prepare Book
        self.book_db = bookdb.BookDB(conf.Use_Large_DB)
        self.book_list = self.book_db.get_book_info(0, 1)
        self.book_id = self.book_list[0].id
        assert self.seller.add_book(self.store_id, 0, self.book_list[0]) == 200
        
        # Base URL
        self.url_prefix = conf.URL

        yield

    def test_address(self):
        # 1. Add Address
        url = urljoin(self.url_prefix, "buyer/add_address")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "recipient": "Mr. Test",
            "address": "123 Test St, Test City",
            "phone": "1234567890"
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200

        # 2. Get Addresses
        url = urljoin(self.url_prefix, "buyer/get_addresses")
        params = {"user_id": self.buyer_id}
        r = requests.get(url, headers=headers, params=params)
        assert r.status_code == 200
        res = r.json()
        assert len(res["addresses"]) > 0
        assert res["addresses"][0]["recipient_name"] == "Mr. Test"

    def test_wishlist(self):
        # 1. Add to Wishlist
        url = urljoin(self.url_prefix, "buyer/wishlist")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "book_id": self.book_id
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        assert r.json()["message"] == "added"

        # 2. Get Wishlist
        url_get = urljoin(self.url_prefix, "buyer/wishlist")
        params = {"user_id": self.buyer_id}
        r = requests.get(url_get, headers=headers, params=params)
        assert r.status_code == 200
        assert len(r.json()["wishlist"]) == 1
        
        # 3. Remove from Wishlist
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        assert r.json()["message"] == "removed"

    def test_follow(self):
        # 1. Follow Store
        url = urljoin(self.url_prefix, "buyer/follow")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "store_id": self.store_id
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        assert r.json()["message"] == "followed"

        # 2. Get Following
        url_get = urljoin(self.url_prefix, "buyer/follow")
        params = {"user_id": self.buyer_id}
        r = requests.get(url_get, headers=headers, params=params)
        assert r.status_code == 200
        assert len(r.json()["following"]) == 1
        assert r.json()["following"][0]["store_id"] == self.store_id

        # 3. Unfollow
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        assert r.json()["message"] == "unfollowed"
    
    def test_review(self):
        # 1. Add Review
        url = urljoin(self.url_prefix, "book/review")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "book_id": self.book_id,
            "content": "Great book!",
            "rating": 5
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        
        # 2. Get Reviews
        url_get = urljoin(self.url_prefix, "book/review")
        params = {"book_id": self.book_id}
        r = requests.get(url_get, params=params)
        assert r.status_code == 200
        reviews = r.json()["reviews"]
        assert len(reviews) > 0
        assert reviews[0]["content"] == "Great book!"

    def test_stats(self):
        # Generate some sales data
        # Add stock
        self.seller.add_stock_level(self.seller_id, self.store_id, self.book_id, 100) 
        
        # Buy book
        buy_book_info_list = [(self.book_id, 2)]
        code, order_id = self.buyer.new_order(self.store_id, buy_book_info_list)
        assert code == 200
        
        # Pay
        code = self.buyer.add_funds(1000000)
        assert code == 200
        code = self.buyer.payment(order_id)
        assert code == 200
        
        # Get Stats
        url = urljoin(self.url_prefix, "seller/stats")
        headers = {"token": self.seller.token}
        params = {
            "user_id": self.seller_id,
            "store_id": self.store_id
        }
        r = requests.get(url, headers=headers, params=params)
        assert r.status_code == 200
        stats = r.json()["stats"]
        
        assert stats["total_orders"] == 1
        assert stats["total_revenue"] > 0
        assert len(stats["top_books"]) == 1
        assert stats["top_books"][0]["book_id"] == self.book_id

    def test_cart(self):
        # 1. Add to Cart
        url = urljoin(self.url_prefix, "buyer/cart")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "store_id": self.store_id,
            "book_id": self.book_id,
            "count": 2,
            "action": "add"
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200

        # 2. Get Cart
        url_get = urljoin(self.url_prefix, "buyer/cart")
        params = {"user_id": self.buyer_id}
        r = requests.get(url_get, headers=headers, params=params)
        assert r.status_code == 200
        cart = r.json()["cart"]
        assert len(cart) == 1
        assert cart[0]["count"] == 2
        
        # 3. Update Cart
        data["count"] = 5
        data["action"] = "update"
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        
        r = requests.get(url_get, headers=headers, params=params)
        cart = r.json()["cart"]
        assert cart[0]["count"] == 5

        # 4. Remove Item
        r = requests.delete(url, headers=headers, json=data)
        assert r.status_code == 200
        
        r = requests.get(url_get, headers=headers, params=params)
        cart = r.json()["cart"]
        assert len(cart) == 0

    def test_cart_error(self):
        # Test non-exist store
        url = urljoin(self.url_prefix, "buyer/cart")
        headers = {"token": self.buyer.token}
        data = {
            "user_id": self.buyer_id,
            "store_id": "bad_store",
            "book_id": self.book_id,
            "count": 1
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code != 200

    def test_coupon(self):
        from datetime import datetime, timedelta
        # 1. Seller Create Coupon (Threshold 100, Discount 10)
        url = urljoin(self.url_prefix, "seller/create_coupon")
        headers = {"token": self.seller.token}
        end_time = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "user_id": self.seller_id,
            "store_id": self.store_id,
            "name": "Test Coupon",
            "threshold": 100,
            "discount": 10,
            "stock": 5,
            "end_time": end_time
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        coupon_id = r.json()["coupon_id"]

        # 2. Buyer Collect Coupon
        url = urljoin(self.url_prefix, "buyer/coupon")
        headers_b = {"token": self.buyer.token}
        data_b = {
            "user_id": self.buyer_id,
            "coupon_id": coupon_id
        }
        r = requests.post(url, headers=headers_b, json=data_b)
        assert r.status_code == 200

        # 3. Buyer Check Coupon
        url_get = urljoin(self.url_prefix, "buyer/coupon")
        params = {"user_id": self.buyer_id}
        r = requests.get(url_get, headers=headers_b, params=params)
        assert r.status_code == 200
        coupons = r.json()["coupons"]
        assert len(coupons) == 1
        user_coupon_id = coupons[0]["id"]

        # 4. Use Coupon (Order > 100)
        # Add stock first
        self.seller.add_stock_level(self.seller_id, self.store_id, self.book_id, 10)
        
        buy_list = [{"id": self.book_id, "count": 2}] 
        
        url_order = urljoin(self.url_prefix, "buyer/new_order")
        data_order = {
            "user_id": self.buyer_id,
            "store_id": self.store_id,
            "books": buy_list,
            "coupon_id": user_coupon_id
        }
        
        # Ensure buyer has funds (Price might be high)
        self.buyer.add_funds(1000000)
        
        r = requests.post(url_order, headers=headers_b, json=data_order)
        assert r.status_code == 200
        
        # 5. Verify Coupon Used
        r = requests.get(url_get, headers=headers_b, params=params)
        coupons = r.json()["coupons"]
        assert len(coupons) == 0

    def test_coupon_error(self):
        from datetime import datetime, timedelta
        # 1. Create expired coupon
        url = urljoin(self.url_prefix, "seller/create_coupon")
        headers = {"token": self.seller.token}
        # Yesterday
        end_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        data = {
            "user_id": self.seller_id,
            "store_id": self.store_id,
            "name": "Expired Coupon",
            "threshold": 10,
            "discount": 1,
            "stock": 5,
            "end_time": end_time
        }
        r = requests.post(url, headers=headers, json=data)
        assert r.status_code == 200
        coupon_id = r.json()["coupon_id"]

        # 2. Collect expired coupon (should fail)
        url_col = urljoin(self.url_prefix, "buyer/coupon")
        headers_b = {"token": self.buyer.token}
        data_b = {"user_id": self.buyer_id, "coupon_id": coupon_id}
        r = requests.post(url_col, headers=headers_b, json=data_b)
        assert r.status_code != 200

        # 3. Use coupon with insufficient threshold
        # Create high threshold coupon
        end_time = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        data["end_time"] = end_time
        data["threshold"] = 100000000 # Very high
        data["name"] = "High Threshold"
        r = requests.post(url, headers=headers, json=data)
        high_cid = r.json()["coupon_id"]
        
        # Collect
        data_b["coupon_id"] = high_cid
        requests.post(url_col, headers=headers_b, json=data_b)
        
        # Get user coupon id
        r = requests.get(url_col, headers=headers_b, params={"user_id": self.buyer_id})
        high_uc_id = None
        for c in r.json()["coupons"]:
            if c["coupon_id"] == high_cid:
                high_uc_id = c["id"]
                break
        
        assert high_uc_id is not None

        # Try order
        buy_list = [{"id": self.book_id, "count": 1}]
        url_order = urljoin(self.url_prefix, "buyer/new_order")
        data_order = {
            "user_id": self.buyer_id,
            "store_id": self.store_id,
            "books": buy_list,
            "coupon_id": high_uc_id
        }
        r = requests.post(url_order, headers=headers_b, json=data_order)
        assert r.status_code != 200 # Threshold not met
