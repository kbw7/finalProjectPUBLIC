import csv
import requests
import json
import sqlite3
import os
import uuid
from datetime import datetime
import pandas as pd
import streamlit as st

# Database setup
DB_PATH = 'wellesley_crave.db'

def init_db():
    """Initialize the SQLite database with necessary tables"""
    db_exists = os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Create users table
    c.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        username TEXT,
        email TEXT
    )
    ''')

    # Check if food_journal table exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='food_journal'")
    if not c.fetchone():
        query = '''
        CREATE TABLE food_journal (
            entry_id TEXT PRIMARY KEY,
            user_id TEXT,
            date TEXT,
            meal_type TEXT,
            food_item TEXT,
            dining_hall TEXT,
            notes TEXT,
            calories FLOAT,
            protein FLOAT,
            carbs FLOAT,
            fat FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        '''
        c.execute(query)

    conn.commit()
    conn.close()
    return db_exists

def add_user(email, username="WellesleyUser"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = c.fetchone()

    if not user:
        user_id = str(uuid.uuid4())
        c.execute(
            "INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)",
            (user_id, username, email)
        )
        conn.commit()
    else:
        user_id = user[0]

    conn.close()
    return user_id

def add_food_entry(user_id, date, meal_type, food_item, dining_hall, notes="", calories=0.0, protein=0.0, carbs=0.0, fat=0.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    entry_id = str(uuid.uuid4())

    query = '''
    INSERT INTO food_journal 
    (entry_id, user_id, date, meal_type, food_item, dining_hall, notes, calories, protein, carbs, fat) 
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    c.execute(query, (entry_id, user_id, date, meal_type, food_item, dining_hall, notes, calories, protein, carbs, fat))

    conn.commit()
    conn.close()
    return entry_id

def get_food_entries(user_id, date=None):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    if date:
        c.execute('''
            SELECT entry_id, user_id, date, meal_type, food_item, dining_hall, notes, 
                   calories, protein, carbs as carbs, fat, created_at
            FROM food_journal 
            WHERE user_id = ? AND date = ? 
            ORDER BY meal_type, created_at DESC
        ''', (user_id, date))
    else:
        c.execute('''
            SELECT entry_id, user_id, date, meal_type, food_item, dining_hall, notes, 
                   calories, protein, carbs as carbs, fat, created_at
            FROM food_journal 
            WHERE user_id = ? 
            ORDER BY date DESC, meal_type, created_at DESC
        ''', (user_id,))

    rows = c.fetchall()
    entries = [dict(row) for row in rows]
    conn.close()
    return entries

def delete_food_entry(entry_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM food_journal WHERE entry_id = ?", (entry_id,))
    conn.commit()
    conn.close()
    return True

idInfo = [
    {"location": "Bae", "meal": "Breakfast", "locationID": "96", "mealID": "148"},
    {"location": "Bae", "meal": "Lunch", "locationID": "96", "mealID": "149"},
    {"location": "Bae", "meal": "Dinner", "locationID": "96", "mealID": "312"},
    {"location": "Bates", "meal": "Breakfast", "locationID": "95", "mealID": "145"},
    {"location": "Bates", "meal": "Lunch", "locationID": "95", "mealID": "146"},
    {"location": "Bates", "meal": "Dinner", "locationID": "95", "mealID": "311"},
    {"location": "StoneD", "meal": "Breakfast", "locationID": "131", "mealID": "261"},
    {"location": "StoneD", "meal": "Lunch", "locationID": "131", "mealID": "262"},
    {"location": "StoneD", "meal": "Dinner", "locationID": "131", "mealID": "263"},
    {"location": "Tower", "meal": "Breakfast", "locationID": "97", "mealID": "153"},
    {"location": "Tower", "meal": "Lunch", "locationID": "97", "mealID": "154"},
    {"location": "Tower", "meal": "Dinner", "locationID": "97", "mealID": "310"}
]

def fetch_all_menu_items():
    menu_items = []
    current_date = datetime.now().date()
    formatted_date = current_date.strftime("%m-%d-%Y")

    for item in idInfo:
        try:
            location_id = item["locationID"]
            meal_id = item["mealID"]
            location = item["location"]
            meal = item["meal"]

            base_url = "https://dish.avifoodsystems.com/api/menu-items/week"
            params = {"date": formatted_date, "locationId": location_id, "mealId": meal_id}

            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()

            for food_item in data:
                food_item["dining_hall"] = location
                food_item["meal_type"] = meal
                menu_items.append(food_item)

        except requests.RequestException as e:
            st.error(f"Error fetching menu for {location} {meal}: {e}")

    return menu_items

def extract_nutritional_info(nutritionals):
    if not nutritionals:
        return 0.0, 0.0, 0.0, 0.0

    calories = float(nutritionals.get("calories", 0) or 0)
    protein = float(nutritionals.get("protein", 0) or 0)
    carbs = float(nutritionals.get("carbohydrates", 0) or 0)
    fat = float(nutritionals.get("fat", 0) or 0)

    return calories, protein, carbs, fat

# Initialize database
init_db()

# Add a test user
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = add_user("test@wellesley.edu")

# Session state setup
if 'selected_dishes' not in st.session_state:
    st.session_state['selected_dishes'] = []
if 'meal_notes' not in st.session_state:
    st.session_state['meal_notes'] = ""

# Streamlit layout
st.title("Wellesley Food Journal")
tab1, tab2 = st.tabs(["Log Food", "View Journal"])

with tab1:
    st.header("Log Your Meals")
    if 'all_menu_items' not in st.session_state:
        with st.spinner("Loading menu items..."):
            st.session_state['all_menu_items'] = fetch_all_menu_items()

    food_options = []
    food_item_map = {}

    for item in st.session_state['all_menu_items']:
        name = item.get('name', '')
        if name:
            label = f"{name} ({item['dining_hall']} - {item['meal_type']})"
            food_options.append(label)
            food_item_map[label] = item

    food_options.sort()
    col1, col2 = st.columns(2)
    with col1:
        log_date = st.date_input("Date", datetime.now().date())
    with col2:
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])

    selected_food = st.selectbox(
        "Search for food item",
        options=[""] + food_options,
        index=0,
        key="food_search"
    )

    if selected_food and st.button("Add to Meal"):
        selected_item = food_item_map.get(selected_food)
        if selected_item:
            food_name = selected_item.get('name', '')
            dining_hall = selected_item.get('dining_hall', '')
            item_meal_type = selected_item.get('meal_type', '')
            calories, protein, carbs, fat = extract_nutritional_info(selected_item.get('nutritionals', {}))

            st.session_state['selected_dishes'].append({
                "name": food_name,
                "dining_hall": dining_hall,
                "meal_type": item_meal_type,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat
            })
            st.success(f"Added {food_name} to your meal!")
            st.rerun()

    if st.session_state['selected_dishes']:
        st.subheader("Selected Items for this Meal")
        total_calories = total_protein = total_carbs = total_fat = 0

        for i, dish in enumerate(st.session_state['selected_dishes']):
            with st.container(border=True):
                col1, col2, col3 = st.columns([3, 1, 0.5])
                with col1:
                    st.write(f"**{dish['name']}**")
                    st.caption(f"From: {dish['dining_hall']}")
                with col2:
                    st.caption(f"Calories: {dish['calories']:.1f}")
                    st.caption(f"Protein: {dish['protein']:.1f}g")
                    st.caption(f"Carbs: {dish['carbs']:.1f}g")
                    st.caption(f"Fat: {dish['fat']:.1f}g")
                with col3:
                    if st.button("✕", key=f"remove_{i}"):
                        st.session_state['selected_dishes'].pop(i)
                        st.rerun()
            total_calories += dish['calories']
            total_protein += dish['protein']
            total_carbs += dish['carbs']
            total_fat += dish['fat']

        st.subheader("Meal Totals")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Calories", f"{total_calories:.1f}")
        col2.metric("Total Protein", f"{total_protein:.1f}g")
        col3.metric("Total Carbs", f"{total_carbs:.1f}g")
        col4.metric("Total Fat", f"{total_fat:.1f}g")

        st.session_state['meal_notes'] = st.text_area("Notes for this meal", st.session_state['meal_notes'])

        if st.button("Log Complete Meal"):
            formatted_log_date = log_date.strftime("%Y-%m-%d")
            for dish in st.session_state['selected_dishes']:
                add_food_entry(
                    st.session_state['user_id'],
                    formatted_log_date,
                    meal_type,
                    dish['name'],
                    dish['dining_hall'],
                    st.session_state['meal_notes'],
                    dish['calories'],
                    dish['protein'],
                    dish['carbs'],
                    dish['fat']
                )
            st.success(f"Added {len(st.session_state['selected_dishes'])} items to your food journal!")
            st.session_state['selected_dishes'] = []
            st.session_state['meal_notes'] = ""
            st.rerun()
    else:
        st.info("Search and add items to create your meal")

