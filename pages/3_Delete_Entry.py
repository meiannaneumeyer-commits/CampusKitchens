import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(page_title="Delete Entry", page_icon="🗑️")

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.title("🗑️ Delete Food Entry")
st.write("Search for a record, then delete it.")

try:
    conn = get_connection()
    cur = conn.cursor()

    # Load locations for optional filter
    cur.execute("SELECT name FROM locations ORDER BY name;")
    location_options = ["All"] + [row[0] for row in cur.fetchall()]

    # Load years for optional filter
    cur.execute("""
        SELECT DISTINCT EXTRACT(YEAR FROM entry_date)::INT AS year
        FROM food_entries
        ORDER BY year DESC;
    """)
    year_options = ["All"] + [str(row[0]) for row in cur.fetchall()]

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Error loading filters: {e}")
    st.stop()

col1, col2 = st.columns(2)
selected_year = col1.selectbox("Filter by Year", year_options)
selected_location = col2.selectbox("Filter by Location", location_options)

item_search = st.text_input("Type food item name to search")

try:
    conn = get_connection()

    query = """
        SELECT
            ei.id AS entry_item_id,
            fe.id AS food_entry_id,
            fe.entry_date,
            l.name AS location,
            fi.name AS item,
            ei.quantity,
            fe.notes
        FROM entry_items ei
        JOIN food_entries fe ON ei.entry_id = fe.id
        JOIN locations l ON fe.location_id = l.id
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

    if item_search.strip() != "":
        query += " AND LOWER(fi.name) LIKE LOWER(%s)"
        params.append(f"%{item_search.strip()}%")

    query += " ORDER BY fe.entry_date DESC, l.name, fi.name;"

    df = pd.read_sql(query, conn, params=params)
    conn.close()

except Exception as e:
    st.error(f"Error loading records: {e}")
    st.stop()

if df.empty:
    st.info("No matching records found.")
else:
    st.markdown("### Matching Records")

    for _, row in df.iterrows():
        with st.container():
            st.write(
                f"**Date:** {row['entry_date']}  |  "
                f"**Location:** {row['location']}  |  "
                f"**Item:** {row['item']}  |  "
                f"**Qty:** {row['quantity']}"
            )

            if pd.notna(row["notes"]) and str(row["notes"]).strip() != "":
                st.write(f"**Notes:** {row['notes']}")

            confirm_key = f"confirm_{int(row['entry_item_id'])}"
            button_key = f"delete_{int(row['entry_item_id'])}"

            confirm = st.checkbox(
                f"Confirm delete for {row['item']} on {row['entry_date']}",
                key=confirm_key
            )

            if st.button("Delete This Record", key=button_key):
                if not confirm:
                    st.error("Please confirm deletion first.")
                else:
                    try:
                        conn = get_connection()
                        cur = conn.cursor()

                        entry_item_id = int(row["entry_item_id"])
                        food_entry_id = int(row["food_entry_id"])

                        # Delete child row
                        cur.execute(
                            "DELETE FROM entry_items WHERE id = %s;",
                            (entry_item_id,)
                        )

                        # If no more child rows remain, delete parent row
                        cur.execute(
                            "SELECT COUNT(*) FROM entry_items WHERE entry_id = %s;",
                            (food_entry_id,)
                        )
                        remaining = cur.fetchone()[0]

                        if remaining == 0:
                            cur.execute(
                                "DELETE FROM food_entries WHERE id = %s;",
                                (food_entry_id,)
                            )

                        conn.commit()
                        cur.close()
                        conn.close()

                        st.success("✅ Record deleted successfully!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error deleting record: {e}")

            st.markdown("---")
