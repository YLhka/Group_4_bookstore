import json
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import func, desc
from be.model import error
from be.model import db_conn
from be.model.db_schema import Store as StoreModel, StoreBook, Book, Order, OrderDetail
from be.model.blob_store import get_blob_store

class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(
        self,
        user_id: str,
        store_id: str,
        book_id: str,
        book_json_str: str,
        stock_level: int,
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            book_info = json.loads(book_json_str)
            
            # 1. Ensure Book exists in global catalog (SQL)
            book = self.conn.query(Book).filter_by(id=book_id).first()
            if not book:
                price = book_info.get("price", 0)
                if isinstance(price, str):
                    try:
                        price = int(price)
                    except:
                        price = 0
                        
                # Core data -> SQL
                new_book = Book(
                    id=book_id,
                    title=book_info.get("title", "Untitled"),
                    author=book_info.get("author"),
                    publisher=book_info.get("publisher"),
                    original_title=book_info.get("original_title"),
                    translator=book_info.get("translator"),
                    pub_year=book_info.get("pub_year"),
                    pages=book_info.get("pages"),
                    price=price,
                    currency_unit=book_info.get("currency_unit"),
                    binding=book_info.get("binding"),
                    isbn=book_info.get("isbn"),
                    tags=json.dumps(book_info.get("tags", [])) if isinstance(book_info.get("tags"), list) else book_info.get("tags", "")
                )
                self.conn.add(new_book)
                self.conn.flush()
                
                # Blob data -> NoSQL (MongoDB)
                get_blob_store().put_book_blob(
                    book_id=book_id,
                    content=book_info.get("content", ""),
                    book_intro=book_info.get("book_intro", ""),
                    author_intro=book_info.get("author_intro", "")
                )

            # 2. Add to Store Inventory (StoreBook)
            selling_price = book_info.get("price", 0) 
            
            store_book = StoreBook(
                store_id=store_id,
                book_id=book_id,
                stock_level=stock_level,
                price=selling_price
            )
            self.conn.add(store_book)
            self.conn.commit()
            
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def add_stock_level(
        self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if add_stock_level <= 0:
                return 530, "invalid stock level"
            
            store_book = self.conn.query(StoreBook).filter_by(store_id=store_id, book_id=book_id).first()
            if not store_book:
                return error.error_non_exist_book_id(book_id)

            store_book.stock_level += add_stock_level
            self.conn.commit()
            
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            
            store = StoreModel(
                store_id=store_id,
                user_id=user_id
            )
            self.conn.add(store)
            self.conn.commit()
            
        except SQLAlchemyError as e:
            self.conn.rollback()
            import logging
            logging.error(f"Create Store SQL Error: {e}")
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            import logging
            logging.error(f"Create Store Generic Error: {e}")
            return 530, "{}".format(str(e))
        return 200, "ok"

    # === Extension: Sales Statistics ===
    def get_store_stats(self, user_id: str, store_id: str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            
            # 1. Total Sales & Order Count
            # Query Orders belonging to this store
            stats = self.conn.query(
                func.count(Order.order_id).label("total_orders"),
                func.sum(Order.total_price).label("total_revenue")
            ).filter_by(store_id=store_id, status="paid").first()
            
            total_orders = stats.total_orders or 0
            total_revenue = stats.total_revenue or 0
            
            # 2. Top Selling Books (Aggregation on OrderDetail)
            # Join OrderDetail -> Order (to filter by store and paid status)
            top_books_query = self.conn.query(
                OrderDetail.book_id,
                func.sum(OrderDetail.count).label("total_sold")
            ).join(Order).filter(
                Order.store_id == store_id,
                Order.status == "paid"
            ).group_by(OrderDetail.book_id).order_by(desc("total_sold")).limit(5).all()
            
            top_books = [{"book_id": b.book_id, "total_sold": b.total_sold} for b in top_books_query]
            
            return 200, "ok", {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "top_books": top_books
            }
            
        except SQLAlchemyError as e:
            return 528, str(e), {}