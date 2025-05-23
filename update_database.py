import sqlite3
from datetime import datetime
from typing import List
from zoneinfo import ZoneInfo
import json
import uuid

# All of Prof. Eni Code from fresh-missing repo
                                                             
from db_sync import get_db_path
DB_PATH = get_db_path()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for individual users
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            diningHall TEXT,
            allergens TEXT,
            dietaryRestrictions TEXT,
            favorites TEXT
        )
    ''')

    # Table for submission summaries
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_journal (
            entry_id TEXT PRIMARY KEY,
            user_id INTEGER AUTO_INCREMENT,
            date TEXT,
            meal_type TEXT,
            food_item TEXT,
            dining_hall TEXT,
            notes TEXT,
            calories FLOAT,
            protein FLOAT,
            carbs FLOAT,
            fat FLOAT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    conn.commit()
    conn.close()

def fetch_food_journal():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM food_journal")
    entries = cursor.fetchall()
    conn.close()

    return entries

def fetch_user_info(email: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user_info = cursor.fetchone()
    conn.close()

    return user_info

def checkNewUser(email:str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))

    userInfo = cursor.fetchone()

    return str(type(userInfo)) == "<class 'NoneType'>"


def store_new_user_info(email: str, diningHall: str, allergens: str, dietaryRestrictions: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("INSERT INTO users (email, diningHall, allergens, dietaryRestrictions) VALUES (?, ?, ?, ?)", (email, diningHall, allergens, dietaryRestrictions))

    conn.commit()
    conn.close()

def getUserFavDiningHall(user):
    conn = sqlite3.connect(DB_PATH) # adding local path to private repo
    cursor = conn.cursor()

    cursor.execute("SELECT diningHall FROM users WHERE email = ?", (user.get("email"),))

    # Source on try/except - https://www.geeksforgeeks.org/python-exception-handling/
    try:
        diningHall = cursor.fetchone()[0]
    except TypeError:
        diningHall = "" # making this default for now!

    conn.close()

    return diningHall

# ------ Food Journal Methods -------
def get_or_create_user(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE email = ?", (email,))
    result = c.fetchone()
    if result:
        user_id = result[0]
    else:
        c.execute("INSERT INTO users (email) VALUES (?)", (email,))
        conn.commit()
        user_id = c.lastrowid
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
           calories, protein, carbs, fat
    FROM food_journal 
    WHERE user_id = ? AND date = ? 
    ORDER BY meal_type
''', (user_id, date))
    else:
        c.execute('''
    SELECT entry_id, user_id, date, meal_type, food_item, dining_hall, notes, 
           calories, protein, carbs, fat
    FROM food_journal 
    WHERE user_id = ? 
    ORDER BY date DESC, meal_type
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

# --------------------------------------Settings Page Methods ---------------------------------------
def update_user_dining_hall(email: str, dining_hall: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE users SET diningHall = ? WHERE email = ?", (dining_hall, email))
        conn.commit()

def get_user_favorites(email: str):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT favorites FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return json.loads(row[0]) if row and row[0] else []

def add_favorite_dish(email: str, new_dish: str):
    favorites = get_user_favorites(email)
    if new_dish not in favorites:
        favorites.append(new_dish)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET favorites = ? WHERE email = ?", (json.dumps(favorites), email))
            conn.commit()
    return favorites

def remove_favorite_dish(email: str, dish: str):
    favorites = get_user_favorites(email)
    if dish in favorites:
        favorites.remove(dish)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("UPDATE users SET favorites = ? WHERE email = ?", (json.dumps(favorites), email))
            conn.commit()
    return favorites

def get_user_allergens_and_restrictions(email: str):
    import ast
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT allergens, dietaryRestrictions FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        
        curr_allergens = []
        curr_restrictions = []
        
        if row and row[0]:
            try:
                curr_allergens = ast.literal_eval(row[0])
            except (SyntaxError, ValueError):
                # Fallback to empty list if parsing fails
                pass
        
        if row and row[1]:
            try:
                curr_restrictions = ast.literal_eval(row[1])
            except (SyntaxError, ValueError):
                # Fallback to empty list if parsing fails
                pass
        
        return curr_allergens, curr_restrictions


def update_user_allergy_preferences(email: str, allergens: list, restrictions: list):
    # Ensure inputs are proper lists
    if not isinstance(allergens, list):
        allergens = [allergens] if allergens else []
    if not isinstance(restrictions, list):
        restrictions = [restrictions] if restrictions else []
    
    # Convert to JSON
    allergens_json = json.dumps(allergens)
    restrictions_json = json.dumps(restrictions)
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET allergens = ?, dietaryRestrictions = ? WHERE email = ?",
            (allergens_json, restrictions_json, email)
        )
        
        conn.commit()
        return True
    
# Call this once in your main app to initialize the DB (if not already)
if __name__ == "__main__":
    init_db()
    print("Database initialized.")
