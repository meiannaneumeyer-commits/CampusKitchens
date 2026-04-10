import streamlit as st
import psycopg2

st.set_page_config(page_title="Add Entry", page_icon="➕")

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.title("➕ Add Food Entry")
st.write("Create one entry for a date and location, then attach multiple food items.")

# Load dropdown data
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

            location_id = location_options[selected_location]

            # 1. Check whether a parent entry already exists for this date + location
            cur.execute(
                """
                SELECT id, notes
                FROM food_entries
                WHERE entry_date = %s AND location_id = %s;
                """,
                (entry_date, location_id)
            )
            existing_entry = cur.fetchone()

            if existing_entry:
                entry_id = existing_entry[0]
                existing_notes = existing_entry[1]

                # Optional: update notes only if the existing notes are blank and user entered new notes
                if notes and (existing_notes is None or str(existing_notes).strip() == ""):
                    cur.execute(
                        """
                        UPDATE food_entries
                        SET notes = %s
                        WHERE id = %s;
                        """,
                        (notes, entry_id)
                    )
            else:
                # 2. Create a new parent entry if one does not already exist
                cur.execute(
                    """
                    INSERT INTO food_entries (entry_date, location_id, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (entry_date, location_id, notes)
                )
                entry_id = cur.fetchone()[0]

            # 3. Insert or update each selected item
            for item_name in selected_items:
                food_item_id = item_options[item_name]
                quantity = quantities[item_name]

                # Check if this item already exists for the same parent entry
                cur.execute(
                    """
                    SELECT id, quantity
                    FROM entry_items
                    WHERE entry_id = %s AND food_item_id = %s;
                    """,
                    (entry_id, food_item_id)
                )
                existing_item = cur.fetchone()

                if existing_item:
                    entry_item_id = existing_item[0]
                    existing_quantity = float(existing_item[1])

                    # Add the new quantity onto the old quantity
                    new_quantity = existing_quantity + float(quantity)

                    cur.execute(
                        """
                        UPDATE entry_items
                        SET quantity = %s
                        WHERE id = %s;
                        """,
                        (new_quantity, entry_item_id)
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO entry_items (entry_id, food_item_id, quantity)
                        VALUES (%s, %s, %s);
                        """,
                        (entry_id, food_item_id, quantity)
                    )

            conn.commit()
            cur.close()
            conn.close()

            st.success("✅ Food entry added successfully!")

        except Exception as e:
            st.error(f"Error adding entry: {e}")
