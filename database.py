import sqlite3
import datetime

DB_NAME = "weather_bot.db"

def create_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            reg_datetime DATETIME
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query TEXT,
            datetime DATETIME,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS citys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            aliases TEXT
        )
    """)

    conn.commit()
    conn.close()

def register_user_if_not_exists(user_id: int):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        now = datetime.datetime.now()
        cur.execute("INSERT INTO users (user_id, reg_datetime) VALUES (?, ?)", (user_id, now))
        conn.commit()
    conn.close()

def log_query(user_id: int, text: str):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    now = datetime.datetime.now()
    cur.execute(
        "INSERT INTO query_logs (user_id, query, datetime) VALUES (?, ?, ?)",
        (user_id, text, now)
    )
    conn.commit()
    conn.close()

def find_cities_in_db(city_list):
    """
    Возвращает (found, not_found).
      found = [(user_input, official_name), ...]
      not_found = [user_input, ...]
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT name, aliases FROM citys")
    rows = cur.fetchall()
    conn.close()

    aliases_map = {}
    for row in rows:
        db_name = row[0]
        db_aliases = row[1] or ""
        variants = [v.strip().lower() for v in db_aliases.split(',')]
        variants.append(db_name.lower())
        for v in variants:
            aliases_map[v] = db_name

    found = []
    not_found = []
    for city in city_list:
        low = city.lower()
        if low in aliases_map:
            found.append((city, aliases_map[low]))
        else:
            not_found.append(city)

    return found, not_found
