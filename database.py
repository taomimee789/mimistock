"""database.py

SQLite helper + schema migrations for Stock_PRO.

Keep this module import-safe (no side effects like creating/migrating DB on import).
Call `init_db()` once at app startup.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional


def get_db_path() -> Path:
    """Return default DB path.

    - In dev: use per-user appdata DB (more reliable than cwd)
    - Can be overridden by passing db_path into connect_db/init_db
    """
    try:
        from paths import user_db_path

        return user_db_path()
    except Exception:
        return Path(__file__).resolve().parent / "bot_system.db"


def connect_db(db_path: Optional[os.PathLike | str] = None) -> sqlite3.Connection:
    """Connect to SQLite database."""
    path = Path(db_path) if db_path else get_db_path()
    # check_same_thread=False lets us use the connection across threads if needed.
    return sqlite3.connect(str(path), check_same_thread=False)


def setup_database(db_path: Optional[os.PathLike | str] = None) -> None:
    """Create DB file and base tables if missing."""
    path = Path(db_path) if db_path else get_db_path()
    is_new = not path.exists()

    conn = connect_db(path)
    cursor = conn.cursor()

    # Base tables (CREATE IF NOT EXISTS is safe to run repeatedly)
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_recorded TEXT DEFAULT CURRENT_TIMESTAMP,
            product TEXT NOT NULL,
            shop TEXT NOT NULL,
            price REAL NOT NULL,
            payment TEXT NOT NULL,
            tracking TEXT,
            shipping TEXT,
            status TEXT,
            user_id TEXT,
            password TEXT,
            f2a TEXT,
            cod_expense REAL DEFAULT 0,
            unit_per_item INTEGER DEFAULT 1,
            processed INTEGER DEFAULT 0
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0,
            cost_price REAL NOT NULL DEFAULT 0,
            date_received TEXT DEFAULT CURRENT_TIMESTAMP,
            sku TEXT,
            order_id INTEGER,
            sell_price_retail REAL DEFAULT 0,
            sell_price_wholesale REAL DEFAULT 0,
            sold_quantity INTEGER DEFAULT 0,
            sold_revenue REAL DEFAULT 0,
            unit_per_pack INTEGER DEFAULT 1,
            barcode TEXT,
            unit_per_item INTEGER DEFAULT 1
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS product_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT UNIQUE NOT NULL,
            sku_prefix TEXT NOT NULL,
            sell_price_retail REAL NOT NULL,
            sell_price_wholesale REAL NOT NULL,
            barcode TEXT DEFAULT NULL
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            total_price REAL NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    conn.close()

    # avoid emoji printing issues on some Windows consoles


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols


def update_database_schema(db_path: Optional[os.PathLike | str] = None) -> None:
    """Apply lightweight migrations (add missing columns)."""
    conn = connect_db(db_path)
    cur = conn.cursor()

    # orders additions
    if not _has_column(conn, "orders", "status_updated_at"):
        cur.execute("ALTER TABLE orders ADD COLUMN status_updated_at TEXT;")

    if not _has_column(conn, "orders", "unit_conversion"):
        cur.execute("ALTER TABLE orders ADD COLUMN unit_conversion TEXT DEFAULT '1:1';")

    if not _has_column(conn, "orders", "hidden"):
        cur.execute("ALTER TABLE orders ADD COLUMN hidden INTEGER DEFAULT 0;")

    # stock additions
    if not _has_column(conn, "stock", "unit_conversion"):
        cur.execute("ALTER TABLE stock ADD COLUMN unit_conversion TEXT DEFAULT '1:1';")

    # product_categories additions
    if not _has_column(conn, "product_categories", "unit_conversion"):
        cur.execute("ALTER TABLE product_categories ADD COLUMN unit_conversion TEXT DEFAULT '1:1';")

    if not _has_column(conn, "product_categories", "unit_per_item"):
        cur.execute("ALTER TABLE product_categories ADD COLUMN unit_per_item INTEGER DEFAULT 1;")

    conn.commit()
    conn.close()


def init_db(db_path: Optional[os.PathLike | str] = None) -> None:
    """Create DB + run migrations. Call once at startup."""
    setup_database(db_path)
    update_database_schema(db_path)
