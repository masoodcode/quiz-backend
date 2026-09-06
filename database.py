import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load variables from .env file when running locally
# On Railway, these are set as environment variables in the dashboard
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL environment variable is not set. "
                       "Create a .env file in the backend/ folder with DATABASE_URL=...")

# PostgreSQL needs no extra args. SQLite needed check_same_thread=False.
# We detect which one is being used and configure accordingly.
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL — Railway/Neon may provide URLs starting with postgres://
    # SQLAlchemy requires postgresql:// so we fix it here if needed
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Open a DB session, yield it for use, then close it when done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
