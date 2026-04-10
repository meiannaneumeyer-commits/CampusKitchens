import streamlit as st
import psycopg2

st.set_page_config(page_title="Add Entry", page_icon="➕")

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

st.title("➕ Add Food Entry")
st.write("Create one entry for a date and location, then attach multiple food items.")

# --------------------------
# Load dropdown data
# --------------------------
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

if not location_options:
    st.error("No locations found in the database.")
    st.stop()

if not item_options:
    st.error("No food items found in the database.")
    st.stop()

# --------------------------
# Form
# --------------------------
with st.form("multi_item_entry_form"):
    entry_date = st.date_input("Entry Date")
    selected_location = st.selectbox("Location", options=list(location_options.keys()))
    notes = st.text_area("Notes")

    st.markdown("### Select Food Items")

    selected_items = st.multiselect(
        "Choose one or more food items",
        options=list(item_options.keys())
    )

    quantities = {}
    if selected_items:
        st.markdown("### Enter Quantity for Each Selected Item")
        for item_name in selected_items:
            quantities[item_name] = st.number_input(
                f"Quantity for {item_name}",
                min_value=0.01,
                step=0.5,
                key=f"qty_{item_name}"
            )

    submitted = st.form_submit_button("Add Entry")

    if submitted:
        errors = []

        if not selected_location:
            errors.append("Location is required.")

        if len(selected_items) == 0:
            errors.append("Please select at least one food item.")

        for item_name in selected_items:
            if quantities[item_name] <= 0:
                errors.append(f"Quantity for {item_name} must be greater than 0.")

        if errors:
            for error in errors:
                st.error(error)
        else:
            try:
                conn = get_connection()
                cur = conn.cursor()

                # Create one parent entry
                cur.execute(
                    """
                    INSERT INTO food_entries (entry_date, location_id, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (entry_date, location_options[selected_location], notes)
                )
                entry_id = cur.fetchone()[0]

                # Create one child row per selected item
                for item_name in selected_items:
                    cur.execute(
                        """
                        INSERT INTO entry_items (entry_id, food_item_id, quantity)
                        VALUES (%s, %s, %s);
                        """,
                        (
                            entry_id,
                            item_options[item_name],
                            quantities[item_name]
                        )
                    )

                conn.commit()
                cur.close()
                conn.close()

                st.success("✅ Food entry added successfully with multiple items!")

            except Exception as e:
                st.error(f"Error adding entry: {e}")
