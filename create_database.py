
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "eca_demo.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    market_or_sector TEXT,
    establishment_year INTEGER,
    company_type TEXT,
    contact_details TEXT
);


CREATE TABLE IF NOT EXISTS company_financials (
    financial_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    issued_capital NUMERIC CHECK (issued_capital IS NULL OR issued_capital >= 0),
    paid_in_capital NUMERIC CHECK (paid_in_capital IS NULL OR paid_in_capital >= 0),
    total_assets NUMERIC CHECK (total_assets IS NULL OR total_assets >= 0),
    annual_revenue NUMERIC CHECK (annual_revenue IS NULL OR annual_revenue >= 0),
    total_liabilities NUMERIC CHECK (total_liabilities IS NULL OR total_liabilities >= 0),
    total_expenses NUMERIC CHECK (total_expenses IS NULL OR total_expenses >= 0),

    UNIQUE (company_id, year),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS company_activities (
    activity_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    activity_name TEXT NOT NULL,

    UNIQUE (company_id, activity_name),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS related_parties (
    related_party_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    related_party_name TEXT NOT NULL,
    contact_details TEXT,

    UNIQUE (company_id, related_party_name),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY,
    product_name TEXT NOT NULL,
    brand_name TEXT,
    product_specifications TEXT,
    license_holder_company TEXT,
    manufacturer_company TEXT,
    product_source TEXT,
    product_type TEXT,
    dispensing_method TEXT,
    registration_status TEXT,
    registration_authority TEXT,
    therapeutic_purpose TEXT,
    active_ingredient TEXT
);


CREATE TABLE IF NOT EXISTS product_alternatives (
    product_alternative_id INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    alternative_product_name TEXT NOT NULL,
    alternative_product_manufacturer TEXT,

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS company_products (
    company_product_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,

    UNIQUE (company_id, product_id),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    customer_name TEXT NOT NULL,
    customer_type TEXT,
    customer_code TEXT,
    branch_area TEXT,
    governorate TEXT,
    relationship_start_date TEXT,
    relationship_end_date TEXT,
    phone_number TEXT,

    UNIQUE (company_id, customer_code),

    CHECK (
        relationship_end_date IS NULL
        OR relationship_start_date IS NULL
        OR relationship_end_date >= relationship_start_date
    ),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY,
    supplier_name TEXT NOT NULL UNIQUE
);


CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    warehouse_name TEXT NOT NULL,
    warehouse_area TEXT,

    UNIQUE (company_id, warehouse_name),

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS imports (
    import_id INTEGER PRIMARY KEY,
    company_product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    country_of_origin TEXT,
    cif_import_price NUMERIC CHECK (cif_import_price IS NULL OR cif_import_price >= 0),
    quantity INTEGER CHECK (quantity IS NULL OR quantity >= 0),
    discount_value NUMERIC CHECK (discount_value IS NULL OR discount_value >= 0),
    purchase_value NUMERIC CHECK (purchase_value IS NULL OR purchase_value >= 0),

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS purchases (
    purchase_id INTEGER PRIMARY KEY,
    company_product_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    quantity INTEGER CHECK (quantity IS NULL OR quantity >= 0),
    discount_value NUMERIC CHECK (discount_value IS NULL OR discount_value >= 0),
    price_excluding_tax_and_discounts NUMERIC
        CHECK (
            price_excluding_tax_and_discounts IS NULL
            OR price_excluding_tax_and_discounts >= 0
        ),
    purchase_value_excluding_tax_and_discounts NUMERIC
        CHECK (
            purchase_value_excluding_tax_and_discounts IS NULL
            OR purchase_value_excluding_tax_and_discounts >= 0
        ),
    purchase_value_including_tax_and_discounts NUMERIC
        CHECK (
            purchase_value_including_tax_and_discounts IS NULL
            OR purchase_value_including_tax_and_discounts >= 0
        ),

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS costs (
    cost_id INTEGER PRIMARY KEY,
    company_product_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),

    wages_and_salaries NUMERIC CHECK (wages_and_salaries IS NULL OR wages_and_salaries >= 0),
    financing_and_banking_costs NUMERIC
        CHECK (
            financing_and_banking_costs IS NULL
            OR financing_and_banking_costs >= 0
        ),
    administrative_expenses NUMERIC
        CHECK (
            administrative_expenses IS NULL
            OR administrative_expenses >= 0
        ),
    other_fixed_costs NUMERIC CHECK (other_fixed_costs IS NULL OR other_fixed_costs >= 0),
    total_fixed_cost NUMERIC CHECK (total_fixed_cost IS NULL OR total_fixed_cost >= 0),

    drug_purchase_cost NUMERIC CHECK (drug_purchase_cost IS NULL OR drug_purchase_cost >= 0),
    energy_cost NUMERIC CHECK (energy_cost IS NULL OR energy_cost >= 0),
    transport_cost NUMERIC CHECK (transport_cost IS NULL OR transport_cost >= 0),
    other_variable_costs NUMERIC
        CHECK (
            other_variable_costs IS NULL
            OR other_variable_costs >= 0
        ),
    total_variable_cost NUMERIC
        CHECK (
            total_variable_cost IS NULL
            OR total_variable_cost >= 0
        ),

    total_production_cost NUMERIC
        CHECK (
            total_production_cost IS NULL
            OR total_production_cost >= 0
        ),

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS sales (
    sale_id INTEGER PRIMARY KEY,
    company_product_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),

    sales_quantity INTEGER CHECK (sales_quantity IS NULL OR sales_quantity >= 0),
    returned_quantity INTEGER
        CHECK (returned_quantity IS NULL OR returned_quantity >= 0),

    sale_price_excluding_tax_and_discounts NUMERIC
        CHECK (
            sale_price_excluding_tax_and_discounts IS NULL
            OR sale_price_excluding_tax_and_discounts >= 0
        ),

    customer_discount_value NUMERIC
        CHECK (
            customer_discount_value IS NULL
            OR customer_discount_value >= 0
        ),

    sales_value_excluding_tax_and_discounts NUMERIC
        CHECK (
            sales_value_excluding_tax_and_discounts IS NULL
            OR sales_value_excluding_tax_and_discounts >= 0
        ),

    sales_value_including_tax_and_discounts NUMERIC
        CHECK (
            sales_value_including_tax_and_discounts IS NULL
            OR sales_value_including_tax_and_discounts >= 0
        ),

    CHECK (
        returned_quantity IS NULL
        OR sales_quantity IS NULL
        OR returned_quantity <= sales_quantity
    ),

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS tenders (
    tender_id INTEGER PRIMARY KEY,
    company_id INTEGER NOT NULL,
    contractual_operation_type TEXT,
    tendering_entity_name TEXT NOT NULL,
    tender_date TEXT,

    FOREIGN KEY (company_id)
        REFERENCES companies(company_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS tender_items (
    tender_item_id INTEGER PRIMARY KEY,
    tender_id INTEGER NOT NULL,
    company_product_id INTEGER NOT NULL,

    price_excluding_tax NUMERIC
        CHECK (price_excluding_tax IS NULL OR price_excluding_tax >= 0),

    sales_quantity INTEGER
        CHECK (sales_quantity IS NULL OR sales_quantity >= 0),

    sales_value_excluding_tax NUMERIC
        CHECK (
            sales_value_excluding_tax IS NULL
            OR sales_value_excluding_tax >= 0
        ),

    sales_value_including_tax NUMERIC
        CHECK (
            sales_value_including_tax IS NULL
            OR sales_value_including_tax >= 0
        ),

    FOREIGN KEY (tender_id)
        REFERENCES tenders(tender_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS exports (
    export_id INTEGER PRIMARY KEY,
    company_product_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),

    recipient_company_name TEXT,
    destination_country TEXT,

    export_price_excluding_tax NUMERIC
        CHECK (
            export_price_excluding_tax IS NULL
            OR export_price_excluding_tax >= 0
        ),

    export_quantity INTEGER
        CHECK (
            export_quantity IS NULL
            OR export_quantity >= 0
        ),

    export_value_excluding_tax NUMERIC
        CHECK (
            export_value_excluding_tax IS NULL
            OR export_value_excluding_tax >= 0
        ),

    export_value_including_tax NUMERIC
        CHECK (
            export_value_including_tax IS NULL
            OR export_value_including_tax >= 0
        ),

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS storage_capacity (
    capacity_id INTEGER PRIMARY KEY,
    warehouse_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    storage_capacity NUMERIC NOT NULL
        CHECK (storage_capacity >= 0),

    UNIQUE (warehouse_id, year),

    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY,
    warehouse_id INTEGER NOT NULL,
    company_product_id INTEGER NOT NULL,
    year INTEGER NOT NULL,

    inventory_quantity INTEGER
        CHECK (
            inventory_quantity IS NULL
            OR inventory_quantity >= 0
        ),

    inventory_value_excluding_tax NUMERIC
        CHECK (
            inventory_value_excluding_tax IS NULL
            OR inventory_value_excluding_tax >= 0
        ),

    inventory_value_including_tax NUMERIC
        CHECK (
            inventory_value_including_tax IS NULL
            OR inventory_value_including_tax >= 0
        ),

    UNIQUE (warehouse_id, company_product_id, year),

    FOREIGN KEY (warehouse_id)
        REFERENCES warehouses(warehouse_id)
        ON DELETE RESTRICT,

    FOREIGN KEY (company_product_id)
        REFERENCES company_products(company_product_id)
        ON DELETE RESTRICT
);
"""


def create_database():
    conn = get_connection()

    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()

        table_count = conn.execute("""
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%';
        """).fetchone()[0]

        print(f"Schema created successfully.")
        print(f"User tables created: {table_count}")

    except sqlite3.Error as error:
        conn.rollback()
        print(f"Database creation failed: {error}")
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    create_database()
    print(f"Database path: {DB_PATH}")
