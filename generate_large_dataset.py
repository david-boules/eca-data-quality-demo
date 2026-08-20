"""Generate a larger fully synthetic dataset for the ECA demo schema.

This script creates a separate SQLite database (default: eca_demo_large.db)
using SCHEMA_SQL from create_database.py and populates it with deterministic,
fictional data. It is intended for demonstration/testing only, not benchmarking
or production use.

Example:
    python generate_large_dataset.py --companies 1000 --overwrite
"""

from __future__ import annotations

import argparse
import random
import sqlite3
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from create_database import SCHEMA_SQL  # noqa: E402


ACTIVITIES = [
    "Distribution",
    "Importing",
    "Exporting",
    "Wholesale",
    "Warehousing",
]
COMPANY_TYPES = [
    "Joint Stock Company",
    "Limited Liability Company",
    "Partnership",
]
SECTORS = [
    "Pharmaceutical Distribution",
    "Medical Supplies Distribution",
    "Healthcare Products Distribution",
]
CUSTOMER_TYPES = ["Pharmacy", "Hospital", "Medical Center", "Wholesaler"]
AREAS = ["Area A", "Area B", "Area C", "Area D", "Area E"]
GOVERNORATES = ["Cairo", "Giza", "Alexandria", "Dakahlia", "Sharqia"]
SOURCES = ["Local", "Imported"]
PRODUCT_TYPES = ["Generic", "Originator"]
DISPENSING = ["Prescribed", "OTC"]
COUNTRIES = [f"Synthetic Country {i:02d}" for i in range(1, 21)]


def maybe_none(rng: random.Random, value, probability: float = 0.08):
    return None if rng.random() < probability else value


def money(rng: random.Random, low: float, high: float) -> float:
    return round(rng.uniform(low, high), 2)


