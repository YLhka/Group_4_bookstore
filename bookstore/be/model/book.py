from sqlalchemy import or_
from be.model import db_conn
from be.model.db_schema import Book as BookModel, StoreBook
from be.model.blob_store import get_blob_store

class Book(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def get_book_info(self, book_id: str):
        # 1. Get Core Data from SQL
        book = self.conn.query(BookModel).filter_by(id=book_id).first()
        if book:
            book_dict = {c.name: getattr(book, c.name) for c in book.__table__.columns}
            
            # 2. Get Blob Data from NoSQL
            blob_data = get_blob_store().get_book_blob(book_id)
            
            # 3. Merge
            book_dict.update(blob_data)
            return book_dict
        return None

    def search_by_title(self, keyword: str, limit: int = 10, skip: int = 0):
        # Basic search (legacy support)
        query = self.conn.query(BookModel).filter(BookModel.title.like(f"%{keyword}%"))
        books = query.offset(skip).limit(limit).all()
        return self._enrich_books(books)

    def search_in_store(self, store_id: str, keyword: str, limit: int = 10, skip: int = 0):
        # Search books within a specific store
        query = self.conn.query(BookModel).join(StoreBook).filter(StoreBook.store_id == store_id).order_by(BookModel.id)
        if keyword:
            query = query.filter(BookModel.title.like(f"%{keyword}%"))
            
        books = query.offset(skip).limit(limit).all()
        # Manually inject store_id for legacy test compatibility
        res = self._enrich_books(books)
        for b in res:
            b["store_id"] = store_id
        return res

    def search_complex(self, keyword: str, limit: int = 10, skip: int = 0):
        # Full text search simulation using LIKE on multiple columns
        # Note: Content/Intro search moved to NoSQL is possible, but for now we search SQL fields
        if not keyword:
            query = self.conn.query(BookModel).order_by(BookModel.id)
        else:
            term = f"%{keyword}%"
            query = self.conn.query(BookModel).filter(
                or_(
                    BookModel.title.like(term),
                    BookModel.author.like(term),
                    # BookModel.book_intro.like(term), # Removed from SQL
                    BookModel.tags.like(term)
                )
            ).order_by(BookModel.id)
            
        books = query.offset(skip).limit(limit).all()
        total = query.count()
        return self._enrich_books(books), total

    def _enrich_books(self, books):
        # Helper to merge SQL books with NoSQL data (optional for list view to save bandwidth)
        # For list view, we might NOT want full content. 
        # Let's just return SQL data for lists to be efficient.
        return [{c.name: getattr(b, c.name) for c in b.__table__.columns} for b in books]

    def add_review(self, user_id: str, book_id: str, content: str, rating: int):
        from be.model.db_schema import Review
        try:
            review = Review(
                user_id=user_id,
                book_id=book_id,
                content=content,
                rating=rating
            )
            self.conn.add(review)
            self.conn.commit()
            return True, "ok"
        except Exception as e:
            self.conn.rollback()
            return False, str(e)

    def get_reviews(self, book_id: str):
        from be.model.db_schema import Review
        try:
            reviews = self.conn.query(Review).filter_by(book_id=book_id).order_by(Review.created_at.desc()).all()
            res = []
            for r in reviews:
                res.append({
                    "user_id": r.user_id,
                    "content": r.content,
                    "rating": r.rating,
                    "created_at": r.created_at.timestamp() if r.created_at else 0
                })
            return res
        except Exception as e:
            return []
