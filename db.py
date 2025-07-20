import sqlite3

def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS premium_users (user_id TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_premium_user(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO premium_users (user_id) VALUES (?)", (str(user_id),))
    conn.commit()
    conn.close()

def is_premium_user(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT 1 FROM premium_users WHERE user_id = ?", (str(user_id),))
    result = c.fetchone()
    conn.close()
    return result is not None