def create_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def insert_product_catalog(conn: sqlite3.Connection, rng: random.Random, count: int) -> list[int]:
    rows = []
    for i in range(1, count + 1):
        rows.append(
            (
                f"Synthetic Product {i:04d}",
                f"Brand {i:04d}",
                f"{rng.choice([5, 10, 20, 50, 100, 250, 500])}mg synthetic formulation",
                f"Synthetic License Holder {(i % 80) + 1:03d}",
                f"Synthetic Manufacturer {(i % 120) + 1:03d}",
                rng.choice(SOURCES),
                rng.choice(PRODUCT_TYPES),
                rng.choice(DISPENSING),
                "Registered",
                "Synthetic Registration Authority",
                maybe_none(rng, f"Synthetic therapeutic purpose {(i % 25) + 1}"),
                maybe_none(rng, f"Synthetic Compound {(i % 60) + 1:02d}"),
            )
        )

    conn.executemany(
        """
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
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )

    product_ids = [row[0] for row in conn.execute("SELECT product_id FROM products ORDER BY product_id;")]

    alternative_rows = []
    for product_id in product_ids:
        if rng.random() < 0.30:
            alternative_rows.append(
                (
                    product_id,
                    f"Synthetic Alternative {product_id:04d}",
                    f"Alternative Manufacturer {(product_id % 75) + 1:03d}",
                )
            )
    if alternative_rows:
        conn.executemany(
            """
            INSERT INTO product_alternatives (
                product_id,
                alternative_product_name,
                alternative_product_manufacturer
            ) VALUES (?, ?, ?);
            """,
            alternative_rows,
        )

    return product_ids


def insert_suppliers(conn: sqlite3.Connection, count: int) -> list[int]:
    conn.executemany(
        "INSERT INTO suppliers (supplier_name) VALUES (?);",
        [(f"Synthetic Supplier {i:03d}",) for i in range(1, count + 1)],
    )
    return [row[0] for row in conn.execute("SELECT supplier_id FROM suppliers ORDER BY supplier_id;")]


def generate_dataset(
    db_path: Path,
    company_count: int,
    product_count: int,
    supplier_count: int,
    seed: int,
    overwrite: bool,
) -> None:
    if db_path.exists():
        if not overwrite:
            raise FileExistsError(
                f"{db_path} already exists. Use --overwrite to recreate it."
            )
        db_path.unlink()

    rng = random.Random(seed)
    start = time.perf_counter()
    conn = create_connection(db_path)

    try:
        conn.executescript(SCHEMA_SQL)

        with conn:
            product_ids = insert_product_catalog(conn, rng, product_count)
            supplier_ids = insert_suppliers(conn, supplier_count)

            for company_num in range(1, company_count + 1):
                company_name = f"Synthetic Company {company_num:04d}"
                establishment_year = rng.randint(1985, 2025)

                cursor = conn.execute(
                    """
                    INSERT INTO companies (
                        company_name,
                        market_or_sector,
                        establishment_year,
                        company_type,
                        contact_details
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        company_name,
                        rng.choice(SECTORS),
                        establishment_year,
                        rng.choice(COMPANY_TYPES),
                        maybe_none(
                            rng,
                            f"company{company_num:04d}@synthetic.example",
                            0.12,
                        ),
                    ),
                )
                company_id = cursor.lastrowid

                # 1-3 annual financial records. Some optional values are left NULL.
                years = rng.sample([2024, 2025, 2026], k=rng.randint(1, 3))
                financial_rows = []
                for year in sorted(years):
                    issued = money(rng, 2_000_000, 80_000_000)
                    paid = round(issued * rng.uniform(0.60, 1.00), 2)
                    assets = money(rng, 5_000_000, 300_000_000)
                    revenue = money(rng, 3_000_000, 450_000_000)
                    liabilities = round(assets * rng.uniform(0.15, 0.75), 2)
                    expenses = round(revenue * rng.uniform(0.45, 0.95), 2)
                    financial_rows.append(
                        (
                            company_id,
                            year,
                            maybe_none(rng, issued, 0.05),
                            maybe_none(rng, paid, 0.05),
                            maybe_none(rng, assets, 0.05),
                            maybe_none(rng, revenue, 0.05),
                            maybe_none(rng, liabilities, 0.05),
                            maybe_none(rng, expenses, 0.05),
                        )
                    )
                conn.executemany(
                    """
                    INSERT INTO company_financials (
                        company_id, year, issued_capital, paid_in_capital,
                        total_assets, annual_revenue, total_liabilities, total_expenses
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    financial_rows,
                )

                activities = rng.sample(ACTIVITIES, k=rng.randint(1, min(3, len(ACTIVITIES))))
                conn.executemany(
                    "INSERT INTO company_activities (company_id, activity_name) VALUES (?, ?);",
                    [(company_id, activity) for activity in activities],
                )

                related_count = rng.choices([0, 1, 2], weights=[0.45, 0.40, 0.15], k=1)[0]
                if related_count:
                    conn.executemany(
                        """
                        INSERT INTO related_parties (
                            company_id, related_party_name, contact_details
                        ) VALUES (?, ?, ?);
                        """,
                        [
                            (
                                company_id,
                                f"Synthetic Related Party {company_num:04d}-{j:02d}",
                                maybe_none(
                                    rng,
                                    f"related{company_num:04d}_{j:02d}@synthetic.example",
                                    0.20,
                                ),
                            )
                            for j in range(1, related_count + 1)
                        ],
                    )

                # Company-product bridge demonstrates many-to-many reuse of the catalog.
                selected_products = rng.sample(product_ids, k=rng.randint(4, 10))
                conn.executemany(
                    "INSERT INTO company_products (company_id, product_id) VALUES (?, ?);",
                    [(company_id, product_id) for product_id in selected_products],
                )
                company_products = [
                    row[0]
                    for row in conn.execute(
                        "SELECT company_product_id FROM company_products WHERE company_id = ?;",
                        (company_id,),
                    )
                ]

                customer_ids = []
                customer_count = rng.randint(5, 15)
                for j in range(1, customer_count + 1):
                    start_year = rng.randint(max(2018, establishment_year), 2026)
                    start_month = rng.randint(1, 12)
                    end_date = None
                    if rng.random() < 0.12 and start_year < 2026:
                        end_year = rng.randint(start_year, 2026)
                        min_end_month = start_month if end_year == start_year else 1
                        end_month = rng.randint(min_end_month, 12)
                        end_date = f"{end_year:04d}-{end_month:02d}-01"
                    cursor = conn.execute(
                        """
                        INSERT INTO customers (
                            company_id, customer_name, customer_type, customer_code,
                            branch_area, governorate, relationship_start_date,
                            relationship_end_date, phone_number
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            company_id,
                            f"Synthetic Customer {company_num:04d}-{j:03d}",
                            rng.choice(CUSTOMER_TYPES),
                            f"C{company_num:04d}-{j:03d}",
                            rng.choice(AREAS),
                            rng.choice(GOVERNORATES),
                            f"{start_year:04d}-{start_month:02d}-01",
                            end_date,
                            maybe_none(rng, f"010{company_num % 10000:04d}{j:04d}"[:11], 0.10),
                        ),
                    )
                    customer_ids.append(cursor.lastrowid)

                warehouse_ids = []
                for j in range(1, rng.randint(1, 3) + 1):
                    cursor = conn.execute(
                        """
                        INSERT INTO warehouses (
                            company_id, warehouse_name, warehouse_area
                        ) VALUES (?, ?, ?);
                        """,
                        (
                            company_id,
                            f"Warehouse {company_num:04d}-{j:02d}",
                            rng.choice(AREAS),
                        ),
                    )
                    warehouse_ids.append(cursor.lastrowid)

                # Annual capacity for each warehouse.
                conn.executemany(
                    """
                    INSERT INTO storage_capacity (
                        warehouse_id, year, storage_capacity
                    ) VALUES (?, ?, ?);
                    """,
                    [
                        (warehouse_id, 2026, money(rng, 5_000, 150_000))
                        for warehouse_id in warehouse_ids
                    ],
                )

                # Local purchases.
                for _ in range(rng.randint(3, 8)):
                    cp_id = rng.choice(company_products)
                    supplier_id = rng.choice(supplier_ids)
                    month = rng.randint(1, 12)
                    quantity = rng.randint(100, 10_000)
                    unit_price = money(rng, 5, 500)
                    gross = round(quantity * unit_price, 2)
                    discount = round(gross * rng.uniform(0, 0.08), 2)
                    excl = round(gross - discount, 2)
                    incl = round(excl * rng.uniform(1.05, 1.15), 2)
                    conn.execute(
                        """
                        INSERT INTO purchases (
                            company_product_id, supplier_id, year, month, quantity,
                            discount_value, price_excluding_tax_and_discounts,
                            purchase_value_excluding_tax_and_discounts,
                            purchase_value_including_tax_and_discounts
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            cp_id,
                            supplier_id,
                            2026,
                            month,
                            quantity,
                            discount,
                            unit_price,
                            excl,
                            incl,
                        ),
                    )

                # Imports are absent for many companies by design.
                if rng.random() < 0.65:
                    for _ in range(rng.randint(1, 4)):
                        cp_id = rng.choice(company_products)
                        supplier_id = rng.choice(supplier_ids)
                        quantity = rng.randint(100, 5_000)
                        cif = money(rng, 10, 700)
                        gross = round(quantity * cif, 2)
                        discount = round(gross * rng.uniform(0, 0.05), 2)
                        conn.execute(
                            """
                            INSERT INTO imports (
                                company_product_id, supplier_id, year, month,
                                country_of_origin, cif_import_price, quantity,
                                discount_value, purchase_value
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                cp_id,
                                supplier_id,
                                2026,
                                rng.randint(1, 12),
                                rng.choice(COUNTRIES),
                                cif,
                                quantity,
                                discount,
                                round(gross - discount, 2),
                            ),
                        )

                # Monthly cost records for selected products.
                for cp_id in rng.sample(company_products, k=min(len(company_products), rng.randint(2, 5))):
                    wages = money(rng, 2_000, 50_000)
                    finance = money(rng, 500, 15_000)
                    admin = money(rng, 500, 20_000)
                    other_fixed = money(rng, 0, 8_000)
                    fixed_total = round(wages + finance + admin + other_fixed, 2)
                    drug = money(rng, 5_000, 180_000)
                    energy = money(rng, 500, 15_000)
                    transport = money(rng, 500, 25_000)
                    other_variable = money(rng, 0, 10_000)
                    variable_total = round(drug + energy + transport + other_variable, 2)
                    conn.execute(
                        """
                        INSERT INTO costs (
                            company_product_id, year, month, wages_and_salaries,
                            financing_and_banking_costs, administrative_expenses,
                            other_fixed_costs, total_fixed_cost, drug_purchase_cost,
                            energy_cost, transport_cost, other_variable_costs,
                            total_variable_cost, total_production_cost
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            cp_id,
                            2026,
                            rng.randint(1, 12),
                            wages,
                            finance,
                            admin,
                            other_fixed,
                            fixed_total,
                            drug,
                            energy,
                            transport,
                            other_variable,
                            variable_total,
                            round(fixed_total + variable_total, 2),
                        ),
                    )

                # Sales are generated only using customers from the same company.
                for _ in range(rng.randint(10, 25)):
                    cp_id = rng.choice(company_products)
                    customer_id = rng.choice(customer_ids)
                    quantity = rng.randint(20, 2_000)
                    returns = rng.randint(0, min(quantity, max(1, quantity // 20)))
                    unit_price = money(rng, 8, 900)
                    gross = round(quantity * unit_price, 2)
                    discount = round(gross * rng.uniform(0, 0.10), 2)
                    excl = round(gross - discount, 2)
                    incl = round(excl * rng.uniform(1.05, 1.15), 2)
                    conn.execute(
                        """
                        INSERT INTO sales (
                            company_product_id, customer_id, year, month,
                            sales_quantity, returned_quantity,
                            sale_price_excluding_tax_and_discounts,
                            customer_discount_value,
                            sales_value_excluding_tax_and_discounts,
                            sales_value_including_tax_and_discounts
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            cp_id,
                            customer_id,
                            2026,
                            rng.randint(1, 12),
                            quantity,
                            returns,
                            unit_price,
                            discount,
                            excl,
                            incl,
                        ),
                    )

                # Optional tenders with one or more items from this company.
                if rng.random() < 0.55:
                    for tender_num in range(1, rng.randint(1, 3) + 1):
                        cursor = conn.execute(
                            """
                            INSERT INTO tenders (
                                company_id, contractual_operation_type,
                                tendering_entity_name, tender_date
                            ) VALUES (?, ?, ?, ?);
                            """,
                            (
                                company_id,
                                rng.choice(["Tender", "Contractual Operation"]),
                                f"Synthetic Tendering Entity {rng.randint(1, 80):03d}",
                                f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
                            ),
                        )
                        tender_id = cursor.lastrowid
                        selected_cp = rng.sample(
                            company_products,
                            k=min(len(company_products), rng.randint(1, 3)),
                        )
                        for cp_id in selected_cp:
                            quantity = rng.randint(50, 5_000)
                            price = money(rng, 5, 850)
                            excl = round(quantity * price, 2)
                            conn.execute(
                                """
                                INSERT INTO tender_items (
                                    tender_id, company_product_id, price_excluding_tax,
                                    sales_quantity, sales_value_excluding_tax,
                                    sales_value_including_tax
                                ) VALUES (?, ?, ?, ?, ?, ?);
                                """,
                                (
                                    tender_id,
                                    cp_id,
                                    price,
                                    quantity,
                                    excl,
                                    round(excl * rng.uniform(1.05, 1.15), 2),
                                ),
                            )

                # Optional exports.
                if rng.random() < 0.45:
                    for _ in range(rng.randint(1, 3)):
                        cp_id = rng.choice(company_products)
                        quantity = rng.randint(50, 4_000)
                        price = money(rng, 10, 1_000)
                        excl = round(quantity * price, 2)
                        conn.execute(
                            """
                            INSERT INTO exports (
                                company_product_id, year, month,
                                recipient_company_name, destination_country,
                                export_price_excluding_tax, export_quantity,
                                export_value_excluding_tax, export_value_including_tax
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                            """,
                            (
                                cp_id,
                                2026,
                                rng.randint(1, 12),
                                f"Synthetic Overseas Customer {rng.randint(1, 500):04d}",
                                rng.choice(COUNTRIES),
                                price,
                                quantity,
                                excl,
                                round(excl * rng.uniform(1.05, 1.15), 2),
                            ),
                        )

                # Inventory uses only warehouse/product combinations owned by this company.
                used_inventory_pairs: set[tuple[int, int]] = set()
                inventory_target = rng.randint(2, min(8, len(company_products) * len(warehouse_ids)))
                while len(used_inventory_pairs) < inventory_target:
                    pair = (rng.choice(warehouse_ids), rng.choice(company_products))
                    if pair in used_inventory_pairs:
                        continue
                    used_inventory_pairs.add(pair)
                    warehouse_id, cp_id = pair
                    quantity = rng.randint(0, 15_000)
                    unit_value = money(rng, 5, 500)
                    excl = round(quantity * unit_value, 2)
                    conn.execute(
                        """
                        INSERT INTO inventory (
                            warehouse_id, company_product_id, year,
                            inventory_quantity, inventory_value_excluding_tax,
                            inventory_value_including_tax
                        ) VALUES (?, ?, ?, ?, ?, ?);
                        """,
                        (
                            warehouse_id,
                            cp_id,
                            2026,
                            quantity,
                            excl,
                            round(excl * rng.uniform(1.05, 1.15), 2),
                        ),
                    )

                if company_num % 100 == 0 or company_num == company_count:
                    print(f"Generated {company_num:,}/{company_count:,} companies...")

        validation = validate_generated_database(conn)
        elapsed = time.perf_counter() - start
        print_summary(conn, db_path, company_count, product_count, supplier_count, seed, elapsed, validation)

    finally:
        conn.close()


