"""
database.py - SQLite persistence and financial analytics engine for CashBook Application.
Handles transactions, category headers, running balances, and monthly summaries.
"""

import sqlite3
from datetime import datetime
import os

def get_default_db_path():
    """Determine database path dynamically, supporting Android user_data_dir."""
    try:
        from kivy.utils import platform
        if platform == 'android':
            from kivy.app import App
            app = App.get_running_app()
            if app and hasattr(app, 'user_data_dir') and app.user_data_dir:
                return os.path.join(app.user_data_dir, "cashbook.db")
    except Exception:
        pass
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "cashbook.db")


DEFAULT_DB_PATH = get_default_db_path()

DEFAULT_CATEGORIES = [
    # Inflow Categories
    ("Sales", "IN"),
    ("Services", "IN"),
    ("Investment", "IN"),
    ("Loan Recovery", "IN"),
    ("Salary / Wages", "IN"),
    ("Commission", "IN"),
    ("Other Income", "IN"),
    # Outflow Categories
    ("Rent", "OUT"),
    ("Utilities & Bills", "OUT"),
    ("Office Supplies", "OUT"),
    ("Salaries Paid", "OUT"),
    ("Maintenance & Repairs", "OUT"),
    ("Travel & Transport", "OUT"),
    ("Food & Refreshment", "OUT"),
    ("Marketing & Ads", "OUT"),
    ("Taxes & Fees", "OUT"),
    ("Personal Draw", "OUT"),
    ("Other Expense", "OUT"),
]


def get_connection(db_path=None):
    """Create and return a database connection."""
    target_path = db_path or get_default_db_path()
    conn = sqlite3.connect(target_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path=None):
    """Initialize database schema and seed default category headers if empty."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Create Categories Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            type TEXT NOT NULL CHECK(type IN ('IN', 'OUT', 'BOTH')),
            is_default INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,          -- Format: YYYY-MM-DD
            time TEXT NOT NULL,          -- Format: HH:MM:SS
            category TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('IN', 'OUT')),
            amount REAL NOT NULL CHECK(amount >= 0),
            payment_mode TEXT NOT NULL,  -- Cash, Bank Transfer, Online/UPI, Cheque, etc.
            remarks TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexing for performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(date, time)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_type ON transactions(type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trans_cat ON transactions(category)")

    # Seed Default Categories if none exist
    cursor.execute("SELECT COUNT(*) FROM categories")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            "INSERT OR IGNORE INTO categories (name, type, is_default) VALUES (?, ?, 1)",
            DEFAULT_CATEGORIES
        )

    conn.commit()
    conn.close()


# ==========================================
# CATEGORY CRUD OPERATIONS
# ==========================================

def get_categories(category_type=None, db_path=None):
    """
    Retrieve categories, optionally filtered by type ('IN', 'OUT', or None for all).
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    if category_type:
        cursor.execute(
            "SELECT id, name, type, is_default FROM categories WHERE type = ? OR type = 'BOTH' ORDER BY name ASC",
            (category_type.upper(),)
        )
    else:
        cursor.execute("SELECT id, name, type, is_default FROM categories ORDER BY type, name ASC")

    rows = cursor.fetchall()
    categories = [dict(row) for row in rows]
    conn.close()
    return categories


def add_category(name, category_type="OUT", db_path=None):
    """Add a new custom category header."""
    name = name.strip()
    if not name:
        raise ValueError("Category name cannot be empty.")

    category_type = category_type.upper()
    if category_type not in ('IN', 'OUT', 'BOTH'):
        raise ValueError("Category type must be 'IN', 'OUT', or 'BOTH'.")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (name, type, is_default) VALUES (?, ?, 0)",
            (name, category_type)
        )
        conn.commit()
        cat_id = cursor.lastrowid
        return cat_id
    except sqlite3.IntegrityError:
        raise ValueError(f"Category '{name}' already exists.")
    finally:
        conn.close()


def update_category(category_id, new_name, new_type=None, db_path=None):
    """Update an existing category's name or type."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Category name cannot be empty.")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        if new_type:
            cursor.execute(
                "UPDATE categories SET name = ?, type = ? WHERE id = ?",
                (new_name, new_type.upper(), category_id)
            )
        else:
            cursor.execute(
                "UPDATE categories SET name = ? WHERE id = ?",
                (new_name, category_id)
            )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_category(category_id, db_path=None):
    """Delete a category header by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


# ==========================================
# TRANSACTION CRUD & RUNNING BALANCE
# ==========================================

