
import sqlite3
from pathlib import Path
import pandas as pd

DB_PATH = Path(__file__).parent / "eca_demo.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def show_query(conn, title, query):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    result = pd.read_sql_query(query, conn)

    if result.empty:
        print("No rows returned.")
    else:
        print(result.to_string(index=False))


def run_sample_queries():

    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Database does not exist. Run create_database.py first."
        )

    conn = get_connection()

    try:

        # -----------------------------------------------------
        # QUERY 1
        # Detailed sales records
        # -----------------------------------------------------

        show_query(
            conn,
            "1. Detailed Sales Records",
            """
            SELECT
                c.company_name,
                p.product_name,
                cu.customer_name,
                s.year,
                s.month,
                s.sales_quantity,
                s.returned_quantity,
                s.sale_price_excluding_tax_and_discounts,
                s.sales_value_excluding_tax_and_discounts
            FROM sales AS s
            JOIN company_products AS cp
                ON s.company_product_id = cp.company_product_id
            JOIN companies AS c
                ON cp.company_id = c.company_id
            JOIN products AS p
                ON cp.product_id = p.product_id
            JOIN customers AS cu
                ON s.customer_id = cu.customer_id
            ORDER BY
                c.company_name,
                s.year,
                s.month;
            """
        )


        # -----------------------------------------------------
        # QUERY 2
        # Total sales by company
        # -----------------------------------------------------

        show_query(
            conn,
            "2. Total Sales by Company",
            """
            SELECT
                c.company_name,
                SUM(s.sales_quantity) AS total_quantity_sold,
                ROUND(
                    SUM(s.sales_value_excluding_tax_and_discounts),
                    2
                ) AS total_sales_value
            FROM sales AS s
            JOIN company_products AS cp
                ON s.company_product_id = cp.company_product_id
            JOIN companies AS c
                ON cp.company_id = c.company_id
            GROUP BY
                c.company_id,
                c.company_name
            ORDER BY
                total_sales_value DESC;
            """
        )


        # -----------------------------------------------------
        # QUERY 3
        # Procurement by supplier
        # Combines local purchases and imports
        # -----------------------------------------------------

        show_query(
            conn,
            "3. Procurement Records by Supplier",
            """
            SELECT
                'Local Purchase' AS procurement_type,
                s.supplier_name,
                c.company_name,
                p.product_name,
                pu.year,
                pu.month,
                pu.quantity,
                pu.purchase_value_excluding_tax_and_discounts
                    AS purchase_value
            FROM purchases AS pu
            JOIN suppliers AS s
                ON pu.supplier_id = s.supplier_id
            JOIN company_products AS cp
                ON pu.company_product_id = cp.company_product_id
            JOIN companies AS c
                ON cp.company_id = c.company_id
            JOIN products AS p
                ON cp.product_id = p.product_id

            UNION ALL

            SELECT
                'Import' AS procurement_type,
                s.supplier_name,
                c.company_name,
                p.product_name,
                i.year,
                i.month,
                i.quantity,
                i.purchase_value
            FROM imports AS i
            JOIN suppliers AS s
                ON i.supplier_id = s.supplier_id
            JOIN company_products AS cp
                ON i.company_product_id = cp.company_product_id
            JOIN companies AS c
                ON cp.company_id = c.company_id
            JOIN products AS p
                ON cp.product_id = p.product_id

            ORDER BY
                company_name,
                year,
                month;
            """
        )


        # -----------------------------------------------------
        # QUERY 4
        # Inventory by warehouse
        # -----------------------------------------------------

        show_query(
            conn,
            "4. Inventory by Warehouse",
            """
            SELECT
                c.company_name,
                w.warehouse_name,
                p.product_name,
                i.year,
                i.inventory_quantity,
                i.inventory_value_excluding_tax,
                sc.storage_capacity
            FROM inventory AS i
            JOIN warehouses AS w
                ON i.warehouse_id = w.warehouse_id
            JOIN companies AS c
                ON w.company_id = c.company_id
            JOIN company_products AS cp
                ON i.company_product_id = cp.company_product_id
            JOIN products AS p
                ON cp.product_id = p.product_id
            LEFT JOIN storage_capacity AS sc
                ON sc.warehouse_id = w.warehouse_id
               AND sc.year = i.year
            ORDER BY
                c.company_name,
                w.warehouse_name,
                p.product_name;
            """
        )


        # -----------------------------------------------------
        # QUERY 5
        # Tender summary
        # -----------------------------------------------------

        show_query(
            conn,
            "5. Tender Summary",
            """
            SELECT
                c.company_name,
                t.tendering_entity_name,
                t.tender_date,
                COUNT(ti.tender_item_id) AS number_of_products,
                SUM(ti.sales_quantity) AS total_quantity,
                ROUND(
                    SUM(ti.sales_value_excluding_tax),
                    2
                ) AS total_value_excluding_tax
            FROM tenders AS t
            JOIN companies AS c
                ON t.company_id = c.company_id
            JOIN tender_items AS ti
                ON t.tender_id = ti.tender_id
            GROUP BY
                t.tender_id,
                c.company_name,
                t.tendering_entity_name,
                t.tender_date
            ORDER BY
                t.tender_date;
            """
        )


        # -----------------------------------------------------
        # QUERY 6
        # Company financial overview
        # -----------------------------------------------------

        show_query(
            conn,
            "6. Company Financial Overview",
            """
            SELECT
                c.company_name,
                cf.year,
                cf.total_assets,
                cf.annual_revenue,
                cf.total_liabilities,
                cf.total_expenses
            FROM company_financials AS cf
            JOIN companies AS c
                ON cf.company_id = c.company_id
            ORDER BY
                cf.year DESC,
                c.company_name;
            """
        )

    finally:
        conn.close()


if __name__ == "__main__":
    run_sample_queries()