def validate_generated_database(conn: sqlite3.Connection) -> dict[str, int | str]:
    integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    fk_violations = len(conn.execute("PRAGMA foreign_key_check;").fetchall())

    sales_mismatches = conn.execute(
        """
        SELECT COUNT(*)
        FROM sales AS s
        JOIN company_products AS cp ON s.company_product_id = cp.company_product_id
        JOIN customers AS cu ON s.customer_id = cu.customer_id
        WHERE cp.company_id <> cu.company_id;
        """
    ).fetchone()[0]

    tender_mismatches = conn.execute(
        """
        SELECT COUNT(*)
        FROM tender_items AS ti
        JOIN tenders AS t ON ti.tender_id = t.tender_id
        JOIN company_products AS cp ON ti.company_product_id = cp.company_product_id
        WHERE t.company_id <> cp.company_id;
        """
    ).fetchone()[0]

    inventory_mismatches = conn.execute(
        """
        SELECT COUNT(*)
        FROM inventory AS i
        JOIN warehouses AS w ON i.warehouse_id = w.warehouse_id
        JOIN company_products AS cp ON i.company_product_id = cp.company_product_id
        WHERE w.company_id <> cp.company_id;
        """
    ).fetchone()[0]

    return {
        "integrity": integrity,
        "fk_violations": fk_violations,
        "sales_mismatches": sales_mismatches,
        "tender_mismatches": tender_mismatches,
        "inventory_mismatches": inventory_mismatches,
    }


