"""Streamlit interface for the imported ECA synthetic Data Request database."""

from __future__ import annotations
import json
import csv
import io
import os
import sys
import tempfile
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parent
LOGO = ROOT / "assets" / "eca_logo.png"
GUIDE = ROOT / "SIMPLE_GUIDE.md"

st.set_page_config(page_title="ECA Data Request Database", page_icon="◢", layout="wide")
st.markdown("""
<style>
    :root { --eca-red:#e31b23; --eca-charcoal:#17191d; --eca-grey:#68707a; --eca-soft:#f4f5f7; }
    .stApp { background: #f5f6f8; color: var(--eca-charcoal); }
    [data-testid="stHeader"] { background: rgba(245,246,248,.92); border-bottom: 1px solid #e2e5e9; }
    [data-testid="stSidebar"] { background: #181b20; border-right: 4px solid var(--eca-red); }
    [data-testid="stSidebar"] * { color: #f6f7f8; }
    [data-testid="stSidebar"] [data-testid="stImage"] { background: white; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
    [data-testid="stSidebar"] hr { border-color: #343941; }
    [data-testid="stSidebar"] .stRadio label { padding: 7px 8px; border-radius: 6px; }
    [data-testid="stSidebar"] .stRadio label:hover { background: #272c33; }
    .block-container { padding-top: 2rem; max-width: 1440px; }
    h1, h2, h3 { color: var(--eca-charcoal); letter-spacing: -.02em; }
    h1 { font-weight: 760; }
    h2 { border-left: 4px solid var(--eca-red); padding-left: .65rem; margin-top: 1.5rem; }
    .eca-header { border-bottom: 1px solid #dfe2e6; padding-bottom: 1.1rem; margin-bottom: 1.3rem; }
    .eca-kicker { color: var(--eca-red); text-transform: uppercase; font-size: .76rem; font-weight: 800; letter-spacing: .12em; }
    .eca-subtitle { color: #5d6570; font-size: .98rem; margin-top: -.4rem; }
    .eca-notice { background:#fff; border:1px solid #e1e4e8; border-left:4px solid var(--eca-red); border-radius:8px; padding:.75rem 1rem; color:#4c535c; margin-bottom:1.25rem; }
    [data-testid="stMetric"] { background:#fff; border:1px solid #e0e3e7; border-top:3px solid var(--eca-red); border-radius:10px; padding:1rem 1.1rem; box-shadow:0 3px 12px rgba(20,24,28,.04); }
    [data-testid="stMetricLabel"] { color:#626a74; font-weight:650; }
    [data-testid="stMetricValue"] { color:var(--eca-charcoal); font-weight:750; }
    [data-testid="stDataFrame"] { border:1px solid #dde1e5; border-radius:9px; overflow:hidden; background:white; }
    .stButton > button, .stDownloadButton > button { background:var(--eca-red); color:white; border:0; border-radius:7px; font-weight:700; }
    .stButton > button:hover, .stDownloadButton > button:hover { background:#bd1118; color:white; border:0; }
    div[data-baseweb="select"] > div, .stTextInput input { background:white; border-color:#d8dce1; }
    [data-testid="stTabs"] button[aria-selected="true"] { color:var(--eca-red); border-bottom-color:var(--eca-red); }
    .eca-guide-intro { background:linear-gradient(135deg,#17191d,#2a2e34); color:white; padding:1.4rem 1.5rem; border-radius:12px; border-bottom:4px solid var(--eca-red); margin-bottom:1rem; }
    .eca-guide-intro h3 { color:white; margin:0 0 .35rem 0; }
    .eca-guide-intro p { margin:0; color:#d9dde2; }
    footer { visibility:hidden; }
</style>
""", unsafe_allow_html=True)

header_logo, header_title = st.columns([1.15, 4.85], vertical_alignment="center")
with header_logo:
    if LOGO.exists(): st.image(str(LOGO), width=285)