def add_transaction(date_str, time_str, category, trans_type, amount, payment_mode="Cash", remarks="", db_path=None):
    """
    Log a new transaction (Cash In or Cash Out).
    """
    trans_type = trans_type.upper()
    if trans_type not in ('IN', 'OUT'):
        raise ValueError("Transaction type must be 'IN' or 'OUT'.")

    amount = float(amount)
    if amount < 0:
        raise ValueError("Amount cannot be negative.")

    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    if not time_str:
        time_str = datetime.now().strftime("%H:%M:%S")

    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (date, time, category, type, amount, payment_mode, remarks)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date_str, time_str, category, trans_type, amount, payment_mode, remarks.strip()))
    conn.commit()
    trans_id = cursor.lastrowid
    conn.close()
    return trans_id


def delete_transaction(transaction_id, db_path=None):
    """Remove a transaction by ID."""
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


def get_transactions(start_date=None, end_date=None, category=None, trans_type=None, search=None, db_path=None):
    """
    Retrieve filtered transactions with chronological running balances.
    First computes global running balances chronologically, then filters if required.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Pull all transactions in chronological order to compute true running balances
    cursor.execute("""
        SELECT id, date, time, category, type, amount, payment_mode, remarks, created_at
        FROM transactions
        ORDER BY date ASC, time ASC, id ASC
    """)
    all_rows = cursor.fetchall()
    conn.close()

    running_balance = 0.0
    computed_list = []

    for row in all_rows:
        item = dict(row)
        amt = float(item["amount"])
        if item["type"] == "IN":
            running_balance += amt
        else:
            running_balance -= amt
        item["running_balance"] = round(running_balance, 2)
        computed_list.append(item)

    # Apply filters in memory to preserve accurate running balance calculation
    filtered_list = computed_list
    if start_date:
        filtered_list = [t for t in filtered_list if t["date"] >= start_date]
    if end_date:
        filtered_list = [t for t in filtered_list if t["date"] <= end_date]
    if category:
        filtered_list = [t for t in filtered_list if t["category"].lower() == category.lower()]
    if trans_type:
        filtered_list = [t for t in filtered_list if t["type"] == trans_type.upper()]
    if search:
        s_lower = search.lower()
        filtered_list = [
            t for t in filtered_list
            if s_lower in t["category"].lower()
            or s_lower in t["remarks"].lower()
            or s_lower in t["payment_mode"].lower()
        ]

    # Return most recent first for dashboard display
    return list(reversed(filtered_list))


def get_financial_summary(start_date=None, end_date=None, db_path=None):
    """
    Aggregates financial totals: Total Cash In, Total Cash Out, and Net Balance.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT type, SUM(amount) as total FROM transactions"
    params = []
    conditions = []

    if start_date:
        conditions.append("date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date <= ?")
        params.append(end_date)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY type"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    total_in = 0.0
    total_out = 0.0
    for row in rows:
        if row["type"] == "IN":
            total_in = float(row["total"])
        elif row["type"] == "OUT":
            total_out = float(row["total"])

    return {
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "net_balance": round(total_in - total_out, 2)
    }


def get_monthly_ledger_data(year, month, db_path=None):
    """
    Retrieve opening balance, monthly transactions with running balance,
    totals, and closing balance for a specific year and month.
    """
    start_date = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1:04d}-01-01"
    else:
        end_date = f"{year:04d}-{month + 1:02d}-01"

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Opening balance: all transactions before start_date
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'IN' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type = 'OUT' THEN amount ELSE 0 END), 0) AS opening_balance
        FROM transactions
        WHERE date < ?
    """, (start_date,))
    opening_balance = float(cursor.fetchone()["opening_balance"])

    # 2. Transactions during the month in chronological order
    cursor.execute("""
        SELECT id, date, time, category, type, amount, payment_mode, remarks
        FROM transactions
        WHERE date >= ? AND date < ?
        ORDER BY date ASC, time ASC, id ASC
    """, (start_date, end_date))
    rows = cursor.fetchall()
    conn.close()

    monthly_transactions = []
    current_balance = opening_balance
    total_in = 0.0
    total_out = 0.0

    for r in rows:
        item = dict(r)
        amt = float(item["amount"])
        if item["type"] == "IN":
            total_in += amt
            current_balance += amt
        else:
            total_out += amt
            current_balance -= amt
        item["running_balance"] = round(current_balance, 2)
        monthly_transactions.append(item)

    return {
        "year": year,
        "month": month,
        "opening_balance": round(opening_balance, 2),
        "total_in": round(total_in, 2),
        "total_out": round(total_out, 2),
        "closing_balance": round(current_balance, 2),
        "transactions": monthly_transactions
    }
