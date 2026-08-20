
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "eca_demo.db"

EXPECTED_TABLES = {
    "companies",
    "company_financials",
    "company_activities",
    "related_parties",
    "products",
    "product_alternatives",
    "company_products",
    "customers",
    "suppliers",
    "warehouses",
    "imports",
    "purchases",
    "costs",
    "sales",
    "tenders",
    "tender_items",
    "exports",
    "storage_capacity",
    "inventory"
}


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def test_rejected_insert(conn, test_name, sql, params):
    """
    Tests whether SQLite correctly rejects an invalid row.
    The database is left unchanged.
    """

    conn.execute("SAVEPOINT validation_test;")

    try:
        conn.execute(sql, params)

        print(f"[FAIL] {test_name}")
        print("       Invalid row was accepted.")

    except sqlite3.IntegrityError:
        print(f"[PASS] {test_name}")

    finally:
        conn.execute("ROLLBACK TO validation_test;")
        conn.execute("RELEASE validation_test;")


def get_duplicate_financial_pair(conn):
    """Return an existing key so the deliberate UNIQUE test is data-independent."""
    row = conn.execute("""
        SELECT company_id, year
        FROM company_financials
        ORDER BY company_id, year
        LIMIT 1;
    """).fetchone()
    if row is None:
        raise ValueError("Duplicate-financial constraint test requires one financial record")
    return row