with tab2:
    st.header("Your Food Journal")
    view_date = st.date_input("Select Date to View", datetime.now().date(), key="view_date")
    formatted_view_date = view_date.strftime("%Y-%m-%d")
    entries = get_food_entries(st.session_state['user_id'], formatted_view_date)

    for entry in entries:
        if st.session_state.get(f'delete_{entry["entry_id"]}', False):
            delete_food_entry(entry["entry_id"])
            st.session_state[f'delete_{entry["entry_id"]}'] = False
            st.rerun()

    if entries:
        meal_entries = {}
        for entry in entries:
            meal = entry['meal_type']
            meal_entries.setdefault(meal, []).append(entry)

        for meal, meal_entries_list in meal_entries.items():
            st.subheader(meal)
            meal_calories = sum(entry['calories'] for entry in meal_entries_list)
            meal_protein = sum(entry['protein'] for entry in meal_entries_list)
            meal_carbs = sum(entry['carbs'] for entry in meal_entries_list)
            meal_fat = sum(entry['fat'] for entry in meal_entries_list)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Calories", f"{meal_calories:.1f}")
            col2.metric("Total Protein", f"{meal_protein:.1f}g")
            col3.metric("Total Carbs", f"{meal_carbs:.1f}g")
            col4.metric("Total Fat", f"{meal_fat:.1f}g")

            for entry in meal_entries_list:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([3, 1, 0.5])
                    with col1:
                        st.markdown(f"**{entry['food_item']}**")
                        st.caption(f"Dining Hall: {entry['dining_hall']}")
                        if entry['notes']:
                            st.text(f"Notes: {entry['notes']}")
                    with col2:
                        st.caption(f"Calories: {entry['calories']}")
                        st.caption(f"Protein: {entry['protein']}g")
                        st.caption(f"Carbs: {entry['carbs']}g")
                        st.caption(f"Fat: {entry['fat']}g")
                    with col3:
                        if st.button("✕", key=f"delete_button_{entry['entry_id']}"):
                            st.session_state[f'delete_{entry["entry_id"]}'] = True
                            st.rerun()
    else:
        st.info(f"No journal entries found for {view_date.strftime('%B %d, %Y')}.")

