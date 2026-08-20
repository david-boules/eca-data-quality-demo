"""Explicit synthetic workbook-to-database mapping for Phase 2.

Workbook labels live here so generator and importer do not scatter Excel names
throughout their implementations.  Product names and supplier names are stable
business keys only within the controlled synthetic dataset.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SheetMapping:
    name: str
    table: str
    columns: tuple[str, ...]
    required: tuple[str, ...]


SHEETS: dict[str, SheetMapping] = {
    "Company Info": SheetMapping("Company Info", "companies", (
        "company_name", "market_or_sector", "establishment_year", "company_type", "contact_details"
    ), ("company_name",)),
    "Financials": SheetMapping("Financials", "company_financials", (
        "year", "issued_capital", "paid_in_capital", "total_assets", "annual_revenue",
        "total_liabilities", "total_expenses"
    ), ("year",)),
    "Activities": SheetMapping("Activities", "company_activities", ("activity_name",), ("activity_name",)),
    "Related Parties": SheetMapping("Related Parties", "related_parties", (
        "related_party_name", "contact_details"
    ), ("related_party_name",)),
    "Products": SheetMapping("Products", "products", (
        "product_name", "brand_name", "product_specifications", "license_holder_company",
        "manufacturer_company", "product_source", "product_type", "dispensing_method",
        "registration_status", "registration_authority", "therapeutic_purpose", "active_ingredient",
        "alternative_product_name", "alternative_product_manufacturer"
    ), ("product_name",)),
    "Customers": SheetMapping("Customers", "customers", (
        "customer_name", "customer_type", "customer_code", "branch_area", "governorate",
        "relationship_start_date", "relationship_end_date", "phone_number"
    ), ("customer_name", "customer_code")),
    "Imports": SheetMapping("Imports", "imports", (
        "product_name", "supplier_name", "year", "month", "country_of_origin", "cif_import_price",
        "quantity", "discount_value", "purchase_value"
    ), ("product_name", "supplier_name", "year", "month")),
    "Local Purchases": SheetMapping("Local Purchases", "purchases", (
        "product_name", "supplier_name", "year", "month", "quantity", "discount_value",
        "price_excluding_tax_and_discounts", "purchase_value_excluding_tax_and_discounts",
        "purchase_value_including_tax_and_discounts"
    ), ("product_name", "supplier_name", "year", "month")),
    "Costs": SheetMapping("Costs", "costs", (
        "product_name", "year", "month", "wages_and_salaries", "financing_and_banking_costs",
        "administrative_expenses", "other_fixed_costs", "total_fixed_cost", "drug_purchase_cost",
        "energy_cost", "transport_cost", "other_variable_costs", "total_variable_cost",
        "total_production_cost"
    ), ("product_name", "year", "month")),
    "Sales": SheetMapping("Sales", "sales", (
        "product_name", "customer_code", "year", "month", "sales_quantity", "returned_quantity",
        "sale_price_excluding_tax_and_discounts", "customer_discount_value",
        "sales_value_excluding_tax_and_discounts", "sales_value_including_tax_and_discounts"
    ), ("product_name", "customer_code", "year", "month")),
    "Tenders": SheetMapping("Tenders", "tenders+tender_items", (
        "tender_key", "contractual_operation_type", "tendering_entity_name", "tender_date",
        "product_name", "price_excluding_tax", "sales_quantity", "sales_value_excluding_tax",
        "sales_value_including_tax"
    ), ("tender_key", "tendering_entity_name", "product_name")),
    "Exports": SheetMapping("Exports", "exports", (
        "product_name", "year", "month", "recipient_company_name", "destination_country",
        "export_price_excluding_tax", "export_quantity", "export_value_excluding_tax",
        "export_value_including_tax"
    ), ("product_name", "year", "month")),
    "Storage Capacity": SheetMapping("Storage Capacity", "warehouses+storage_capacity", (
        "warehouse_name", "warehouse_area", "year", "storage_capacity"
    ), ("warehouse_name", "year", "storage_capacity")),
    "Inventory": SheetMapping("Inventory", "inventory", (
        "warehouse_name", "product_name", "year", "inventory_quantity",
        "inventory_value_excluding_tax", "inventory_value_including_tax"
    ), ("warehouse_name", "product_name", "year")),
}

REQUIRED_SHEETS = tuple(SHEETS)
INTEGER_FIELDS = {"establishment_year", "year", "month", "quantity", "sales_quantity",
                  "returned_quantity", "export_quantity", "inventory_quantity"}
NONNEGATIVE_FIELDS = {
    "issued_capital", "paid_in_capital", "total_assets", "annual_revenue", "total_liabilities",
    "total_expenses", "cif_import_price", "quantity", "discount_value", "purchase_value",
    "price_excluding_tax_and_discounts", "purchase_value_excluding_tax_and_discounts",
    "purchase_value_including_tax_and_discounts", "wages_and_salaries", "financing_and_banking_costs",
    "administrative_expenses", "other_fixed_costs", "total_fixed_cost", "drug_purchase_cost",
    "energy_cost", "transport_cost", "other_variable_costs", "total_variable_cost",
    "total_production_cost", "sales_quantity", "returned_quantity",
    "sale_price_excluding_tax_and_discounts", "customer_discount_value",
    "sales_value_excluding_tax_and_discounts", "sales_value_including_tax_and_discounts",
    "price_excluding_tax", "export_price_excluding_tax", "export_quantity",
    "export_value_excluding_tax", "export_value_including_tax", "storage_capacity",
    "inventory_quantity", "inventory_value_excluding_tax", "inventory_value_including_tax",
}