with header_title:
    st.markdown('<div class="eca-kicker">Data Request Information System</div>', unsafe_allow_html=True)
    st.title("ECA Data Request Database")
    st.markdown('<div class="eca-subtitle">Structured company submissions, validation, and market analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="eca-notice"><strong>Demonstration environment.</strong> All records are synthetic. This local prototype is not an official production system.</div>', unsafe_allow_html=True)

if LOGO.exists(): st.sidebar.image(str(LOGO), width=260)
st.sidebar.markdown("### Data Request System")
hosted_demo = os.environ.get("ECA_HOSTED_DEMO", "").lower() in {"1", "true", "yes"}
st.sidebar.caption("Hosted synthetic demo" if hosted_demo else "Phase 2 · Local prototype")
st.sidebar.markdown("[Egyptian Competition Authority website ↗](https://eca.org.eg)")
st.sidebar.divider()

expected_python = ROOT / ".venv" / "bin" / "python"
if expected_python.exists() and Path(sys.executable).resolve() != expected_python.resolve():
    st.error("The application was started with the wrong Python environment.")
    st.markdown("Use the project launcher below. It always selects the compatible environment and an available port.")
    st.code("python3 launch_app.py", language="bash")
    st.caption(f"Current interpreter: {sys.executable}")
    st.stop()

from db import Database
from import_data_requests import import_workbook
from validate_database import EXPECTED_TABLES
from data_quality import analyze_data_quality
from anomaly_detection import detect_anomalies, DEFAULT_MIN_SAMPLE_SIZE, DEFAULT_ROBUST_Z_THRESHOLD

def rows_to_csv(rows):
    if not rows: return ""
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader(); writer.writerows(rows); return output.getvalue()

default_name = "eca_demo_anomaly.db" if hosted_demo else "eca_demo.db"
default_db = os.environ.get("ECA_DB_PATH", str(ROOT / default_name))
if hosted_demo:
    db_path = Path(default_db)
    st.sidebar.info("Read-only synthetic demonstration data")
else:
    db_path = Path(st.sidebar.text_input("SQLite database", default_db))
pages = ["Overview", "Company Explorer", "Product Explorer", "Data Explorer", "Sales / Market Analysis", "Data Quality / Import Status"]
if not hosted_demo: pages.append("Import Data")
pages.append("System Guide")
page = st.sidebar.radio("Navigate", pages)
db = Database(db_path)
database_ok, database_message = db.preflight(EXPECTED_TABLES)
if not database_ok:
    st.error(database_message)
    st.markdown("Create a valid target database, or select one in the sidebar.")
    st.code(".venv/bin/python create_database.py", language="bash")
    st.stop()
companies, products, years = db.companies(), db.products(), db.years()

if page == "Overview":
    cols = st.columns(4)
    for col, label, table in zip(cols, ["Companies", "Products", "Sales records", "Customers"], ["companies", "products", "sales", "customers"]):
        col.metric(label, f"{db.scalar(f'SELECT COUNT(*) FROM {table}'):,}")
    st.write("Available years:", ", ".join(map(str, years)) or "None")
    counts = [{"dataset": t, "records": db.scalar(f"SELECT COUNT(*) FROM {t}")} for t in
              ["company_financials", "company_products", "imports", "purchases", "costs", "sales", "tenders", "exports", "inventory"]]
    st.dataframe(counts, use_container_width=True, hide_index=True)
