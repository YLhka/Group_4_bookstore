from sqlalchemy import Column, String, Integer, ForeignKey, Text, DateTime, Float, create_engine, Index
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import os

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    user_id = Column(String(255), primary_key=True)
    password = Column(String(255), nullable=False)
    balance = Column(Integer, nullable=False, default=0)
    token = Column(Text)
    terminal = Column(String(255))
    
    # Relationships
    orders = relationship("Order", back_populates="user")
    reviews = relationship("Review", back_populates="user")
    addresses = relationship("Address", back_populates="user")
    store = relationship("Store", back_populates="user", uselist=False) # One user can be a seller (store owner)
    
    # New Relationships
    wishlist = relationship("Wishlist", back_populates="user")
    following = relationship("StoreFollow", back_populates="user")

class Store(Base):
    __tablename__ = 'store'
    store_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('user.user_id'))
    
    user = relationship("User", back_populates="store")
    # Inventory management
    inventory = relationship("StoreBook", back_populates="store")
    orders = relationship("Order", back_populates="store")
    
    # New Relationships
    followers = relationship("StoreFollow", back_populates="store")

class Book(Base):
    __tablename__ = 'book'
    id = Column(String(255), primary_key=True)
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255))
    publisher = Column(String(255))
    original_title = Column(String(255))
    translator = Column(String(255))
    pub_year = Column(String(20))
    pages = Column(Integer)
    price = Column(Integer) 
    currency_unit = Column(String(20))
    binding = Column(String(100))
    isbn = Column(String(20))
    
    # author_intro, book_intro, content are moved to NoSQL (BlobStore)
    
    tags = Column(Text, index=True) 
    
    stores = relationship("StoreBook", back_populates="book")
    reviews = relationship("Review", back_populates="book")
    
    # New Relationships
    wishlisted_by = relationship("Wishlist", back_populates="book")

class StoreBook(Base):
    __tablename__ = 'store_book'
    store_id = Column(String(255), ForeignKey('store.store_id'), primary_key=True)
    book_id = Column(String(255), ForeignKey('book.id'), primary_key=True)
    stock_level = Column(Integer, default=0)
    price = Column(Integer, nullable=False, index=True) 
    
    store = relationship("Store", back_populates="inventory")
    book = relationship("Book", back_populates="stores")

class Order(Base):
    __tablename__ = 'order'
    order_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), ForeignKey('user.user_id'), index=True)
    store_id = Column(String(255), ForeignKey('store.store_id'), index=True)
    status = Column(String(50), default="PENDING") 
    created_at = Column(DateTime, default=func.now())
    total_price = Column(Integer, nullable=False)
    
    __table_args__ = (
        Index('idx_order_status_created_at', 'status', 'created_at'),
    )
    
    user = relationship("User", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    details = relationship("OrderDetail", back_populates="order", cascade="all, delete-orphan")

class OrderDetail(Base):
    __tablename__ = 'order_detail'
    order_id = Column(String(255), ForeignKey('order.order_id'), primary_key=True)
    book_id = Column(String(255), ForeignKey('book.id'), primary_key=True)
    count = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False) 
    
    order = relationship("Order", back_populates="details")
    book = relationship("Book")

# === EXTENSION TABLES ===

class Review(Base):
    __tablename__ = 'review'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey('user.user_id'))
    book_id = Column(String(255), ForeignKey('book.id'), index=True)
    content = Column(Text)
    rating = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="reviews")
    book = relationship("Book", back_populates="reviews")

class Address(Base):
    __tablename__ = 'address'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey('user.user_id'))
    recipient_name = Column(String(255), nullable=False)
    address_line = Column(Text, nullable=False)
    phone = Column(String(50), nullable=False)
    
    user = relationship("User", back_populates="addresses")

class Wishlist(Base):
    __tablename__ = 'wishlist'
    user_id = Column(String(255), ForeignKey('user.user_id'), primary_key=True)
    book_id = Column(String(255), ForeignKey('book.id'), primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="wishlist")
    book = relationship("Book", back_populates="wishlisted_by")

class StoreFollow(Base):
    __tablename__ = 'store_follow'
    user_id = Column(String(255), ForeignKey('user.user_id'), primary_key=True)
    store_id = Column(String(255), ForeignKey('store.store_id'), primary_key=True)
    created_at = Column(DateTime, default=func.now())
    
    user = relationship("User", back_populates="following")
    store = relationship("Store", back_populates="followers")

class ShoppingCart(Base):
    __tablename__ = 'shopping_cart'
    user_id = Column(String(255), ForeignKey('user.user_id'), primary_key=True)
    store_id = Column(String(255), ForeignKey('store.store_id'), primary_key=True)
    book_id = Column(String(255), ForeignKey('book.id'), primary_key=True)
    count = Column(Integer, nullable=False)

class Coupon(Base):
    __tablename__ = 'coupon'
    id = Column(Integer, primary_key=True, autoincrement=True)
    store_id = Column(String(255), ForeignKey('store.store_id'), nullable=False)
    name = Column(String(255), nullable=False)
    threshold = Column(Integer, nullable=False) # 满多少 (单位: 分)
    discount = Column(Integer, nullable=False)  # 减多少 (单位: 分)
    stock = Column(Integer, default=0)          # 总库存
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=False) # 过期时间
    
    store = relationship("Store")

class UserCoupon(Base):
    __tablename__ = 'user_coupon'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey('user.user_id'), nullable=False)
    coupon_id = Column(Integer, ForeignKey('coupon.id'), nullable=False)
    status = Column(String(20), default="unused") # unused, used, expired
    order_id = Column(String(255), ForeignKey('order.order_id'), nullable=True) # 关联订单
    
    coupon = relationship("Coupon")
    user = relationship("User")

def init_db_schema(engine):
    Base.metadata.create_all(engine)

def get_base():
    return Base
