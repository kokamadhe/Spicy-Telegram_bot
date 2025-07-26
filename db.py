import sqlite3

# Connect to SQLite DB (creates it if it doesn't exist)
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# Create a users table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        is_premium INTEGER DEFAULT 0
    )
''')
conn.commit()

# Add or update user
def add_user(user_id, username):
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()

# Set a user as premium
def set_premium(user_id):
    cursor.execute('''
        UPDATE users SET is_premium = 1 WHERE user_id = ?
    ''', (user_id,))
    conn.commit()

# Check if a user is premium
def is_premium(user_id):
    cursor.execute('''
        SELECT is_premium FROM users WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    return result and result[0] == 1

# Get all users (optional)
def get_all_users():
    cursor.execute('SELECT * FROM users')
    return cursor.fetchall()

