import streamlit as st
import psycopg2

st.set_page_config(page_title="Add Entry", page_icon="➕")

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL"])

st.title("➕ Add Food Entry")
st.write("Enter one date and location, then type food items manually.")

# Load locations
try:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name FROM locations ORDER BY name;")
    location_rows = cur.fetchall()
    location_options = {row[1]: row[0] for row in location_rows}

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Error loading locations: {e}")
    st.stop()

if not location_options:
    st.error("No locations found in the database.")
    st.stop()

with st.form("add_entry_form"):
    entry_date = st.date_input("Entry Date")
    selected_location = st.selectbox("Location", options=list(location_options.keys()))
    notes = st.text_area("Notes")

    st.markdown("### Add Food Items")

    num_items = st.number_input(
        "Number of different items",
        min_value=1,
        max_value=10,
        value=3,
        step=1
    )

    item_inputs = []

    for i in range(int(num_items)):
        col1, col2 = st.columns(2)

        item_name = col1.text_input(f"Item {i+1}", key=f"item_{i}")
        quantity = col2.number_input(
            f"Qty {i+1}",
            min_value=0.01,
            step=0.5,
            key=f"qty_{i}"
        )

        item_inputs.append((item_name, quantity))

    submitted = st.form_submit_button("Add Entry")

if submitted:
    errors = []
    valid_items = []

    for name, qty in item_inputs:
        clean_name = name.strip()
        if clean_name != "":
            if qty <= 0:
                errors.append(f"Quantity for '{clean_name}' must be greater than 0.")
            else:
                valid_items.append((clean_name, qty))

    if len(valid_items) == 0:
        errors.append("Enter at least one food item.")

    if errors:
        for error in errors:
            st.error(error)
    else:
        try:
            conn = get_connection()
            cur = conn.cursor()

            location_id = location_options[selected_location]

            # Check for existing parent entry
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
                cur.execute(
                    """
                    INSERT INTO food_entries (entry_date, location_id, notes)
                    VALUES (%s, %s, %s)
                    RETURNING id;
                    """,
                    (entry_date, location_id, notes)
                )
                entry_id = cur.fetchone()[0]

            # Add typed food items
            for item_name, quantity in valid_items:
                cur.execute(
                    """
                    SELECT id
                    FROM food_items
                    WHERE LOWER(name) = LOWER(%s);
                    """,
                    (item_name,)
                )
                existing_food = cur.fetchone()

                if existing_food:
                    food_item_id = existing_food[0]
                else:
                    cur.execute(
                        """
                        INSERT INTO food_items (name)
                        VALUES (%s)
                        RETURNING id;
                        """,
                        (item_name,)
                    )
                    food_item_id = cur.fetchone()[0]

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
            st.error(f"Error saving entry: {e}")
