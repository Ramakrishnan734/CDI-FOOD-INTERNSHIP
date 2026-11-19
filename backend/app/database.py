# backend/app/database.py

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
import os

# Database URL format:
# postgresql+psycopg2://username:password@host:port/database_name
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://rk@localhost:5432/cdi_food_db"
)

# Engine = the actual connection pool to PostgreSQL
engine: Engine = create_engine(
    DATABASE_URL,
    echo=True,        # logs every SQL query — helpful during development
    future=True       # use SQLAlchemy 2.0 style
)

def get_engine() -> Engine:
    return engine