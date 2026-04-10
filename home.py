import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(
    page_title="Food Entry Database App",
    page_icon="🍽️",
    layout="wide"
)

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.title("🍽️ Food Entry Database App")
st.write("Welcome! Use the sidebar to view, add, edit, or delete food entries.")

st.markdown("---")
st.subheader("📊 Current Data Summary")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM food_entries;")
    total_entries = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM locations;")
    total_locations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM food_items;")
    total_items = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(quantity), 0) FROM entry_items;")
    total_quantity = cur.fetchone()[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Entries", int(total_entries))
    col2.metric("Locations", int(total_locations))
    col3.metric("Unique Items", int(total_items))
    col4.metric("Total Quantity", float(total_quantity))

    st.markdown("---")
    st.subheader("🔍 Filter Food Entries")

    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM entry_date)::INT AS year
        FROM food_entries
        ORDER BY year;
    """)
    years = [row[0] for row in cur.fetchall()]
    year_options = ["All"] + [str(year) for year in years]

    cur.execute("SELECT name FROM locations ORDER BY name;")
    locations = [row[0] for row in cur.fetchall()]
    location_options = ["All"] + locations

    filter_col1, filter_col2 = st.columns(2)
    selected_year = filter_col1.selectbox("Filter by Year", year_options)
    selected_location = filter_col2.selectbox("Filter by Location", location_options)

    query = """
        SELECT
            fe.id AS entry_id,
            fe.entry_date AS entry_date,
            l.name AS location,
            fi.name AS item,
            ei.quantity AS quantity,
            fe.notes AS notes
        FROM food_entries fe
        JOIN locations l ON fe.location_id = l.id
        JOIN entry_items ei ON fe.id = ei.entry_id
        JOIN food_items fi ON ei.food_item_id = fi.id
        WHERE 1=1
    """
    params = []

    if selected_year != "All":
        query += " AND EXTRACT(YEAR FROM fe.entry_date) = %s"
        params.append(int(selected_year))

    if selected_location != "All":
        query += " AND l.name = %s"
        params.append(selected_location)

    query += " ORDER BY fe.entry_date DESC, l.name, fi.name;"

    df = pd.read_sql(query, conn, params=params)

    st.markdown("---")
    st.subheader("📈 Filtered Data Summary")

    filtered_entries = int(df["entry_id"].nunique()) if not df.empty else 0
    filtered_items = int(df["item"].nunique()) if not df.empty else 0
    filtered_quantity = float(df["quantity"].sum()) if not df.empty else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("Filtered Entries", filtered_entries)
    c2.metric("Filtered Unique Items", filtered_items)
    c3.metric("Filtered Total Quantity", filtered_quantity)

    st.markdown("---")
    st.subheader("📋 Food Entry Records")

    if df.empty:
        st.info("No matching records found.")
    else:
        display_df = df.rename(columns={
            "entry_id": "ID",
            "entry_date": "Date",
            "location": "Location",
            "item": "Item",
            "quantity": "Quantity",
            "notes": "Notes"
        })
        st.dataframe(display_df, use_container_width=True)

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Error loading dashboard: {e}")