def validate_database():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Database does not exist. Run create_database.py first."
        )

    conn = get_connection()

    try:

        print("=" * 60)
        print("ECA DEMO DATABASE VALIDATION")
        print("=" * 60)

        # -----------------------------------------------------
        # 1. SQLite integrity check
        # -----------------------------------------------------

        integrity_result = conn.execute(
            "PRAGMA integrity_check;"
        ).fetchone()[0]

        if integrity_result == "ok":
            print("[PASS] SQLite integrity check")
        else:
            print("[FAIL] SQLite integrity check:", integrity_result)


        # -----------------------------------------------------
        # 2. Expected tables
        # -----------------------------------------------------

        actual_tables = {
            row[0]
            for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%';
            """)
        }

        missing_tables = EXPECTED_TABLES - actual_tables

        if not missing_tables:
            print(f"[PASS] All {len(EXPECTED_TABLES)} expected tables exist")
        else:
            print("[FAIL] Missing tables:", missing_tables)


        # -----------------------------------------------------
        # 3. Foreign key violations
        # -----------------------------------------------------

        fk_violations = conn.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

        if not fk_violations:
            print("[PASS] No foreign key violations")
        else:
            print("[FAIL] Foreign key violations found:")
            for violation in fk_violations:
                print("      ", violation)


        # -----------------------------------------------------
        # 4. Cross-company SALES validation
        #
        # A sale's company_product and customer must belong
        # to the same company.
        # -----------------------------------------------------

        inconsistent_sales = conn.execute("""
            SELECT
                s.sale_id,
                cp.company_id AS product_company_id,
                cu.company_id AS customer_company_id
            FROM sales AS s
            JOIN company_products AS cp
                ON s.company_product_id = cp.company_product_id
            JOIN customers AS cu
                ON s.customer_id = cu.customer_id
            WHERE cp.company_id <> cu.company_id;
        """).fetchall()

        if not inconsistent_sales:
            print("[PASS] All sales use customers belonging to the same company")
        else:
            print("[FAIL] Cross-company sales detected:")
            for row in inconsistent_sales:
                print("      ", row)


        # -----------------------------------------------------
        # 5. Cross-company TENDER ITEM validation
        #
        # Product in tender item should belong to company
        # that owns the tender.
        # -----------------------------------------------------

        inconsistent_tenders = conn.execute("""
            SELECT
                ti.tender_item_id,
                t.company_id AS tender_company_id,
                cp.company_id AS product_company_id
            FROM tender_items AS ti
            JOIN tenders AS t
                ON ti.tender_id = t.tender_id
            JOIN company_products AS cp
                ON ti.company_product_id = cp.company_product_id
            WHERE t.company_id <> cp.company_id;
        """).fetchall()

        if not inconsistent_tenders:
            print("[PASS] All tender items belong to the tender company")
        else:
            print("[FAIL] Cross-company tender items detected:")
            for row in inconsistent_tenders:
                print("      ", row)


        # -----------------------------------------------------
        # 6. Cross-company INVENTORY validation
        #
        # Product and warehouse should belong to same company.
        # -----------------------------------------------------

        inconsistent_inventory = conn.execute("""
            SELECT
                i.inventory_id,
                w.company_id AS warehouse_company_id,
                cp.company_id AS product_company_id
            FROM inventory AS i
            JOIN warehouses AS w
                ON i.warehouse_id = w.warehouse_id
            JOIN company_products AS cp
                ON i.company_product_id = cp.company_product_id
            WHERE w.company_id <> cp.company_id;
        """).fetchall()

        if not inconsistent_inventory:
            print("[PASS] Inventory products belong to the warehouse company")
        else:
            print("[FAIL] Cross-company inventory records detected:")
            for row in inconsistent_inventory:
                print("      ", row)


        print()
        print("-" * 60)
        print("CONSTRAINT TESTS")
        print("-" * 60)


        # -----------------------------------------------------
        # Get valid IDs for deliberate tests
        # -----------------------------------------------------

        company_id = conn.execute("""
            SELECT company_id FROM companies ORDER BY company_id LIMIT 1;
        """).fetchone()[0]

        # Use a pair that actually exists. Large synthetic companies do not all
        # have a 2025 record, so a hard-coded year would not test the UNIQUE key.
        duplicate_company_id, duplicate_financial_year = get_duplicate_financial_pair(conn)

        company_product_id = conn.execute("""
            SELECT company_product_id
            FROM company_products
            ORDER BY company_product_id
            LIMIT 1;
        """).fetchone()[0]

        customer_id = conn.execute("""
            SELECT customer_id
            FROM customers
            ORDER BY customer_id
            LIMIT 1;
        """).fetchone()[0]


        # -----------------------------------------------------
        # 7. Invalid foreign key
        # -----------------------------------------------------

        test_rejected_insert(
            conn,
            "Foreign key rejects nonexistent company",
            """
            INSERT INTO company_financials (
                company_id,
                year,
                annual_revenue
            )
            VALUES (?, ?, ?);
            """,
            (999999, 2026, 100000)
        )


        # -----------------------------------------------------
        # 8. Duplicate company/year
        # -----------------------------------------------------

        test_rejected_insert(
            conn,
            "UNIQUE prevents duplicate company financial year",
            """
            INSERT INTO company_financials (
                company_id,
                year,
                annual_revenue
            )
            VALUES (?, ?, ?);
            """,
            (duplicate_company_id, duplicate_financial_year, 999999)
        )


        # -----------------------------------------------------
        # 9. Invalid month
        # -----------------------------------------------------

        test_rejected_insert(
            conn,
            "CHECK rejects month outside 1-12",
            """
            INSERT INTO sales (
                company_product_id,
                customer_id,
                year,
                month,
                sales_quantity
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                company_product_id,
                customer_id,
                2026,
                13,
                100
            )
        )


        # -----------------------------------------------------
        # 10. Returned quantity > sales quantity
        # -----------------------------------------------------

        test_rejected_insert(
            conn,
            "CHECK rejects returns greater than sales",
            """
            INSERT INTO sales (
                company_product_id,
                customer_id,
                year,
                month,
                sales_quantity,
                returned_quantity
            )
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (
                company_product_id,
                customer_id,
                2026,
                3,
                100,
                150
            )
        )


        # -----------------------------------------------------
        # 11. Negative quantity
        # -----------------------------------------------------

        test_rejected_insert(
            conn,
            "CHECK rejects negative sales quantity",
            """
            INSERT INTO sales (
                company_product_id,
                customer_id,
                year,
                month,
                sales_quantity
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                company_product_id,
                customer_id,
                2026,
                3,
                -50
            )
        )


        # -----------------------------------------------------
        # 12. Demonstrate the cross-company FK limitation
        # -----------------------------------------------------

        companies = conn.execute("""
            SELECT company_id
            FROM companies
            ORDER BY company_id;
        """).fetchall()

        if len(companies) >= 2:

            company_a = companies[0][0]
            company_b = companies[1][0]

            product_a = conn.execute("""
                SELECT company_product_id
                FROM company_products
                WHERE company_id = ?
                LIMIT 1;
            """, (company_a,)).fetchone()[0]

            customer_b = conn.execute("""
                SELECT customer_id
                FROM customers
                WHERE company_id = ?
                LIMIT 1;
            """, (company_b,)).fetchone()[0]

            conn.execute("SAVEPOINT cross_company_test;")

            try:

                conn.execute("""
                    INSERT INTO sales (
                        company_product_id,
                        customer_id,
                        year,
                        month,
                        sales_quantity
                    )
                    VALUES (?, ?, ?, ?, ?);
                """, (
                    product_a,
                    customer_b,
                    2026,
                    3,
                    10
                ))

                mismatch_count = conn.execute("""
                    SELECT COUNT(*)
                    FROM sales AS s
                    JOIN company_products AS cp
                        ON s.company_product_id = cp.company_product_id
                    JOIN customers AS cu
                        ON s.customer_id = cu.customer_id
                    WHERE cp.company_id <> cu.company_id;
                """).fetchone()[0]

                if mismatch_count > 0:
                    print(
                        "[PASS] Cross-company business-rule validator "
                        "detects mismatch not prevented by ordinary FKs"
                    )
                else:
                    print(
                        "[FAIL] Cross-company mismatch was not detected"
                    )

            finally:
                conn.execute("ROLLBACK TO cross_company_test;")
                conn.execute("RELEASE cross_company_test;")


        print()
        print("=" * 60)
        print("Validation complete.")
        print("No deliberate test rows were retained.")
        print("=" * 60)

    finally:
        conn.close()


if __name__ == "__main__":
    validate_database()
