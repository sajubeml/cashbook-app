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


def clear_all_transactions(db_path=None):
    """
    Delete all transactions and reset auto-increment ID to start fresh.
    Preserves all category headers.
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions")
    try:
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='transactions'")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    return True


def import_transactions_from_excel(file_path, db_path=None):
    """
    Import transactions from Excel (.xlsx, .xls) or CSV file.
    Intelligently maps column aliases (date, category, in/out, amount, payment mode, remarks),
    automatically creates missing category headers, and persists all records.
    """
    import pandas as pd
    from datetime import datetime

    if not os.path.exists(file_path):
        return {"success": False, "count": 0, "message": "File not found."}

    try:
        if file_path.lower().endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as e:
        return {"success": False, "count": 0, "message": f"Error reading file: {str(e)}"}

    if df.empty:
        return {"success": False, "count": 0, "message": "The selected file is empty."}

    # Normalize column names for flexible matching
    cols_map = {}
    for col in df.columns:
        norm = str(col).strip().lower().replace(" ", "_").replace("-", "_")
        cols_map[norm] = col

    def find_col(aliases):
        for a in aliases:
            if a in cols_map:
                return cols_map[a]
        return None

    date_col = find_col(['date', 'tx_date', 'transaction_date', 'dt', 'txn_date', 'trans_date'])
    time_col = find_col(['time', 'tx_time', 'transaction_time', 'tm'])
    cat_col = find_col(['category', 'head', 'header', 'particulars', 'description', 'account', 'item'])
    type_col = find_col(['type', 'trans_type', 'transaction_type', 'in_out', 'flow', 'direction'])
    amt_col = find_col(['amount', 'total', 'amt', 'value', 'net_amount'])
    in_col = find_col(['cash_in', 'in', 'inflow', 'credit', 'cr', 'received', 'receipt', 'deposit', 'income'])
    out_col = find_col(['cash_out', 'out', 'outflow', 'debit', 'dr', 'paid', 'payment', 'withdrawal', 'expense'])
    mode_col = find_col(['payment_mode', 'mode', 'payment_type', 'method', 'channel'])
    remarks_col = find_col(['remarks', 'remark', 'notes', 'narration', 'memo', 'details', 'comment'])

    if not date_col:
        date_col = df.columns[0]

    imported_count = 0
    now_time = datetime.now().strftime("%H:%M:%S")

    conn = get_connection(db_path)
    cursor = conn.cursor()

    # Pre-fetch categories
    cursor.execute("SELECT name FROM categories")
    existing_cats = {row[0].strip().lower(): row[0] for row in cursor.fetchall()}

    for _, row in df.iterrows():
        # 1. Parse Date
        raw_date = row.get(date_col)
        if pd.isna(raw_date):
            continue
        try:
            if isinstance(raw_date, datetime) or hasattr(raw_date, 'strftime'):
                date_str = raw_date.strftime("%Y-%m-%d")
            else:
                date_str = pd.to_datetime(str(raw_date)).strftime("%Y-%m-%d")
        except Exception:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # 2. Parse Time
        time_str = now_time
        if time_col and not pd.isna(row.get(time_col)):
            raw_time = row.get(time_col)
            if hasattr(raw_time, 'strftime'):
                time_str = raw_time.strftime("%H:%M:%S")
            else:
                t_val = str(raw_time).strip()
                time_str = t_val if len(t_val) >= 5 else now_time

        # 3. Determine Amount & Direction (IN / OUT)
        trans_type = "IN"
        amount = 0.0

        if in_col and out_col:
            in_val = pd.to_numeric(row.get(in_col), errors='coerce')
            out_val = pd.to_numeric(row.get(out_col), errors='coerce')
            if pd.notna(in_val) and in_val > 0:
                trans_type = "IN"
                amount = float(in_val)
            elif pd.notna(out_val) and out_val > 0:
                trans_type = "OUT"
                amount = float(out_val)
            elif amt_col and pd.notna(row.get(amt_col)):
                val = pd.to_numeric(row.get(amt_col), errors='coerce')
                if pd.notna(val) and val != 0:
                    amount = abs(float(val))
                    trans_type = "OUT" if float(val) < 0 else "IN"
        elif amt_col:
            raw_amt = pd.to_numeric(row.get(amt_col), errors='coerce')
            if pd.isna(raw_amt) or raw_amt == 0:
                continue
            amount = abs(float(raw_amt))
            if type_col and not pd.isna(row.get(type_col)):
                t_str = str(row.get(type_col)).strip().upper()
                trans_type = "OUT" if t_str in ['OUT', 'EXPENSE', 'DEBIT', 'DR', 'PAYMENT', '-', 'WITHDRAWAL'] else "IN"
            else:
                trans_type = "OUT" if float(raw_amt) < 0 else "IN"
        elif in_col:
            in_val = pd.to_numeric(row.get(in_col), errors='coerce')
            if pd.notna(in_val) and in_val > 0:
                trans_type = "IN"
                amount = float(in_val)
        elif out_col:
            out_val = pd.to_numeric(row.get(out_col), errors='coerce')
            if pd.notna(out_val) and out_val > 0:
                trans_type = "OUT"
                amount = float(out_val)

        if amount <= 0:
            continue

        # 4. Determine Category
        category_name = "General"
        if cat_col and not pd.isna(row.get(cat_col)):
            cand = str(row.get(cat_col)).strip()
            if cand:
                category_name = cand
        elif remarks_col and not pd.isna(row.get(remarks_col)):
            cand = str(row.get(remarks_col)).strip()
            if cand and len(cand) <= 30:
                category_name = cand

        # Auto-create category if missing
        cat_key = category_name.strip().lower()
        if cat_key not in existing_cats:
            cursor.execute(
                "INSERT INTO categories (name, type, is_default) VALUES (?, ?, 0)",
                (category_name, trans_type)
            )
            existing_cats[cat_key] = category_name

        # 5. Payment Mode
        payment_mode = "Cash"
        if mode_col and not pd.isna(row.get(mode_col)):
            pm = str(row.get(mode_col)).strip()
            if pm:
                payment_mode = pm

        # 6. Remarks
        remarks = ""
        if remarks_col and not pd.isna(row.get(remarks_col)):
            remarks = str(row.get(remarks_col)).strip()

        # Insert Transaction
        cursor.execute("""
            INSERT INTO transactions (date, time, category, type, amount, payment_mode, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (date_str, time_str, category_name, trans_type, amount, payment_mode, remarks))
        imported_count += 1

    conn.commit()
    conn.close()

    return {
        "success": True,
        "count": imported_count,
        "message": f"Successfully imported {imported_count} transactions from Excel!"
    }

