# database.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from .schemas import Base # Import Base from schemas

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL found in environment variables. Please check your .env file.")

# The engine is the central point of communication with the database
engine = create_engine(DATABASE_URL)

# SessionLocal class is a factory for creating new Session objects
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_db_and_tables():
    """
    Creates all database tables based on the SQLAlchemy models (schemas).
    """
    Base.metadata.create_all(bind=engine)

def get_db():
    """
    FastAPI dependency to get a DB session for each request.
    Yields a session and ensures it's closed after the request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()