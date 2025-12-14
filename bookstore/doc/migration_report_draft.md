# Bookstore Database Migration & Extension Report Draft

## 1. Migration Overview
Moved core data from NoSQL (MongoDB) to Relational Database (SQLAlchemy + PostgreSQL/SQLite).
Reasoning:
- **Data Consistency**: Transactional support is critical for Orders and Payments to prevent data inconsistency (e.g., deducting balance but failing to create order).
- **Relational Integrity**: Foreign keys ensure reference integrity between Users, Orders, and Books.
- **Complex Queries**: SQL allows efficient joining for analytics and complex search scenarios.

## 2. Database Schema Design (ER)

### Core Tables (PostgreSQL/SQLite)
- **User**: `user_id` (PK), `password`, `balance`, `token`, `terminal`.
- **Store**: `store_id` (PK), `user_id` (FK -> User).
- **Book**: `id` (PK), `title`, `price`, `tags` (Text, indexed), `isbn`. (Large text fields removed)
- **StoreBook** (Inventory): `store_id` (FK), `book_id` (FK), `stock_level`, `price`. PK is `(store_id, book_id)`.
- **Order**: `order_id` (PK), `user_id` (FK), `store_id` (FK), `status`, `total_price`, `created_at`.
- **OrderDetail**: `order_id` (FK), `book_id` (FK), `count`, `price`.

### Extension Tables (SQL)
- **Address**: `id` (PK), `user_id` (FK), `recipient_name`, `address_line`, `phone`.
- **Review**: `id` (PK), `user_id` (FK), `book_id` (FK), `content`, `rating`, `created_at`.
- **Wishlist**: `user_id` (FK), `book_id` (FK), `created_at`. (Many-to-Many User-Book)
- **StoreFollow**: `user_id` (FK), `store_id` (FK), `created_at`. (Many-to-Many User-Store)
- **ShoppingCart**: `user_id` (FK), `store_id` (FK), `book_id` (FK), `count`. (Transient Transactional Data)
- **Coupon**: `id`, `store_id`, `threshold`, `discount`, `stock`, `start_time`, `end_time`. (Business Rules)
- **UserCoupon**: `id`, `user_id`, `coupon_id`, `status`, `order_id`. (Coupon Instance)

### Blob Storage (NoSQL - MongoDB)
- **Collection**: `book_content`
- **Fields**: `book_id`, `content` (Full text), `book_intro`, `author_intro`.
- **Reasoning**: Separation of concerns. Large unstructured text is stored in NoSQL for efficiency and flexibility, while structured core data remains in SQL for integrity.

## 3. Functionality Extensions (Enrichment)

### 3.1 New Features
1.  **Address Management**: Users can add and list shipping addresses.
    - API: `POST /buyer/add_address`, `GET /buyer/get_addresses`
2.  **Book Reviews**: Users can review books.
    - API: `POST /book/review`, `GET /book/review`
3.  **Wishlist (Favorites)**: Users can save books for later.
    - API: `POST /buyer/wishlist`, `GET /buyer/wishlist`
4.  **Social (Store Follow)**: Users can follow their favorite stores.
    - API: `POST /buyer/follow`, `GET /buyer/follow`
5.  **Sales Analytics**: Sellers can view dashboard stats (Revenue, Orders, Top Selling Books).
    - API: `GET /seller/stats`
    - Implementation: Uses SQL `GROUP BY` and Aggregations (`SUM`, `COUNT`).
6.  **Complex Search**: Enhanced search supporting tags, authors, and content using SQL `ILIKE` (or FullText in future).
    - API: `GET /book/search?q=...` (Backend logic updated)
7.  **Shopping Cart**: Users can add items to cart, update quantities, and manage their pending purchases.
    - API: `POST /buyer/cart`, `GET /buyer/cart`, `DELETE /buyer/cart`
8.  **Coupon System**: Complete lifecycle management (Create, Collect, Use). Supports threshold check and expiration.
    - API: `POST /seller/create_coupon`, `POST /buyer/coupon`
    - Logic: Integrated into `new_order` for atomic validation and deduction.
9.  **Stock Restoration**: Fixed a bug where canceling an order did not restore stock. Now it does.

### 3.2 Technical Improvements
- **Hybrid Persistence**: Implemented a polyglot architecture using **SQL for transactions** and **NoSQL for blob storage**.
- **Transactions**: `new_order` and `payment` now use database transactions to ensure atomicity.
- **ORM**: Codebase refactored to use SQLAlchemy, allowing easy switching between SQLite (Dev) and PostgreSQL (Prod).
- **Code Coverage**: Comprehensive tests added for all new extensions in `fe/test/test_extensions.py`.

## 4. Testing
- Updated `fe/test/test_cancel_timeout_order.py` to support SQL backend.
- Created `fe/test/test_extensions.py` covering Address, Review, Wishlist, Follow, and Stats.
- Existing tests `fe/test/*` should pass with the new backend.

## 5. How to Run
1.  Install dependencies: `pip install -r requirements.txt`
2.  Run tests: `bash script/test.sh`
3.  **Configuration**:
    - **PostgreSQL**: Set `POSTGRES_URL` environment variable (e.g., `postgresql://user:pass@localhost/bookstore`).
    - **MongoDB**: Set `MONGO_URL` environment variable (default: `mongodb://localhost:27017`).
    - Defaults to SQLite (`be_final.db`) if Postgres is not configured.