elif page == "Company Explorer":
    if not companies:
        st.info("No companies are available yet. Import a valid synthetic Data Request workbook to begin.")
    else:
        selected = st.selectbox("Company", companies, format_func=lambda x: x["company_name"])
        cid = selected["company_id"]
        st.dataframe(db.rows("SELECT * FROM companies WHERE company_id=?", (cid,)), hide_index=True)
        queries = {
        "Financials": ("SELECT year,issued_capital,paid_in_capital,total_assets,annual_revenue,total_liabilities,total_expenses FROM company_financials WHERE company_id=? ORDER BY year", (cid,)),
        "Activities": ("SELECT activity_name FROM company_activities WHERE company_id=?", (cid,)),
        "Products": ("SELECT p.* FROM products p JOIN company_products cp ON cp.product_id=p.product_id WHERE cp.company_id=?", (cid,)),
        "Customers": ("SELECT * FROM customers WHERE company_id=?", (cid,)),
        "Sales": ("SELECT p.product_name,s.* FROM sales s JOIN company_products cp ON cp.company_product_id=s.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE cp.company_id=?", (cid,)),
        "Purchases": ("SELECT p.product_name,x.* FROM purchases x JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE cp.company_id=?", (cid,)),
        "Imports": ("SELECT p.product_name,x.* FROM imports x JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE cp.company_id=?", (cid,)),
        "Exports": ("SELECT p.product_name,x.* FROM exports x JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE cp.company_id=?", (cid,)),
        "Inventory": ("SELECT w.warehouse_name,p.product_name,i.* FROM inventory i JOIN warehouses w ON w.warehouse_id=i.warehouse_id JOIN company_products cp ON cp.company_product_id=i.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE w.company_id=?", (cid,)),
        "Tenders": ("SELECT t.*,p.product_name,ti.sales_value_including_tax FROM tenders t JOIN tender_items ti ON ti.tender_id=t.tender_id JOIN company_products cp ON cp.company_product_id=ti.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE t.company_id=?", (cid,)),
        "Costs": ("SELECT p.product_name,x.* FROM costs x JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN products p ON p.product_id=cp.product_id WHERE cp.company_id=?", (cid,)),
        "Storage": ("SELECT w.warehouse_name,w.warehouse_area,sc.year,sc.storage_capacity FROM warehouses w JOIN storage_capacity sc ON sc.warehouse_id=w.warehouse_id WHERE w.company_id=?", (cid,)),
        }
        tabs = st.tabs(list(queries))
        for tab, (name, query) in zip(tabs, queries.items()):
            with tab: st.dataframe(db.rows(*query), use_container_width=True, hide_index=True)
elif page == "Product Explorer":
    if not products:
        st.info("No products are available yet. Import company workbooks containing product records to begin.")
    else:
        selected = st.selectbox("Product", products, format_func=lambda x: x["product_name"]); pid=selected["product_id"]
        st.dataframe(db.rows("""SELECT c.company_name,COUNT(s.sale_id) sales_records,COALESCE(SUM(s.sales_value_including_tax_and_discounts),0) total_sales
        FROM company_products cp JOIN companies c ON c.company_id=cp.company_id LEFT JOIN sales s ON s.company_product_id=cp.company_product_id
        WHERE cp.product_id=? GROUP BY c.company_id ORDER BY total_sales DESC""", (pid,)), use_container_width=True, hide_index=True)
        st.write("Transaction years", [r["year"] for r in db.rows("SELECT DISTINCT s.year FROM sales s JOIN company_products cp ON cp.company_product_id=s.company_product_id WHERE cp.product_id=? ORDER BY s.year", (pid,))])
        imports = db.rows("""SELECT c.company_name,x.year,x.month,x.quantity,x.purchase_value FROM imports x
        JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN companies c ON c.company_id=cp.company_id WHERE cp.product_id=?""", (pid,))
        inventory = db.rows("""SELECT c.company_name,w.warehouse_name,x.year,x.inventory_quantity,x.inventory_value_including_tax FROM inventory x
        JOIN company_products cp ON cp.company_product_id=x.company_product_id JOIN companies c ON c.company_id=cp.company_id
        JOIN warehouses w ON w.warehouse_id=x.warehouse_id WHERE cp.product_id=?""", (pid,))
        left, right = st.columns(2)
        with left: st.subheader("Imports"); st.dataframe(imports, use_container_width=True, hide_index=True)
        with right: st.subheader("Inventory"); st.dataframe(inventory, use_container_width=True, hide_index=True)
