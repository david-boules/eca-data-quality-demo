
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "eca_demo.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def get_single_id(conn, query, params):
    row = conn.execute(query, params).fetchone()

    if row is None:
        raise ValueError(f"Required record not found for query: {query}")

    return row[0]


def populate_database():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            "Database does not exist. Run create_database.py first."
        )

    conn = get_connection()

    try:
        # -----------------------------------------------------
        # Avoid duplicating the synthetic seed dataset
        # -----------------------------------------------------

        existing_demo_companies = conn.execute("""
            SELECT COUNT(*)
            FROM companies
            WHERE company_name IN (?, ?);
        """, (
            "Nile Horizon Distribution",
            "DeltaCare Distribution"
        )).fetchone()[0]

        if existing_demo_companies == 2:
            print("Demo data already exists. Population skipped.")
            return

        # Everything below is one transaction.
        # If any insert fails, the whole population is rolled back.
        with conn:

            # =================================================
            # COMPANIES
            # =================================================

            conn.executemany("""
                INSERT INTO companies (
                    company_name,
                    market_or_sector,
                    establishment_year,
                    company_type,
                    contact_details
                )
                VALUES (?, ?, ?, ?, ?);
            """, [
                (
                    "Nile Horizon Distribution",
                    "Pharmaceutical Distribution",
                    2015,
                    "Joint Stock Company",
                    "demo@nilehorizon.example"
                ),
                (
                    "DeltaCare Distribution",
                    "Pharmaceutical Distribution",
                    2018,
                    "Limited Liability Company",
                    "demo@deltacare.example"
                )
            ])

            nile_id = get_single_id(
                conn,
                "SELECT company_id FROM companies WHERE company_name = ?;",
                ("Nile Horizon Distribution",)
            )

            delta_id = get_single_id(
                conn,
                "SELECT company_id FROM companies WHERE company_name = ?;",
                ("DeltaCare Distribution",)
            )

            # =================================================
            # COMPANY FINANCIALS
            # =================================================

            conn.executemany("""
                INSERT INTO company_financials (
                    company_id,
                    year,
                    issued_capital,
                    paid_in_capital,
                    total_assets,
                    annual_revenue,
                    total_liabilities,
                    total_expenses
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_id, 2025,
                    10_000_000,
                    8_000_000,
                    25_000_000,
                    40_000_000,
                    12_000_000,
                    30_000_000
                ),
                (
                    delta_id, 2025,
                    7_000_000,
                    6_000_000,
                    18_000_000,
                    29_000_000,
                    8_000_000,
                    21_000_000
                )
            ])

            # =================================================
            # COMPANY ACTIVITIES
            # =================================================

            conn.executemany("""
                INSERT INTO company_activities (
                    company_id,
                    activity_name
                )
                VALUES (?, ?);
            """, [
                (nile_id, "Distribution"),
                (nile_id, "Importing"),
                (delta_id, "Distribution"),
                (delta_id, "Exporting")
            ])

            # =================================================
            # RELATED PARTIES
            # =================================================

            conn.executemany("""
                INSERT INTO related_parties (
                    company_id,
                    related_party_name,
                    contact_details
                )
                VALUES (?, ?, ?);
            """, [
                (
                    nile_id,
                    "Nile Horizon Logistics",
                    "synthetic@nilelogistics.example"
                ),
                (
                    delta_id,
                    "DeltaCare Services",
                    "synthetic@deltacareservices.example"
                )
            ])

            # =================================================
            # PRODUCTS
            # =================================================

            conn.executemany("""
                INSERT INTO products (
                    product_name,
                    brand_name,
                    product_specifications,
                    license_holder_company,
                    manufacturer_company,
                    product_source,
                    product_type,
                    dispensing_method,
                    registration_status,
                    registration_authority,
                    therapeutic_purpose,
                    active_ingredient
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    "Cardiovex 10mg",
                    "Cardiovex",
                    "10mg tablets",
                    "Fictional Health Holdings",
                    "Synthetic Pharma Manufacturing",
                    "Local",
                    "Generic",
                    "Prescribed",
                    "Registered",
                    "Fictional Registration Authority",
                    "Cardiovascular treatment",
                    "Compound A"
                ),
                (
                    "Painrelief 500mg",
                    "Painrelief",
                    "500mg tablets",
                    "Demo Medical Holdings",
                    "Demo Laboratories",
                    "Local",
                    "Generic",
                    "OTC",
                    "Registered",
                    "Fictional Registration Authority",
                    "Pain relief",
                    "Compound B"
                ),
                (
                    "Respira 5mg",
                    "Respira",
                    "5mg tablets",
                    "Global Synthetic Healthcare",
                    "Example International Pharma",
                    "Imported",
                    "Originator",
                    "Prescribed",
                    "Registered",
                    "Fictional Registration Authority",
                    "Respiratory treatment",
                    "Compound C"
                )
            ])

            cardiovex_id = get_single_id(
                conn,
                "SELECT product_id FROM products WHERE product_name = ?;",
                ("Cardiovex 10mg",)
            )

            painrelief_id = get_single_id(
                conn,
                "SELECT product_id FROM products WHERE product_name = ?;",
                ("Painrelief 500mg",)
            )

            respira_id = get_single_id(
                conn,
                "SELECT product_id FROM products WHERE product_name = ?;",
                ("Respira 5mg",)
            )

            # =================================================
            # PRODUCT ALTERNATIVES
            # =================================================

            conn.execute("""
                INSERT INTO product_alternatives (
                    product_id,
                    alternative_product_name,
                    alternative_product_manufacturer
                )
                VALUES (?, ?, ?);
            """, (
                cardiovex_id,
                "CardioDemo 10mg",
                "Example Alternative Pharma"
            ))

            # =================================================
            # COMPANY PRODUCTS
            # =================================================

            conn.executemany("""
                INSERT INTO company_products (
                    company_id,
                    product_id
                )
                VALUES (?, ?);
            """, [
                (nile_id, cardiovex_id),
                (nile_id, respira_id),
                (delta_id, cardiovex_id),
                (delta_id, painrelief_id)
            ])

            nile_cardiovex_cp = get_single_id(
                conn,
                """
                SELECT company_product_id
                FROM company_products
                WHERE company_id = ?
                  AND product_id = ?;
                """,
                (nile_id, cardiovex_id)
            )

            nile_respira_cp = get_single_id(
                conn,
                """
                SELECT company_product_id
                FROM company_products
                WHERE company_id = ?
                  AND product_id = ?;
                """,
                (nile_id, respira_id)
            )

            delta_cardiovex_cp = get_single_id(
                conn,
                """
                SELECT company_product_id
                FROM company_products
                WHERE company_id = ?
                  AND product_id = ?;
                """,
                (delta_id, cardiovex_id)
            )

            delta_painrelief_cp = get_single_id(
                conn,
                """
                SELECT company_product_id
                FROM company_products
                WHERE company_id = ?
                  AND product_id = ?;
                """,
                (delta_id, painrelief_id)
            )

            # =================================================
            # CUSTOMERS
            # =================================================

            conn.executemany("""
                INSERT INTO customers (
                    company_id,
                    customer_name,
                    customer_type,
                    customer_code,
                    branch_area,
                    governorate,
                    relationship_start_date,
                    relationship_end_date,
                    phone_number
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_id,
                    "Sunrise Pharmacy",
                    "Pharmacy",
                    "NH-C001",
                    "Nasr City",
                    "Cairo",
                    "2023-01-01",
                    None,
                    "01000000001"
                ),
                (
                    nile_id,
                    "Green Valley Medical Center",
                    "Medical Center",
                    "NH-C002",
                    "Dokki",
                    "Giza",
                    "2024-02-01",
                    None,
                    "01000000002"
                ),
                (
                    delta_id,
                    "Sunrise Pharmacy",
                    "Pharmacy",
                    "DC-C001",
                    "Nasr City",
                    "Cairo",
                    "2024-06-01",
                    None,
                    "01000000001"
                )
            ])

            nile_sunrise_customer = get_single_id(
                conn,
                """
                SELECT customer_id
                FROM customers
                WHERE company_id = ?
                  AND customer_code = ?;
                """,
                (nile_id, "NH-C001")
            )

            nile_green_customer = get_single_id(
                conn,
                """
                SELECT customer_id
                FROM customers
                WHERE company_id = ?
                  AND customer_code = ?;
                """,
                (nile_id, "NH-C002")
            )

            delta_sunrise_customer = get_single_id(
                conn,
                """
                SELECT customer_id
                FROM customers
                WHERE company_id = ?
                  AND customer_code = ?;
                """,
                (delta_id, "DC-C001")
            )

            # =================================================
            # SUPPLIERS
            # =================================================

            conn.executemany("""
                INSERT INTO suppliers (
                    supplier_name
                )
                VALUES (?);
            """, [
                ("Global Demo Pharma",),
                ("Cairo Synthetic Manufacturing",)
            ])

            global_supplier_id = get_single_id(
                conn,
                "SELECT supplier_id FROM suppliers WHERE supplier_name = ?;",
                ("Global Demo Pharma",)
            )

            cairo_supplier_id = get_single_id(
                conn,
                "SELECT supplier_id FROM suppliers WHERE supplier_name = ?;",
                ("Cairo Synthetic Manufacturing",)
            )

            # =================================================
            # WAREHOUSES
            # =================================================

            conn.executemany("""
                INSERT INTO warehouses (
                    company_id,
                    warehouse_name,
                    warehouse_area
                )
                VALUES (?, ?, ?);
            """, [
                (
                    nile_id,
                    "Nile Central Warehouse",
                    "Cairo"
                ),
                (
                    delta_id,
                    "Delta Main Warehouse",
                    "Giza"
                )
            ])

            nile_warehouse_id = get_single_id(
                conn,
                """
                SELECT warehouse_id
                FROM warehouses
                WHERE company_id = ?
                  AND warehouse_name = ?;
                """,
                (nile_id, "Nile Central Warehouse")
            )

            delta_warehouse_id = get_single_id(
                conn,
                """
                SELECT warehouse_id
                FROM warehouses
                WHERE company_id = ?
                  AND warehouse_name = ?;
                """,
                (delta_id, "Delta Main Warehouse")
            )

            # =================================================
            # IMPORTS
            # =================================================

            conn.execute("""
                INSERT INTO imports (
                    company_product_id,
                    supplier_id,
                    year,
                    month,
                    country_of_origin,
                    cif_import_price,
                    quantity,
                    discount_value,
                    purchase_value
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                nile_respira_cp,
                global_supplier_id,
                2026,
                1,
                "Exampleland",
                80.0,
                1000,
                2500.0,
                77_500.0
            ))

            # =================================================
            # LOCAL PURCHASES
            # =================================================

            conn.executemany("""
                INSERT INTO purchases (
                    company_product_id,
                    supplier_id,
                    year,
                    month,
                    quantity,
                    discount_value,
                    price_excluding_tax_and_discounts,
                    purchase_value_excluding_tax_and_discounts,
                    purchase_value_including_tax_and_discounts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_cardiovex_cp,
                    cairo_supplier_id,
                    2026,
                    1,
                    2000,
                    2000.0,
                    30.0,
                    60_000.0,
                    66_000.0
                ),
                (
                    delta_painrelief_cp,
                    cairo_supplier_id,
                    2026,
                    1,
                    1500,
                    1500.0,
                    20.0,
                    30_000.0,
                    33_000.0
                )
            ])

            # =================================================
            # COSTS
            # =================================================

            conn.executemany("""
                INSERT INTO costs (
                    company_product_id,
                    year,
                    month,
                    wages_and_salaries,
                    financing_and_banking_costs,
                    administrative_expenses,
                    other_fixed_costs,
                    total_fixed_cost,
                    drug_purchase_cost,
                    energy_cost,
                    transport_cost,
                    other_variable_costs,
                    total_variable_cost,
                    total_production_cost
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_cardiovex_cp,
                    2026,
                    1,
                    12_000.0,
                    2_000.0,
                    4_000.0,
                    1_000.0,
                    19_000.0,
                    60_000.0,
                    3_000.0,
                    5_000.0,
                    2_000.0,
                    70_000.0,
                    89_000.0
                ),
                (
                    delta_painrelief_cp,
                    2026,
                    1,
                    9_000.0,
                    1_500.0,
                    3_000.0,
                    500.0,
                    14_000.0,
                    30_000.0,
                    2_000.0,
                    3_000.0,
                    1_000.0,
                    36_000.0,
                    50_000.0
                )
            ])

            # =================================================
            # SALES
            # =================================================

            conn.executemany("""
                INSERT INTO sales (
                    company_product_id,
                    customer_id,
                    year,
                    month,
                    sales_quantity,
                    returned_quantity,
                    sale_price_excluding_tax_and_discounts,
                    customer_discount_value,
                    sales_value_excluding_tax_and_discounts,
                    sales_value_including_tax_and_discounts
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_cardiovex_cp,
                    nile_sunrise_customer,
                    2026,
                    1,
                    700,
                    20,
                    45.0,
                    1000.0,
                    31_500.0,
                    34_650.0
                ),
                (
                    nile_respira_cp,
                    nile_green_customer,
                    2026,
                    1,
                    300,
                    5,
                    120.0,
                    750.0,
                    36_000.0,
                    39_600.0
                ),
                (
                    delta_painrelief_cp,
                    delta_sunrise_customer,
                    2026,
                    1,
                    600,
                    10,
                    32.0,
                    500.0,
                    19_200.0,
                    21_120.0
                )
            ])

            # =================================================
            # TENDERS
            # =================================================

            conn.execute("""
                INSERT INTO tenders (
                    company_id,
                    contractual_operation_type,
                    tendering_entity_name,
                    tender_date
                )
                VALUES (?, ?, ?, ?);
            """, (
                nile_id,
                "Tender",
                "Fictional Medical Authority",
                "2026-02-15"
            ))

            tender_id = conn.execute(
                "SELECT last_insert_rowid();"
            ).fetchone()[0]

            conn.executemany("""
                INSERT INTO tender_items (
                    tender_id,
                    company_product_id,
                    price_excluding_tax,
                    sales_quantity,
                    sales_value_excluding_tax,
                    sales_value_including_tax
                )
                VALUES (?, ?, ?, ?, ?, ?);
            """, [
                (
                    tender_id,
                    nile_cardiovex_cp,
                    40.0,
                    1000,
                    40_000.0,
                    44_000.0
                ),
                (
                    tender_id,
                    nile_respira_cp,
                    110.0,
                    300,
                    33_000.0,
                    36_300.0
                )
            ])

            # =================================================
            # EXPORTS
            # =================================================

            conn.execute("""
                INSERT INTO exports (
                    company_product_id,
                    year,
                    month,
                    recipient_company_name,
                    destination_country,
                    export_price_excluding_tax,
                    export_quantity,
                    export_value_excluding_tax,
                    export_value_including_tax
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                delta_painrelief_cp,
                2026,
                2,
                "Synthetic Overseas Distributor",
                "Example Republic",
                35.0,
                400,
                14_000.0,
                15_400.0
            ))

            # =================================================
            # STORAGE CAPACITY
            # =================================================

            conn.executemany("""
                INSERT INTO storage_capacity (
                    warehouse_id,
                    year,
                    storage_capacity
                )
                VALUES (?, ?, ?);
            """, [
                (
                    nile_warehouse_id,
                    2026,
                    50_000.0
                ),
                (
                    delta_warehouse_id,
                    2026,
                    35_000.0
                )
            ])

            # =================================================
            # INVENTORY
            # =================================================

            conn.executemany("""
                INSERT INTO inventory (
                    warehouse_id,
                    company_product_id,
                    year,
                    inventory_quantity,
                    inventory_value_excluding_tax,
                    inventory_value_including_tax
                )
                VALUES (?, ?, ?, ?, ?, ?);
            """, [
                (
                    nile_warehouse_id,
                    nile_cardiovex_cp,
                    2026,
                    1200,
                    36_000.0,
                    39_600.0
                ),
                (
                    delta_warehouse_id,
                    delta_painrelief_cp,
                    2026,
                    900,
                    18_000.0,
                    19_800.0
                )
            ])

        print("Synthetic demo data populated successfully.")

    except sqlite3.Error as error:
        print(f"Population failed: {error}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    populate_database()
