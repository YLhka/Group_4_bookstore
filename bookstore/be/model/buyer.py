import uuid
import time
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from be.model import db_conn
from be.model import error
from be.model.db_schema import User, Store as StoreModel, StoreBook, Order, OrderDetail, Book, UserCoupon, Coupon
from be.model.user import User as UserManager

class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(self, user_id: str, store_id: str, books: list, coupon_id: int = None) -> (bool, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return False, error.error_non_exist_user_id(user_id)[1], ""
            if not self.store_id_exist(store_id):
                return False, error.error_non_exist_store_id(store_id)[1], ""
            
            total_price = 0
            order_details = []
            
            # Prepare data and check stock
            for item in books:
                book_id = item.get("id")
                count = int(item.get("count", 0))
                
                if count <= 0:
                    continue
                
                store_book = self.conn.query(StoreBook).filter_by(store_id=store_id, book_id=book_id).with_for_update().first()
                
                if not store_book:
                    self.conn.rollback()
                    return False, error.error_non_exist_book_id(book_id)[1], ""
                
                if store_book.stock_level < count:
                    self.conn.rollback()
                    return False, error.error_stock_level_low(book_id)[1], ""
                
                store_book.stock_level -= count
                price = store_book.price
                total_price += price * count
                
                order_details.append({
                    "book_id": book_id,
                    "count": count,
                    "price": price
                })

            if not order_details:
                 return False, "no valid books", ""

            # --- Coupon Logic ---
            if coupon_id:
                user_coupon = self.conn.query(UserCoupon).filter_by(id=coupon_id, user_id=user_id).with_for_update().first()
                if not user_coupon:
                    self.conn.rollback()
                    return False, "coupon not found", ""
                
                if user_coupon.status != "unused":
                    self.conn.rollback()
                    return False, "coupon already used", ""
                
                coupon = self.conn.query(Coupon).filter_by(id=user_coupon.coupon_id).first()
                if not coupon:
                    self.conn.rollback()
                    return False, "invalid coupon", ""
                
                if coupon.store_id != store_id:
                    self.conn.rollback()
                    return False, "coupon not for this store", ""
                
                if coupon.end_time < datetime.now():
                    self.conn.rollback()
                    return False, "coupon expired", ""
                
                if total_price < coupon.threshold:
                    self.conn.rollback()
                    return False, f"total price {total_price} less than threshold {coupon.threshold}", ""
                
                # Apply Discount
                total_price = max(0, total_price - coupon.discount)
                
                # Mark as used (will commit later)
                user_coupon.status = "used"
            
            # --- End Coupon Logic ---

            # Create Order
            order_id = f"order_{uuid.uuid4().hex}"
            new_order = Order(
                order_id=order_id,
                user_id=user_id,
                store_id=store_id,
                status="unpaid", 
                total_price=total_price,
                created_at=datetime.now()
            )
            self.conn.add(new_order)
            self.conn.flush() 
            
            # Link coupon to order if used
            if coupon_id and user_coupon:
                user_coupon.order_id = order_id

            for detail in order_details:
                new_detail = OrderDetail(
                    order_id=order_id,
                    book_id=detail["book_id"],
                    count=detail["count"],
                    price=detail["price"]
                )
                self.conn.add(new_detail)
            
            self.conn.commit()
            return True, "ok", order_id

        except SQLAlchemyError as e:
            self.conn.rollback()
            import logging
            logging.error(f"New Order SQL Error: {e}")
            return False, str(e), ""
        except Exception as e:
            self.conn.rollback()
            import logging
            logging.error(f"New Order Generic Error: {e}")
            return False, str(e), ""

    def payment(self, user_id: str, order_id: str, password: str) -> (bool, str):
        try:
            order = self.conn.query(Order).filter_by(order_id=order_id).with_for_update().first()
            if not order:
                 return False, "order not found"
            
            if order.user_id != user_id:
                return False, "authorization fail"
                
            if order.status != "unpaid":
                return False, "order status invalid"
            
            um = UserManager()
            code, msg = um.check_password(user_id, password)
            if code != 200:
                return False, "authorization fail"
            
            total_price = order.total_price
            
            buyer = self.conn.query(User).filter_by(user_id=user_id).with_for_update().first()
            if buyer.balance < total_price:
                self.conn.rollback()
                return False, "not sufficient funds"
            
            buyer.balance -= total_price
            
            store = self.conn.query(StoreModel).filter_by(store_id=order.store_id).first()
            if store and store.user_id:
                seller = self.conn.query(User).filter_by(user_id=store.user_id).with_for_update().first()
                if seller:
                    seller.balance += total_price
            
            order.status = "paid"
            self.conn.commit()
            return True, "ok"

        except SQLAlchemyError as e:
            self.conn.rollback()
            return False, str(e)
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    def add_funds(self, user_id: str, password: str, add_value: int) -> (bool, str):
        try:
            um = UserManager()
            code, msg = um.check_password(user_id, password)
            if code != 200:
                return False, msg 

            if add_value <= 0:
                return False, "invalid add_value"

            user = self.conn.query(User).filter_by(user_id=user_id).with_for_update().first()
            user.balance += add_value
            self.conn.commit()
            return True, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return False, str(e)
        except Exception as e:
            self.conn.rollback()
            return False, str(e)