elif page == "Data Explorer":
    allowed = db.explore_tables()
    table=st.selectbox("Dataset", allowed)
    capabilities = db.explore_capabilities(table)
    supported = [name for name, enabled in capabilities.items() if enabled]
    filter_columns = st.columns(len(supported)) if supported else []
    company_filter = product_filter = year_filter = None
    column_index = 0
    if capabilities["company"]:
        company_filter=filter_columns[column_index].selectbox("Company",[None]+companies,format_func=lambda x:"All" if x is None else x["company_name"]); column_index += 1
    if capabilities["product"]:
        product_filter=filter_columns[column_index].selectbox("Product",[None]+products,format_func=lambda x:"All" if x is None else x["product_name"]); column_index += 1
    if capabilities["year"]:
        year_filter=filter_columns[column_index].selectbox("Year",[None]+years,format_func=lambda x:"All" if x is None else str(x))
    limit=st.slider("Rows",25,500,100)
    rows=db.explore(table,None if company_filter is None else company_filter["company_id"],None if product_filter is None else product_filter["product_id"],year_filter,limit)
    st.dataframe(rows, use_container_width=True, hide_index=True)
elif page == "Sales / Market Analysis":
    if not products or not years: st.info("No imported sales data available.")
    else:
        product=st.selectbox("Product", products, format_func=lambda x:x["product_name"]); year=st.selectbox("Year", years)
        company_choice=st.selectbox("Company (optional)", [None]+companies, format_func=lambda x:"All companies" if x is None else x["company_name"])
        rows=db.sales_analysis(product["product_id"],year,None if company_choice is None else company_choice["company_id"])
        total=sum(float(row["total_sales"] or 0) for row in rows); st.metric("Total sales including tax/discounts", f"{total:,.2f}")
        if rows:
            monthly={}
            for row in rows: monthly[row["month"]]=monthly.get(row["month"],0)+float(row["total_sales"] or 0)
            chart_rows=[{"month":month,"total_sales":value} for month,value in sorted(monthly.items())]
            st.vega_lite_chart(chart_rows,{"mark":"bar","encoding":{"x":{"field":"month","type":"ordinal","title":"Month"},"y":{"field":"total_sales","type":"quantitative","title":"Total sales"}}},use_container_width=True)
            st.dataframe(rows,use_container_width=True,hide_index=True)