def print_summary(
    conn: sqlite3.Connection,
    db_path: Path,
    company_count: int,
    product_count: int,
    supplier_count: int,
    seed: int,
    elapsed: float,
    validation: dict[str, int | str],
) -> None:
    tables = [
        row[0]
        for row in conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
            """
        )
    ]
    counts = {table: conn.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0] for table in tables}
    total_rows = sum(counts.values())

    print("\n" + "=" * 68)
    print("LARGE SYNTHETIC DATASET GENERATED")
    print("=" * 68)
    print(f"Database:                {db_path}")
    print(f"Random seed:             {seed}")
    print(f"Requested companies:     {company_count:,}")
    print(f"Global products:         {product_count:,}")
    print(f"Global suppliers:        {supplier_count:,}")
    print(f"Total rows (all tables): {total_rows:,}")
    print(f"Generation time:         {elapsed:.2f} seconds")
    print("\nValidation")
    print(f"  SQLite integrity:      {validation['integrity']}")
    print(f"  FK violations:         {validation['fk_violations']}")
    print(f"  Sales mismatches:      {validation['sales_mismatches']}")
    print(f"  Tender mismatches:     {validation['tender_mismatches']}")
    print(f"  Inventory mismatches:  {validation['inventory_mismatches']}")
    print("\nRow counts")
    for table, count in counts.items():
        print(f"  {table:<22} {count:>10,}")
    print("=" * 68)
    print("All records are synthetic and intended for demonstration only.")
    print("This is not a scalability or production-performance benchmark.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a larger fully synthetic SQLite dataset for the ECA demo schema."
    )
    parser.add_argument(
        "--companies",
        type=int,
        default=1000,
        help="Number of synthetic companies to generate (default: 1000).",
    )
    parser.add_argument(
        "--products",
        type=int,
        default=None,
        help="Size of shared product catalog. Default scales with company count.",
    )
    parser.add_argument(
        "--suppliers",
        type=int,
        default=None,
        help="Number of shared suppliers. Default scales with company count.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260818,
        help="Random seed for reproducible generation.",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=SCRIPT_DIR / "eca_demo_large.db",
        help="Output SQLite database path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete and recreate the output database if it already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.companies < 1:
        raise ValueError("--companies must be at least 1")

    product_count = args.products or max(100, min(2000, args.companies // 2))
    supplier_count = args.suppliers or max(25, min(250, args.companies // 10))

    if product_count < 10:
        raise ValueError("--products must be at least 10")
    if supplier_count < 1:
        raise ValueError("--suppliers must be at least 1")

    generate_dataset(
        db_path=args.db,
        company_count=args.companies,
        product_count=product_count,
        supplier_count=supplier_count,
        seed=args.seed,
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
