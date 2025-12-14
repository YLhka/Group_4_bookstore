import time
from sqlalchemy.exc import SQLAlchemyError
from be.model import db_conn
from be.model.db_schema import Order as OrderModel, OrderDetail, StoreBook

class Order(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def deliver_order(self, store_id: str, order_id: str):
        try:
            order = self.conn.query(OrderModel).filter_by(order_id=order_id).first()
            if not order:
                return False, "order not found"
            if order.store_id != store_id:
                return False, "order not belong to this store"
            if order.status != "paid":
                return False, "order status not paid"
            
            order.status = "delivering"
            self.conn.commit()
            return True, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return False, str(e)

    def receive_order(self, buyer_id: str, order_id: str):
        try:
            order = self.conn.query(OrderModel).filter_by(order_id=order_id).first()
            if not order:
                return False, "order not found"
            if order.user_id != buyer_id:
                return False, "order not belong to user"
            if order.status != "delivering":
                return False, "order status not delivering"
            
            order.status = "received"
            self.conn.commit()
            return True, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return False, str(e)

    def list_orders(self, buyer_id: str, limit: int = 20, skip: int = 0):
        try:
            orders_query = self.conn.query(OrderModel).filter_by(user_id=buyer_id).order_by(OrderModel.created_at.desc())
            orders = orders_query.offset(skip).limit(limit).all()
            
            result = []
            for o in orders:
                items = []
                for detail in o.details:
                    items.append({
                        "book_id": detail.book_id,
                        "count": detail.count,
                        "price": detail.price
                        # Title/Author would require join with Book, let's skip for perf or add if needed
                    })
                
                result.append({
                    "order_id": o.order_id,
                    "buyer_id": o.user_id,
                    "store_id": o.store_id,
                    "status": o.status,
                    "total_price": o.total_price,
                    "created_time": o.created_at.timestamp() if o.created_at else 0,
                    "items": items
                })
            return result
        except SQLAlchemyError as e:
            return []

    def cancel_order(self, buyer_id: str, order_id: str):
        try:
            order = self.conn.query(OrderModel).filter_by(order_id=order_id).first()
            if not order:
                return False, "order not found"
            if order.user_id != buyer_id:
                return False, "order not belong to user"
            # Tests expect only unpaid orders can be cancelled by buyer
            if order.status != "unpaid":
                return False, "order status not cancelable"
            
            # Restore stock for each item
            for detail in order.details:
                store_book = self.conn.query(StoreBook).filter_by(store_id=order.store_id, book_id=detail.book_id).with_for_update().first()
                if store_book:
                    store_book.stock_level += detail.count

            order.status = "canceled"
            self.conn.commit()
            return True, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return False, str(e)

    def cancel_timeout_orders(self, timeout_seconds: int = 1800):
        # Implementation for timeout cancellation
        from datetime import datetime, timedelta
        
        try:
            cutoff_time = datetime.now() - timedelta(seconds=timeout_seconds)
            # Find unpaid orders created before cutoff_time
            orders_to_cancel = self.conn.query(OrderModel).filter(
                OrderModel.status == "unpaid",
                OrderModel.created_at < cutoff_time
            ).all()
            
            # Extract IDs to avoid session conflict during iteration and commit
            cancel_list = [(o.user_id, o.order_id) for o in orders_to_cancel]

            count = 0
            for uid, oid in cancel_list:
                # Use self.cancel_order logic to ensure stock is restored
                # Note: cancel_order commits transaction, so we do it one by one
                ok, msg = self.cancel_order(uid, oid)
                if ok:
                    count += 1
            
            return count
        except Exception as e:
            return 0

