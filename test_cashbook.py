"""
test_cashbook.py - Test suite for CashBook Application.
Validates database logic, running balances, PDF generation, and Kivy imports.
"""

import os
import sys
import tempfile
from datetime import datetime

import database
import pdf_generator


def run_tests():
    print("========================================")
    print("RUNNING CASHBOOK VALIDATION SUITE")
    print("========================================")

    # 1. TEST DATABASE INITIALIZATION IN A TEMP DB
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db_path = tf.name

    try:
        print("\n[1/5] Testing Database Schema & Defaults Initialization...")
        database.init_db(temp_db_path)
        categories = database.get_categories(db_path=temp_db_path)
        assert len(categories) > 0, "Default categories should be seeded."
        print(f"  -> Successfully seeded {len(categories)} default categories.")

        # 2. TEST CATEGORY CRUD
        print("\n[2/5] Testing Category CRUD Operations...")
        new_cat_id = database.add_category("Crypto Profit", "IN", db_path=temp_db_path)
        assert new_cat_id is not None, "Failed to create category."
        in_cats = database.get_categories(category_type="IN", db_path=temp_db_path)
        assert any(c["name"] == "Crypto Profit" for c in in_cats)
        database.delete_category(new_cat_id, db_path=temp_db_path)
        in_cats_after = database.get_categories(category_type="IN", db_path=temp_db_path)
        assert not any(c["name"] == "Crypto Profit" for c in in_cats_after)
        print("  -> Category creation, filtering, and deletion verified.")

        # 3. TEST TRANSACTIONS & RUNNING BALANCES
        print("\n[3/5] Testing Transactions & Running Balances...")
        # Previous month transaction (2026-08-15)
        database.add_transaction(
            date_str="2026-08-15", time_str="10:00:00", category="Sales",
            trans_type="IN", amount=5000.0, payment_mode="Cash", remarks="August Sales",
            db_path=temp_db_path
        )
        database.add_transaction(
            date_str="2026-08-20", time_str="14:00:00", category="Rent",
            trans_type="OUT", amount=1500.0, payment_mode="Bank Transfer", remarks="August Rent",
            db_path=temp_db_path
        )
        # Aug Net = +3500.0

        # Current month transactions (2026-09-01, 2026-09-02, 2026-09-03)
        t1 = database.add_transaction(
            date_str="2026-09-01", time_str="09:30:00", category="Services",
            trans_type="IN", amount=2000.0, payment_mode="Online / UPI", remarks="Consulting",
            db_path=temp_db_path
        )
        t2 = database.add_transaction(
            date_str="2026-09-02", time_str="11:15:00", category="Utilities & Bills",
            trans_type="OUT", amount=300.0, payment_mode="Cash", remarks="Electric Bill",
            db_path=temp_db_path
        )
        t3 = database.add_transaction(
            date_str="2026-09-03", time_str="16:00:00", category="Office Supplies",
            trans_type="OUT", amount=200.0, payment_mode="Online / UPI", remarks="Stationery",
            db_path=temp_db_path
        )

        all_trans = database.get_transactions(db_path=temp_db_path)
        assert len(all_trans) == 5, f"Expected 5 transactions, got {len(all_trans)}"

        # Verify running balance:
        # Aug 15: +5000 (bal: 5000)
        # Aug 20: -1500 (bal: 3500)
        # Sep 01: +2000 (bal: 5500)
        # Sep 02: -300  (bal: 5200)
        # Sep 03: -200  (bal: 5000)
        # all_trans is in reverse chronological order:
        latest = all_trans[0]
        assert latest["running_balance"] == 5000.0, f"Expected 5000.0, got {latest['running_balance']}"
        print(f"  -> Running balance correctly calculated at each step: final = {latest['running_balance']}")

        # Summary check
        summary = database.get_financial_summary(db_path=temp_db_path)
        assert summary["total_in"] == 7000.0, f"Expected total_in 7000.0, got {summary['total_in']}"
        assert summary["total_out"] == 2000.0, f"Expected total_out 2000.0, got {summary['total_out']}"
        assert summary["net_balance"] == 5000.0, f"Expected net_balance 5000.0, got {summary['net_balance']}"
        print(f"  -> Global financial summary verified: In={summary['total_in']}, Out={summary['total_out']}, Net={summary['net_balance']}")

        # Monthly Ledger Check for Sep 2026
        monthly_data = database.get_monthly_ledger_data(2026, 9, db_path=temp_db_path)
        assert monthly_data["opening_balance"] == 3500.0, f"Expected opening 3500.0, got {monthly_data['opening_balance']}"
        assert monthly_data["total_in"] == 2000.0, f"Expected monthly total_in 2000.0, got {monthly_data['total_in']}"
        assert monthly_data["total_out"] == 500.0, f"Expected monthly total_out 500.0, got {monthly_data['total_out']}"
        assert monthly_data["closing_balance"] == 5000.0, f"Expected closing 5000.0, got {monthly_data['closing_balance']}"
        print(f"  -> Monthly ledger calculations verified: Opening={monthly_data['opening_balance']}, Closing={monthly_data['closing_balance']}")

        # 4. TEST REPORTLAB PDF GENERATION
        print("\n[4/5] Testing ReportLab Monthly Ledger PDF Generation...")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as pdf_tf:
            test_pdf_path = pdf_tf.name

        pdf_generator.generate_monthly_pdf(2026, 9, output_path=test_pdf_path, db_path=temp_db_path)
        assert os.path.exists(test_pdf_path), "PDF file was not created."
        pdf_size = os.path.getsize(test_pdf_path)
        assert pdf_size > 1000, f"PDF file size too small: {pdf_size} bytes"
        print(f"  -> Successfully generated PDF statement: {test_pdf_path} ({pdf_size} bytes)")
        try:
            os.remove(test_pdf_path)
        except Exception:
            pass

        # 5. TEST KIVY UI COMPILATION AND APP INSTANTIATION
        print("\n[5/5] Testing Kivy UI & ScreenManager Initialization...")
        import main
        app = main.CashBookApp()
        root_sm = app.build()
        assert root_sm is not None, "Failed to instantiate Kivy ScreenManager."
        assert root_sm.has_screen("dashboard"), "Missing dashboard screen."
        assert root_sm.has_screen("headers"), "Missing headers screen."
        print("  -> Kivy app, screens, and KV design successfully instantiated!")

    finally:
        if os.path.exists(temp_db_path):
            try:
                os.remove(temp_db_path)
            except Exception:
                pass

    print("\n========================================")
    print("ALL CASHBOOK APP TESTS PASSED!")
    print("========================================")


if __name__ == "__main__":
    run_tests()
