from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from be.model import db_conn
from be.model import error
from be.model.db_schema import Coupon, UserCoupon, Store as StoreModel

class CouponManager(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def create_coupon(self, user_id: str, store_id: str, name: str, threshold: int, discount: int, stock: int, end_time: datetime):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            
            # Verify user is store owner
            store = self.conn.query(StoreModel).filter_by(store_id=store_id).first()
            if store.user_id != user_id:
                return 401, "user is not the owner of this store", 0

            coupon = Coupon(
                store_id=store_id,
                name=name,
                threshold=threshold,
                discount=discount,
                stock=stock,
                end_time=end_time
            )
            self.conn.add(coupon)
            self.conn.commit()
            return 200, "ok", coupon.id
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e), 0

    def collect_coupon(self, user_id: str, coupon_id: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            
            # Transaction: check stock and decrease
            coupon = self.conn.query(Coupon).filter_by(id=coupon_id).with_for_update().first()
            if not coupon:
                return 404, "coupon not found"
            
            if coupon.stock <= 0:
                self.conn.rollback()
                return 400, "coupon out of stock"
            
            if coupon.end_time < datetime.now():
                self.conn.rollback()
                return 400, "coupon expired"

            # Check if user already has this coupon (optional logic, let's allow multiple)
            # For now, let's say unlimited collection per user for simplicity, or limit 1
            # existing = self.conn.query(UserCoupon).filter_by(user_id=user_id, coupon_id=coupon_id, status="unused").first()
            # if existing: ...

            coupon.stock -= 1
            user_coupon = UserCoupon(
                user_id=user_id,
                coupon_id=coupon_id,
                status="unused"
            )
            self.conn.add(user_coupon)
            self.conn.commit()
            return 200, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)

    def get_available_coupons(self, user_id: str, store_id: str = None):
        try:
            query = self.conn.query(UserCoupon).join(Coupon).filter(
                UserCoupon.user_id == user_id,
                UserCoupon.status == "unused",
                Coupon.end_time > datetime.now()
            )
            if store_id:
                query = query.filter(Coupon.store_id == store_id)
            
            res = []
            for uc in query.all():
                res.append({
                    "id": uc.id,
                    "coupon_id": uc.coupon_id,
                    "name": uc.coupon.name,
                    "threshold": uc.coupon.threshold,
                    "discount": uc.coupon.discount,
                    "store_id": uc.coupon.store_id
                })
            return 200, "ok", res
        except SQLAlchemyError as e:
            return 528, str(e), []

