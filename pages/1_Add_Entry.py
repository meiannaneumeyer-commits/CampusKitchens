
import streamlit as st
import psycopg2

st.set_page_config(page_title="Add Entry", page_icon="➕")

def get_connection():
    return psycopg2.connect(st.secrets["DATABASE_URL
"])

st.title("➕ Add Food Entry")
st.write("Enter a date and location, then type food items manually.")

# --------------------------
# Load locations only
# --------------------------
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

# --------------------------
# Form
# --------------------------
with st.form("add_entry_form"):
    entry_date = st.date_input("Entry Date")
    selected_location = st.selectbox("Location", options=list(location_options.keys()))
    notes = st.text_area("Notes")

    st.markdown("### Add Food Items")

    # Let user choose how many rows
    num_items = st.number_input("Number of different items", min_value=1, max_value=10, value=3)

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

# --------------------------
# Submit logic
# --------------------------
if submitted:
    errors = []

    # Validate
    valid_items = []

    for name, qty in item_inputs:
        if name.strip() != "":
            if qty <= 0:
                errors.append(f"Quantity for '{name}' must be > 0")
            else:
                valid_items.append((name.strip(), qty))

    if len(valid_items) == 0:
        errors.append("Enter at least one valid food item")

    if errors:
        for error in errors:
            st.error(error)
    else:
        try:
            conn = get_connection()
            cur = conn.cursor()

            location_id = location_options[selected_location]

            # --------------------------
            # 1. Get or create parent entry
            # --------------------------
            cur.execute(
                """
                SELECT id
                FROM food_entries
                WHERE entry_date = %s AND location_id = %s;
                """,
                (entry_date, location_id)
            )
            existing_entry = cur.fetchone()

            if existing_entry:
                entry_id = existing_entry[0]
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

            # --------------------------
            # 2. Insert items
            # --------------------------
            for item_name, quantity in valid_items:

                # Check if item exists
                cur.execute(
                    "SELECT id FROM food_items WHERE LOWER(name) = LOWER(%s);",
                    (item_name,)
                )
                result = cur.fetchone()

                if result:
                    food_item_id = result[0]
                else:
                    # Create new item
                    cur.execute(
                        """
                        INSERT INTO food_items (name)
                        VALUES (%s)
                        RETURNING id;
                        """,
                        (item_name,)
                    )
                    food_item_id = cur.fetchone()[0]

                # Check if already exists in this entry
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
                    new_qty = float(existing_item[1]) + float(quantity)

                    cur.execute(
                        """
                        UPDATE entry_items
                        SET quantity = %s
                        WHERE id = %s;
                        """,
                        (new_qty, existing_item[0])
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

            st.success("✅ Entry added successfully with typed items!")

        except Exception as e:
            st.error(f"Error: {e}")
