from be.model import store
from be.model.db_schema import User, Store as StoreModel, StoreBook

class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        user = self.conn.query(User).filter_by(user_id=user_id).first()
        return user is not None

    def book_id_exist(self, store_id, book_id):
        # Checks if a specific book exists in a specific store (Inventory check)
        store_book = self.conn.query(StoreBook).filter_by(store_id=store_id, book_id=book_id).first()
        return store_book is not None

    def store_id_exist(self, store_id):
        store_obj = self.conn.query(StoreModel).filter_by(store_id=store_id).first()
        return store_obj is not None
