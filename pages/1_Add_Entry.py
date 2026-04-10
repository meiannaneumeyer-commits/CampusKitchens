import streamlit as st
import psycopg2

st.set_page_config(page_title="Add Entry", page_icon="➕")

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

st.title("➕ Add Food Entry")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM locations ORDER BY name;")
    location_rows = cur.fetchall()
    location_options = {row[1]: row[0] for row in location_rows}

    cur.execute("SELECT id, name FROM food_items ORDER BY name;")
    item_rows = cur.fetchall()
    item_options = {row[1]: row[0] for row in item_rows}

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Error loading form data: {e}")
    st.stop()

with st.form("add_entry_form"):
    entry_date = st.date_input("Entry Date")
    selected_location = st.selectbox("Location", options=list(location_options.keys()))
    selected_item = st.selectbox("Food Item", options=list(item_options.keys()))
    quantity = st.number_input("Quantity", min_value=0.01, step=0.5)
    notes = st.text_area("Notes")

    submitted = st.form_submit_button("Add Entry")

    if submitted:
        errors = []

        if quantity <= 0:
            errors.append("Quantity must be greater than 0.")

        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()

                cur.execute(
                    """
                    INSERT INTO food_entries (entry_date, location_id, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (entry_date, location_options[selected_location], notes)
                )
                entry_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO entry_items (entry_id, food_item_id, quantity)
                    VALUES (%s, %s, %s);
                    """,
                    (entry_id, item_options[selected_item], quantity)
                )

                conn.commit()
                cur.close()
                conn.close()

                st.success("✅ Food entry added successfully!")

            except Exception as e:
                st.error(f"Error adding entry: {e}")