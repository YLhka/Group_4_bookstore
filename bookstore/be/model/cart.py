from sqlalchemy.exc import SQLAlchemyError
from be.model import db_conn
from be.model import error
from be.model.db_schema import ShoppingCart

class Cart(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_item(self, user_id: str, store_id: str, book_id: str, count: int, action: str = "add") -> (int, str):
        """
        action: "add" (increment) or "update" (set specific value)
        """
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)
            
            item = self.conn.query(ShoppingCart).filter_by(
                user_id=user_id, 
                store_id=store_id, 
                book_id=book_id
            ).with_for_update().first()
            
            if item:
                if action == "add":
                    item.count += count
                else:
                    item.count = count
            else:
                item = ShoppingCart(
                    user_id=user_id, 
                    store_id=store_id, 
                    book_id=book_id, 
                    count=count
                )
                self.conn.add(item)
            
            self.conn.commit()
            return 200, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)
        except Exception as e:
            self.conn.rollback()
            return 530, str(e)

    def remove_item(self, user_id: str, store_id: str, book_id: str) -> (int, str):
        try:
            item = self.conn.query(ShoppingCart).filter_by(
                user_id=user_id, 
                store_id=store_id, 
                book_id=book_id
            ).first()
            
            if item:
                self.conn.delete(item)
                self.conn.commit()
            return 200, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)

    def clear_cart(self, user_id: str) -> (int, str):
        try:
            self.conn.query(ShoppingCart).filter_by(user_id=user_id).delete()
            self.conn.commit()
            return 200, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)

    # Backward-compatible alias for legacy tests
    def delete_item(self, user_id: str, book_id: str, store_id: str) -> (int, str):
        return self.remove_item(user_id, store_id, book_id)

    def get_cart(self, user_id: str):
        try:
            items = self.conn.query(ShoppingCart).filter_by(user_id=user_id).all()
            res = []
            for item in items:
                res.append({
                    "store_id": item.store_id,
                    "book_id": item.book_id,
                    "count": item.count
                })
            return 200, "ok", res
        except SQLAlchemyError as e:
            return 528, str(e), []

