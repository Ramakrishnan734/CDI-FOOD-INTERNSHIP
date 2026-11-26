# backend/app/database.py

import os

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url

# Preserve the local development fallback.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://rk@localhost:5432/cdi_food_db"
)

# Railway may provide postgres:// or postgresql://.
# Normalize PostgreSQL URLs to the installed psycopg2 driver.
database_url = make_url(DATABASE_URL)

if database_url.drivername in ("postgres", "postgresql"):
    database_url = database_url.set(
        drivername="postgresql+psycopg2"
    )

engine: Engine = create_engine(
    database_url,
    echo=os.getenv("SQL_ECHO", "true").lower() == "true",
    future=True,
)


def get_engine() -> Engine:
    return engine
