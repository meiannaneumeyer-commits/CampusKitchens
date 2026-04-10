import streamlit as st
import psycopg2

st.set_page_config(page_title="Edit Entry", page_icon="✏️")

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.title("✏️ Edit Food Entry")

try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            ei.id,
            fe.entry_date,
            l.name,
            fi.name,
            ei.quantity,
            fe.notes,
            fe.id
        FROM entry_items ei
        JOIN food_entries fe ON ei.entry_id = fe.id
        JOIN locations l ON fe.location_id = l.id
        JOIN food_items fi ON ei.food_item_id = fi.id
        ORDER BY fe.entry_date DESC, ei.id DESC;
    """)
    records = cur.fetchall()

    cur.execute("SELECT id, name FROM locations ORDER BY name;")
    location_rows = cur.fetchall()
    location_options = {row[1]: row[0] for row in location_rows}

    cur.execute("SELECT id, name FROM food_items ORDER BY name;")
    item_rows = cur.fetchall()
    item_options = {row[1]: row[0] for row in item_rows}

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Error loading records: {e}")
    st.stop()

if not records:
    st.info("No records available to edit.")
    st.stop()

record_map = {
    f"{r[1]} | {r[2]} | {r[3]} | Qty: {r[4]}": r
    for r in records
}

selected_label = st.selectbox("Select a record to edit", list(record_map.keys()))
selected_record = record_map[selected_label]

entry_item_id = selected_record[0]
current_date = selected_record[1]
current_location_name = selected_record[2]
current_item_name = selected_record[3]
current_quantity = float(selected_record[4])
current_notes = selected_record[5]
food_entry_id = selected_record[6]

with st.form("edit_entry_form"):
    new_date = st.date_input("Entry Date", value=current_date)
    new_location = st.selectbox(
        "Location",
        options=list(location_options.keys()),
        index=list(location_options.keys()).index(current_location_name)
    )
    new_item = st.selectbox(
        "Food Item",
        options=list(item_options.keys()),
        index=list(item_options.keys()).index(current_item_name)
    )
    new_quantity = st.number_input("Quantity", min_value=0.01, value=current_quantity, step=0.5)
    new_notes = st.text_area("Notes", value=current_notes if current_notes else "")

    submitted = st.form_submit_button("Update Entry")

    if submitted:
        errors = []

        if new_quantity <= 0:
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
                    UPDATE food_entries
                    SET entry_date = %s,
                        location_id = %s,
                        notes = %s
                    WHERE id = %s;
                    """,
                    (new_date, location_options[new_location], new_notes, food_entry_id)
                )

                cur.execute(
                    """
                    UPDATE entry_items
                    SET food_item_id = %s,
                        quantity = %s
                    WHERE id = %s;
                    """,
                    (item_options[new_item], new_quantity, entry_item_id)
                )

                conn.commit()
                cur.close()
                conn.close()

                st.success("✅ Entry updated successfully!")

            except Exception as e:
                st.error(f"Error updating entry: {e}")