elif page == "Data Quality / Import Status":
    health_tab, quality_tab, anomaly_tab = st.tabs(["Database Health", "Data Quality", "Anomaly Review"])
    quality = analyze_data_quality(db_path); flags = detect_anomalies(db_path)
    with health_tab:
        fk=quality["database_health"]["foreign_key_violations"]
        left,right=st.columns(2); left.metric("Foreign-key violations",len(fk)); right.metric("SQLite integrity",quality["database_health"]["integrity"])
        if fk: st.dataframe(fk,use_container_width=True,hide_index=True)
        report=ROOT/"import_report.json"
        st.subheader("Latest import report")
        if report.exists(): st.json(json.loads(report.read_text()))
        else: st.info("No import_report.json is present.")
    with quality_tab:
        st.info("A consistency issue means stored arithmetic does not reconcile within the rounding tolerance. It is separate from a statistical anomaly.")
        issues=quality["findings"]; completeness=quality["completeness"]
        metrics=st.columns(3); metrics[0].metric("Records checked",f"{quality['records_checked']:,}"); metrics[1].metric("Consistency issues",len(issues)); metrics[2].metric("Currency tolerance",f"±{quality['currency_tolerance']:.2f}")
        st.subheader("Completeness and coverage")
        counts_tab,nulls_tab,coverage_tab=st.tabs(["Record counts","Field nulls","Company / year coverage"])
        with counts_tab: st.dataframe(completeness["record_counts"],use_container_width=True,hide_index=True)
        with nulls_tab: st.dataframe(completeness["null_fields"],use_container_width=True,hide_index=True)
        with coverage_tab:
            st.dataframe(completeness["company_coverage"],use_container_width=True,hide_index=True)
            st.write("Years represented:",", ".join(map(str,completeness["year_coverage"])) or "None")
            st.caption("Optional datasets are reported as coverage facts; their absence does not lower an overall score. No opaque overall score is calculated.")
        st.subheader("Consistency detail")
        issue_companies=sorted({x["company"] for x in issues}); issue_tables=sorted({x["dataset"] for x in issues})
        f1,f2=st.columns(2); company=f1.selectbox("Issue company",["All"]+issue_companies); table=f2.selectbox("Issue dataset",["All"]+issue_tables)
        filtered=[x for x in issues if (company=="All" or x["company"]==company) and (table=="All" or x["dataset"]==table)]
        if filtered: st.dataframe(filtered,use_container_width=True,hide_index=True)
        else: st.success("No arithmetic consistency issues match the current filters.")
        st.download_button("Download consistency issues (CSV)",rows_to_csv(filtered),"eca_consistency_issues.csv","text/csv")
    with anomaly_tab:
        st.warning("Statistical review flag ≠ incorrect data or anti-competitive behavior. Flags only identify unusual observations for human review.")
        affected_companies={x["company"] for x in flags}; affected_products={x["product"] for x in flags}
        metrics=st.columns(3); metrics[0].metric("Statistical review flags",len(flags)); metrics[1].metric("Affected companies",len(affected_companies)); metrics[2].metric("Affected products",len(affected_products))
        st.caption(f"Method: product/year median and MAD, minimum sample {DEFAULT_MIN_SAMPLE_SIZE}, robust-z threshold {DEFAULT_ROBUST_Z_THRESHOLD}.")
        c1,c2,c3,c4=st.columns(4)
        fc=c1.selectbox("Flag company",["All"]+sorted(affected_companies)); fp=c2.selectbox("Flag product",["All"]+sorted(affected_products))
        fy=c3.selectbox("Flag year",["All"]+sorted({x["year"] for x in flags})); fv=c4.selectbox("Flag variable",["All"]+sorted({x["variable"] for x in flags}))
        filtered_flags=[x for x in flags if (fc=="All" or x["company"]==fc) and (fp=="All" or x["product"]==fp) and (fy=="All" or x["year"]==fy) and (fv=="All" or x["variable"]==fv)]
        if filtered_flags: st.dataframe(filtered_flags,use_container_width=True,hide_index=True)
        else: st.info("No statistical review flags match the current filters.")
        st.download_button("Download review flags (CSV)",rows_to_csv(filtered_flags),"eca_statistical_review_flags.csv","text/csv")
elif page == "Import Data":
    uploaded=st.file_uploader("Select a synthetic Data Request workbook",type=["xlsx"])
    if uploaded and st.button("Validate and import"):
        with tempfile.NamedTemporaryFile(suffix=".xlsx",delete=False) as handle: handle.write(uploaded.getbuffer()); temp=Path(handle.name)
        try:
            result=import_workbook(temp,db_path); st.success("Import succeeded") if result.status=="SUCCESS" else st.error("Import failed"); st.json(result.to_dict())
        finally: temp.unlink(missing_ok=True)
else:
    st.markdown('<div class="eca-guide-intro"><h3>How this prototype works</h3><p>A plain-language guide to the databases, workbooks, validation pipeline, application pages, and exact commands.</p></div>', unsafe_allow_html=True)
    if GUIDE.exists():
        guide_text = GUIDE.read_text(encoding="utf-8")
        st.download_button("Download guide", guide_text, file_name="ECA_Data_Request_Simple_Guide.md", mime="text/markdown")
        st.markdown(guide_text)
    else:
        st.error("SIMPLE_GUIDE.md was not found.")
