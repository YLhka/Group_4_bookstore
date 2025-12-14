import logging
import os
import threading
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from be.model.db_schema import init_db_schema
from be.model.blob_store import get_blob_store # Ensure Blob Store is initialized

class Store:
    def __init__(self, db_path):
        # Priority: 
        # 1. Environment Variable POSTGRES_URL
        # 2. Hardcoded Default for Project (if needed)
        # 3. Fallback to SQLite (for local dev/test without Postgres)
        
        self.db_url = os.environ.get("POSTGRES_URL")
        
        # Example Postgres URL: "postgresql://user:password@localhost:5432/bookstore"
        
        if not self.db_url:
            # Fallback to SQLite
            db_file = os.path.join(db_path, "be_final.db")
            self.db_url = f"sqlite:///{db_file}"
            logging.info(f"Using SQLite database at {self.db_url}")
        else:
            logging.info(f"Using PostgreSQL database at {self.db_url}")

        # Create engine
        connect_args = {}
        if self.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
        self.engine = create_engine(self.db_url, connect_args=connect_args, echo=False)
        
        # Create tables (Safe to call, will skip if exist)
        self.init_tables()
        
        # Session factory
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
        # Initialize Blob Store (NoSQL) connection
        # This is lightweight, just establishing the client
        get_blob_store() 

    def init_tables(self):
        try:
            init_db_schema(self.engine)
        except Exception as e:
            logging.error(e)

    def get_db_session(self):
        return self.Session()

database_instance: Store = None
init_completed_event = threading.Event()

def init_database(db_path):
    global database_instance
    database_instance = Store(db_path)

def get_db_conn():
    # Kept for compatibility name, but returns a Session
    global database_instance
    return database_instance.get_db_session()
