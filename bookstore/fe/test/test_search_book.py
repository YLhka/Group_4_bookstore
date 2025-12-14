import pytest
import uuid
from fe.access.new_seller import register_new_seller
from fe.access.new_buyer import register_new_buyer
from fe.access import book as bookdb
from fe import conf

class TestSearchBook:
    @pytest.fixture(autouse=True)
    def prepare(self):
        # Prepare Seller & Store
        self.seller_id = "test_search_s_{}".format(str(uuid.uuid1()))
        self.store_id = "test_search_st_{}".format(str(uuid.uuid1()))
        self.seller = register_new_seller(self.seller_id, self.seller_id)
        self.seller.create_store(self.store_id)
        
        # Prepare Buyer
        self.buyer_id = "test_search_b_{}".format(str(uuid.uuid1()))
        self.buyer = register_new_buyer(self.buyer_id, self.buyer_id)
        
        # Add a specific book
        self.book_db = bookdb.BookDB(conf.Use_Large_DB)
        self.book_list = self.book_db.get_book_info(0, 1)
        self.book = self.book_list[0]
        self.seller.add_book(self.store_id, 10, self.book)
        
        yield

    def test_search_in_store(self):
        # 1. Search by title in specific store
        keyword = self.book.title[:2] # Partial match
        code, res = self.buyer.search_book(keyword, self.store_id, 1, 10)
        assert code == 200
        # Should find at least one
        found = False
        for b in res:
            if b['id'] == self.book.id:
                found = True
                break
        assert found

    def test_search_global(self):
        # 2. Search globally (no store_id)
        keyword = self.book.title
        code, res = self.buyer.search_book(keyword, None, 1, 10)
        assert code == 200
        assert len(res) > 0

    def test_search_pagination(self):
        # 3. Test pagination logic
        # Add another book to ensure we have data
        book2 = self.book_db.get_book_info(1, 1)[0]
        self.seller.add_book(self.store_id, 10, book2)
        
        # Page 1, Limit 1
        code, res1 = self.buyer.search_book("", self.store_id, 1, 1)
        assert code == 200
        assert len(res1) == 1
        
        # Page 2, Limit 1
        code, res2 = self.buyer.search_book("", self.store_id, 2, 1)
        assert code == 200
        assert len(res2) == 1
        
        # Should be different books
        assert res1[0]['id'] != res2[0]['id']

    def test_search_no_result(self):
        code, res = self.buyer.search_book("non_existent_keyword_xyz", self.store_id)
        assert code == 200
        assert len(res) == 0