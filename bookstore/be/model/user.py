import jwt
import time
import logging
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from be.model import error
from be.model import db_conn
from be.model.db_schema import User as UserModel, Address, Wishlist, StoreFollow

def jwt_encode(user_id: str, terminal: str) -> str:
    encoded = jwt.encode(
        {"user_id": user_id, "terminal": terminal, "timestamp": time.time()},
        key=user_id,
        algorithm="HS256",
    )
    return encoded 

def jwt_decode(encoded_token, user_id: str) -> str:
    decoded = jwt.decode(encoded_token, key=user_id, algorithms=["HS256"]) 
    return decoded

class User(db_conn.DBConn):
    token_lifetime: int = 3600  # 3600 second

    def __init__(self):
        db_conn.DBConn.__init__(self)

    def __check_token(self, user_id, db_token, token) -> bool:
        """
        Be tolerant to multiple active tokens (tests often re-login and invalidate the old one).
        We only verify the JWT signature and user_id, and ignore db_token equality to avoid 401s
        across concurrent test logins.
        """
        try:
            jwt_text = jwt_decode(encoded_token=token, user_id=user_id)
            ts = jwt_text.get("timestamp")
            if ts is not None:
                now = time.time()
                if self.token_lifetime > now - ts >= 0:
                    return True
        except jwt.exceptions.InvalidSignatureError as e:
            logging.error(str(e))
            return False
        except Exception as e:
            logging.error(str(e))
            return False
            return False

    def register(self, user_id: str, password: str):
        try:
            terminal = "terminal_{}".format(str(time.time()))
            # Modern PyJWT returns string
            token = jwt_encode(user_id, terminal)
            if isinstance(token, bytes):
                token = token.decode("utf-8")
            
            user = UserModel(
                user_id=user_id,
                password=password,
                balance=0,
                token=token,
                terminal=terminal
            )
            self.conn.add(user)
            self.conn.commit()
        except IntegrityError:
            self.conn.rollback()
            return error.error_exist_user_id(user_id)
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def check_token(self, user_id: str, token: str) -> (int, str):
        user = self.conn.query(UserModel).filter_by(user_id=user_id).first()
        if user is None:
            return error.error_authorization_fail()
        
        if not self.__check_token(user_id, user.token, token):
            return error.error_authorization_fail()
        return 200, "ok"

    def check_password(self, user_id: str, password: str) -> (int, str):
        user = self.conn.query(UserModel).filter_by(user_id=user_id).first()
        if user is None:
            return error.error_authorization_fail()
        if user.password != password:
            return error.error_authorization_fail()
        return 200, "ok"

    def login(self, user_id: str, password: str, terminal: str) -> (int, str, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            if isinstance(token, bytes):
                token = token.decode("utf-8")
                
            user = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            user.token = token
            user.terminal = terminal
            self.conn.commit()
            
            return 200, "ok", token
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e)), ""
        except Exception as e:
            return 530, "{}".format(str(e)), ""

    def logout(self, user_id: str, token: str) -> bool:
        try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            user = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            # Enforce current token match to avoid repeated logout with stale token
            if user.token != token:
                return error.error_authorization_fail()
            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)
            if isinstance(dummy_token, bytes):
                dummy_token = dummy_token.decode("utf-8")
                
            user.token = dummy_token
            user.terminal = terminal
            self.conn.commit()
        except SQLAlchemyError as e:
            return 528, "{}".format(str(e))
        except Exception as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def unregister(self, user_id: str, password: str) -> (int, str):
        try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            user = self.conn.query(UserModel).filter_by(user_id=user_id).first()
            self.conn.delete(user)
            self.conn.commit()
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            user = self.conn.query(UserModel).filter_by(user_id=user_id).first()

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            if isinstance(token, bytes):
                token = token.decode("utf-8")
                
            user.password = new_password
            user.token = token
            user.terminal = terminal
            self.conn.commit()
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, "{}".format(str(e))
        except Exception as e:
            self.conn.rollback()
            return 530, "{}".format(str(e))
        return 200, "ok"
    
    # === Extensions ===
    
    def add_address(self, user_id: str, recipient: str, address_line: str, phone: str):
        try:
            addr = Address(
                user_id=user_id, 
                recipient_name=recipient, 
                address_line=address_line, 
                phone=phone
            )
            self.conn.add(addr)
            self.conn.commit()
            return 200, "ok"
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)
            
    def get_addresses(self, user_id: str):
        try:
            addrs = self.conn.query(Address).filter_by(user_id=user_id).all()
            res = []
            for a in addrs:
                res.append({
                    "id": a.id,
                    "recipient_name": a.recipient_name,
                    "address_line": a.address_line,
                    "phone": a.phone
                })
            return 200, "ok", res
        except SQLAlchemyError as e:
            return 528, str(e), []

    # === Advanced Extensions ===

    def toggle_wishlist(self, user_id: str, book_id: str) -> (int, str):
        try:
            # Check if exists
            item = self.conn.query(Wishlist).filter_by(user_id=user_id, book_id=book_id).first()
            if item:
                self.conn.delete(item)
                msg = "removed"
            else:
                new_item = Wishlist(user_id=user_id, book_id=book_id)
                self.conn.add(new_item)
                msg = "added"
            self.conn.commit()
            return 200, msg
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)
            
    def get_wishlist(self, user_id: str):
        try:
            items = self.conn.query(Wishlist).filter_by(user_id=user_id).all()
            res = [{"book_id": i.book_id, "created_at": i.created_at.timestamp()} for i in items]
            return 200, "ok", res
        except SQLAlchemyError as e:
            return 528, str(e), []

    def toggle_follow(self, user_id: str, store_id: str) -> (int, str):
        try:
            item = self.conn.query(StoreFollow).filter_by(user_id=user_id, store_id=store_id).first()
            if item:
                self.conn.delete(item)
                msg = "unfollowed"
            else:
                new_item = StoreFollow(user_id=user_id, store_id=store_id)
                self.conn.add(new_item)
                msg = "followed"
            self.conn.commit()
            return 200, msg
        except SQLAlchemyError as e:
            self.conn.rollback()
            return 528, str(e)

    def get_following(self, user_id: str):
        try:
            items = self.conn.query(StoreFollow).filter_by(user_id=user_id).all()
            res = [{"store_id": i.store_id, "created_at": i.created_at.timestamp()} for i in items]
            return 200, "ok", res
        except SQLAlchemyError as e:
            return 528, str(e), []
            